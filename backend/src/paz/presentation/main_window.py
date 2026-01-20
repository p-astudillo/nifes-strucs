"""
Main application window for PAZ structural analysis software.

Provides the main UI with toolbar, viewport, and panels.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QToolBar,
)

from paz.application.commands import CreateNodeCommand, CreateFrameCommand
from paz.application.services import AnalysisService, UndoRedoService
from paz.core.grid_config import GridConfig
from paz.domain.loads import LoadCase, LoadCaseType, NodalLoad
from paz.domain.results import AnalysisResults
from paz.domain.model import StructuralModel
from paz.domain.model.project import Project, ProjectFile
from paz.infrastructure.repositories.file_repository import FileRepository
from paz.infrastructure.repositories.materials_repository import MaterialsRepository
from paz.infrastructure.repositories.sections_repository import SectionsRepository
from paz.presentation.dialogs import FrameDialog, MaterialDialog, NodeDialog, SectionDialog
from paz.presentation.panels import ModelTreeWidget, PropertyPanel, ResultsPanel
from paz.presentation.viewport import ViewportWidget


if TYPE_CHECKING:
    pass


class DrawingTool(Enum):
    """Available drawing tools."""

    SELECT = auto()
    NODE = auto()
    FRAME = auto()
    PAN = auto()
    ZOOM = auto()


class MainWindow(QMainWindow):
    """
    Main application window.

    Provides:
    - Toolbar with drawing tools
    - 3D Viewport for model visualization
    - Model tree sidebar
    - Properties panel
    - Undo/redo support
    """

    model_changed = Signal()

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()

        self.setWindowTitle("PAZ - Structural Analysis")
        self.setMinimumSize(1200, 800)

        # Core data
        self._model = StructuralModel()
        self._undo_service = UndoRedoService()
        self._current_tool = DrawingTool.SELECT
        self._default_material = "A36"
        self._default_section = "W14X22"

        # Project management
        self._project = Project(name="Untitled")
        self._project_path: str | None = None
        self._is_modified = False

        # Repositories
        self._file_repository = FileRepository()
        self._materials_repository = MaterialsRepository()
        self._sections_repository = SectionsRepository()

        # Analysis service and results
        self._analysis_service = AnalysisService()
        self._analysis_results: AnalysisResults | None = None

        # For frame creation: store first node
        self._frame_start_node_id: int | None = None

        # Setup UI
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_dock_widgets()
        self._setup_status_bar()

        # Connect signals
        self._connect_signals()

        # Initial state
        self._update_model_tree()
        self._update_status_bar()

    def _setup_menu_bar(self) -> None:
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New Project", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open_project)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._on_save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        self._undo_action = QAction("&Undo", self)
        self._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self._undo_action.triggered.connect(self._on_undo)
        self._undo_action.setEnabled(False)
        edit_menu.addAction(self._undo_action)

        self._redo_action = QAction("&Redo", self)
        self._redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self._redo_action.triggered.connect(self._on_redo)
        self._redo_action.setEnabled(False)
        edit_menu.addAction(self._redo_action)

        edit_menu.addSeparator()

        delete_action = QAction("&Delete", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self._on_delete)
        edit_menu.addAction(delete_action)

        edit_menu.addSeparator()

        select_all_action = QAction("Select &All", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(self._on_select_all)
        edit_menu.addAction(select_all_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        reset_view_action = QAction("&Reset View", self)
        reset_view_action.setShortcut("R")
        reset_view_action.triggered.connect(self._on_reset_view)
        view_menu.addAction(reset_view_action)

        # Model menu
        model_menu = menubar.addMenu("&Model")

        add_node_action = QAction("Add &Node...", self)
        add_node_action.setShortcut("Ctrl+Shift+N")
        add_node_action.triggered.connect(self._on_add_node_dialog)
        model_menu.addAction(add_node_action)

        add_frame_action = QAction("Add &Frame...", self)
        add_frame_action.setShortcut("Ctrl+Shift+F")
        add_frame_action.triggered.connect(self._on_add_frame_dialog)
        model_menu.addAction(add_frame_action)

        model_menu.addSeparator()

        materials_action = QAction("&Materials...", self)
        materials_action.triggered.connect(self._on_select_material)
        model_menu.addAction(materials_action)

        sections_action = QAction("&Sections...", self)
        sections_action.triggered.connect(self._on_select_section)
        model_menu.addAction(sections_action)

        # Analysis menu
        analysis_menu = menubar.addMenu("&Analysis")

        run_analysis_action = QAction("&Run Analysis", self)
        run_analysis_action.setShortcut("F5")
        run_analysis_action.triggered.connect(self._on_run_analysis)
        analysis_menu.addAction(run_analysis_action)

        analysis_menu.addSeparator()

        view_results_action = QAction("&View Results", self)
        view_results_action.triggered.connect(self._on_view_results)
        analysis_menu.addAction(view_results_action)

    def _setup_toolbar(self) -> None:
        """Create the main toolbar with drawing tools."""
        toolbar = QToolBar("Drawing Tools")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Select tool
        self._select_action = QAction("Select", self)
        self._select_action.setCheckable(True)
        self._select_action.setChecked(True)
        self._select_action.setShortcut("V")
        self._select_action.setToolTip("Select elements (V)")
        self._select_action.triggered.connect(lambda: self._set_tool(DrawingTool.SELECT))
        toolbar.addAction(self._select_action)

        # Node tool
        self._node_action = QAction("Node", self)
        self._node_action.setCheckable(True)
        self._node_action.setShortcut("N")
        self._node_action.setToolTip("Create nodes (N) - Click to place")
        self._node_action.triggered.connect(lambda: self._set_tool(DrawingTool.NODE))
        toolbar.addAction(self._node_action)

        # Frame tool
        self._frame_action = QAction("Frame", self)
        self._frame_action.setCheckable(True)
        self._frame_action.setShortcut("F")
        self._frame_action.setToolTip("Create frames (F) - Click two nodes")
        self._frame_action.triggered.connect(lambda: self._set_tool(DrawingTool.FRAME))
        toolbar.addAction(self._frame_action)

        toolbar.addSeparator()

        # Delete action
        delete_action = QAction("Delete", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.setToolTip("Delete selected elements")
        delete_action.triggered.connect(self._on_delete)
        toolbar.addAction(delete_action)

        # Tool action group for exclusive selection
        self._tool_actions = [
            self._select_action,
            self._node_action,
            self._frame_action,
        ]

    def _setup_central_widget(self) -> None:
        """Create the central viewport widget."""
        self._viewport = ViewportWidget()
        self._viewport.set_model(self._model)
        self._viewport.set_grid_config(GridConfig())
        self.setCentralWidget(self._viewport)

    def _setup_dock_widgets(self) -> None:
        """Create dock widgets for sidebars."""
        # Model tree dock (left)
        model_dock = QDockWidget("Model", self)
        model_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self._model_tree = ModelTreeWidget()
        self._model_tree.set_model(self._model)
        model_dock.setWidget(self._model_tree)

        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, model_dock)

        # Properties dock (right)
        props_dock = QDockWidget("Properties", self)
        props_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self._property_panel = PropertyPanel()
        props_dock.setWidget(self._property_panel)

        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, props_dock)

        # Results dock (right, below properties)
        self._results_dock = QDockWidget("Results", self)
        self._results_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self._results_panel = ResultsPanel()
        self._results_dock.setWidget(self._results_panel)
        self._results_dock.hide()  # Hidden until analysis is run

        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._results_dock)

    def _setup_status_bar(self) -> None:
        """Create the status bar."""
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._tool_label = QLabel("Tool: Select")
        self._status_bar.addWidget(self._tool_label)

        self._coords_label = QLabel("X: 0.00  Y: 0.00  Z: 0.00")
        self._status_bar.addPermanentWidget(self._coords_label)

        self._count_label = QLabel("Nodes: 0  Frames: 0")
        self._status_bar.addPermanentWidget(self._count_label)

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        # Viewport node click - use for drawing
        self._viewport.node_clicked.connect(self._on_node_clicked)

        # Override viewport point picking for node creation
        # We'll handle this via a custom click handler
        self._viewport._plotter.add_key_event("n", self._quick_set_node_tool)
        self._viewport._plotter.add_key_event("f", self._quick_set_frame_tool)
        self._viewport._plotter.add_key_event("v", self._quick_set_select_tool)
        self._viewport._plotter.add_key_event("Escape", self._cancel_operation)

        # Custom point picking for node creation
        self._viewport._plotter.track_click_position(
            callback=self._on_viewport_click,
            side="left",
        )

        # Model tree signals
        self._model_tree.node_selected.connect(self._on_tree_node_selected)
        self._model_tree.frame_selected.connect(self._on_tree_frame_selected)
        self._model_tree.node_double_clicked.connect(self._on_edit_node)
        self._model_tree.frame_double_clicked.connect(self._on_edit_frame)
        self._model_tree.delete_node_requested.connect(self._on_delete_node)
        self._model_tree.delete_frame_requested.connect(self._on_delete_frame)

        # Property panel signals
        self._property_panel.node_modified.connect(self._on_node_property_changed)
        self._property_panel.frame_modified.connect(self._on_frame_property_changed)

    def _set_tool(self, tool: DrawingTool) -> None:
        """Set the active drawing tool."""
        self._current_tool = tool
        self._frame_start_node_id = None  # Reset frame drawing state

        # Update action states
        for action in self._tool_actions:
            action.setChecked(False)

        if tool == DrawingTool.SELECT:
            self._select_action.setChecked(True)
            self._tool_label.setText("Tool: Select")
        elif tool == DrawingTool.NODE:
            self._node_action.setChecked(True)
            self._tool_label.setText("Tool: Node (click to place)")
        elif tool == DrawingTool.FRAME:
            self._frame_action.setChecked(True)
            self._tool_label.setText("Tool: Frame (click first node)")

    def _quick_set_node_tool(self) -> None:
        """Keyboard shortcut for node tool."""
        self._set_tool(DrawingTool.NODE)

    def _quick_set_frame_tool(self) -> None:
        """Keyboard shortcut for frame tool."""
        self._set_tool(DrawingTool.FRAME)

    def _quick_set_select_tool(self) -> None:
        """Keyboard shortcut for select tool."""
        self._set_tool(DrawingTool.SELECT)

    def _cancel_operation(self) -> None:
        """Cancel current operation and return to select."""
        self._frame_start_node_id = None
        self._set_tool(DrawingTool.SELECT)
        self._status_bar.showMessage("Operation cancelled", 2000)

    def _on_viewport_click(self, click_pos: tuple[int, int]) -> None:
        """Handle click in viewport for node creation."""
        if self._current_tool == DrawingTool.NODE:
            # Get 3D position from click
            world_pos = self._get_world_position(click_pos)
            if world_pos is not None:
                self._create_node_at(world_pos)

    def _get_world_position(self, screen_pos: tuple[int, int]) -> tuple[float, float, float] | None:
        """Convert screen position to world coordinates on the XY plane (z=0)."""
        # Use PyVista's pick functionality
        picker = self._viewport._plotter.pick_click_position()

        if picker is not None and len(picker) == 3:
            x, y, z = picker
            # Snap to grid if enabled
            grid_config = self._viewport.get_grid_config()
            if grid_config.snap_enabled:
                x, y, z = grid_config.snap_point(x, y, z)
            return (x, y, z)

        # Fallback: project onto Z=0 plane
        # For now, return a default position
        return None

    def _create_node_at(self, pos: tuple[float, float, float]) -> None:
        """Create a node at the given position."""
        x, y, z = pos

        # Create command for undo/redo
        cmd = CreateNodeCommand(self._model, x, y, z)

        try:
            self._undo_service.execute(cmd)
            self._on_model_changed()
            self._status_bar.showMessage(f"Node created at ({x:.2f}, {y:.2f}, {z:.2f})", 2000)
        except Exception as e:
            self._status_bar.showMessage(f"Error: {e}", 3000)

    @Slot(int)
    def _on_node_clicked(self, node_id: int) -> None:
        """Handle node click from viewport."""
        if self._current_tool == DrawingTool.SELECT:
            self._show_node_properties(node_id)

        elif self._current_tool == DrawingTool.FRAME:
            if self._frame_start_node_id is None:
                # First click: store start node
                self._frame_start_node_id = node_id
                self._tool_label.setText(f"Tool: Frame (click second node, started from {node_id})")
                self._status_bar.showMessage(f"Frame start: Node {node_id}. Click second node.", 5000)
            else:
                # Second click: create frame
                if self._frame_start_node_id != node_id:
                    self._create_frame(self._frame_start_node_id, node_id)
                else:
                    self._status_bar.showMessage("Cannot create frame to same node", 2000)
                self._frame_start_node_id = None
                self._tool_label.setText("Tool: Frame (click first node)")

    def _create_frame(self, node_i_id: int, node_j_id: int) -> None:
        """Create a frame between two nodes."""
        cmd = CreateFrameCommand(
            self._model,
            node_i_id=node_i_id,
            node_j_id=node_j_id,
            material_name=self._default_material,
            section_name=self._default_section,
        )

        try:
            self._undo_service.execute(cmd)
            self._on_model_changed()
            self._status_bar.showMessage(f"Frame created: {node_i_id} -> {node_j_id}", 2000)
        except Exception as e:
            self._status_bar.showMessage(f"Error: {e}", 3000)

    def _show_node_properties(self, node_id: int) -> None:
        """Show properties for selected node."""
        try:
            node = self._model.get_node(node_id)
            self._property_panel.show_node(node)
            self._model_tree.select_node(node_id)
        except Exception:
            pass

    def _show_frame_properties(self, frame_id: int) -> None:
        """Show properties for selected frame."""
        try:
            frame = self._model.get_frame(frame_id)
            self._property_panel.show_frame(frame)
            self._model_tree.select_frame(frame_id)
        except Exception:
            pass

    def _on_model_changed(self) -> None:
        """Handle model data change."""
        self._viewport.set_model(self._model)
        self._update_model_tree()
        self._update_status_bar()
        self._update_undo_redo_actions()
        self._is_modified = True
        self._update_window_title()
        self.model_changed.emit()

    def _update_undo_redo_actions(self) -> None:
        """Update undo/redo action enabled states."""
        self._undo_action.setEnabled(self._undo_service.can_undo)
        self._redo_action.setEnabled(self._undo_service.can_redo)

    def _update_model_tree(self) -> None:
        """Update the model tree widget."""
        self._model_tree.set_model(self._model)
        self._model_tree.update_tree()

    def _update_status_bar(self) -> None:
        """Update status bar counts."""
        self._count_label.setText(f"Nodes: {self._model.node_count}  Frames: {self._model.frame_count}")

    @Slot()
    def _on_new_project(self) -> None:
        """Create a new empty project."""
        if self._is_modified:
            reply = QMessageBox.question(
                self,
                "New Project",
                "Current project has unsaved changes. Discard and start new?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._model.clear()
        self._undo_service.clear()
        self._project = Project(name="Untitled")
        self._project_path = None
        self._is_modified = False
        self._on_model_changed()
        self._update_window_title()
        self._status_bar.showMessage("New project created", 2000)

    @Slot()
    def _on_open_project(self) -> None:
        """Open an existing project file."""
        if self._is_modified:
            reply = QMessageBox.question(
                self,
                "Open Project",
                "Current project has unsaved changes. Discard and open?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "PAZ Files (*.paz);;All Files (*)",
        )

        if not file_path:
            return

        try:
            project_file = self._file_repository.load(file_path)
            self._project = project_file.project
            self._project_path = file_path

            # Load model from project file
            if project_file.model:
                self._model = StructuralModel.from_dict(project_file.model)
            else:
                self._model = StructuralModel()

            self._undo_service.clear()
            self._is_modified = False
            self._on_model_changed()
            self._update_window_title()
            self._status_bar.showMessage(f"Opened: {file_path}", 3000)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Opening Project",
                f"Failed to open project:\n{e}",
            )

    @Slot()
    def _on_save_project(self) -> None:
        """Save the current project."""
        if self._project_path is None:
            self._on_save_project_as()
            return

        self._save_to_path(self._project_path)

    @Slot()
    def _on_save_project_as(self) -> None:
        """Save the current project to a new file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            f"{self._project.name}.paz",
            "PAZ Files (*.paz);;All Files (*)",
        )

        if not file_path:
            return

        self._save_to_path(file_path)

    def _save_to_path(self, file_path: str) -> None:
        """Save the project to the specified path."""
        try:
            project_file = ProjectFile(
                project=self._project,
                model=self._model.to_dict(),
            )
            self._file_repository.save(project_file, file_path)
            self._project_path = file_path
            self._is_modified = False
            self._update_window_title()
            self._status_bar.showMessage(f"Saved: {file_path}", 3000)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Saving Project",
                f"Failed to save project:\n{e}",
            )

    def _update_window_title(self) -> None:
        """Update the window title with project name and modified status."""
        title = f"PAZ - {self._project.name}"
        if self._is_modified:
            title += " *"
        self.setWindowTitle(title)

    @Slot()
    def _on_select_material(self) -> None:
        """Open the material selection dialog."""
        dialog = MaterialDialog(
            self,
            repository=self._materials_repository,
            current_material=self._default_material,
        )

        if dialog.exec() == MaterialDialog.DialogCode.Accepted:
            material_name = dialog.get_selected_material_name()
            if material_name:
                self._default_material = material_name
                self._status_bar.showMessage(f"Material: {material_name}", 2000)

    @Slot()
    def _on_select_section(self) -> None:
        """Open the section selection dialog."""
        dialog = SectionDialog(
            self,
            repository=self._sections_repository,
            current_section=self._default_section,
        )

        if dialog.exec() == SectionDialog.DialogCode.Accepted:
            section_name = dialog.get_selected_section_name()
            if section_name:
                self._default_section = section_name
                self._status_bar.showMessage(f"Section: {section_name}", 2000)

    @Slot()
    def _on_undo(self) -> None:
        """Undo last action."""
        if self._undo_service.can_undo:
            self._undo_service.undo()
            self._on_model_changed()
            self._status_bar.showMessage("Undo", 1000)

    @Slot()
    def _on_redo(self) -> None:
        """Redo last undone action."""
        if self._undo_service.can_redo:
            self._undo_service.redo()
            self._on_model_changed()
            self._status_bar.showMessage("Redo", 1000)

    @Slot()
    def _on_reset_view(self) -> None:
        """Reset viewport camera."""
        self._viewport.reset_camera()

    @Slot()
    def _on_delete(self) -> None:
        """Delete selected elements."""
        # TODO: Implement proper selection-based deletion
        self._status_bar.showMessage("Delete: Select elements first", 2000)

    @Slot()
    def _on_select_all(self) -> None:
        """Select all elements."""
        # TODO: Implement proper selection
        node_count = self._model.node_count
        frame_count = self._model.frame_count
        self._status_bar.showMessage(
            f"Selected: {node_count} nodes, {frame_count} frames", 2000
        )

    @Slot()
    def _on_add_node_dialog(self) -> None:
        """Open dialog to add a new node."""
        dialog = NodeDialog(self, title="Add Node")

        if dialog.exec() == NodeDialog.DialogCode.Accepted:
            data = dialog.get_node_data()
            cmd = CreateNodeCommand(
                self._model,
                data["x"],
                data["y"],
                data["z"],
                restraint=data["restraint"],
            )
            try:
                self._undo_service.execute(cmd)
                self._on_model_changed()
                self._status_bar.showMessage(
                    f"Node created at ({data['x']:.2f}, {data['y']:.2f}, {data['z']:.2f})",
                    2000,
                )
            except Exception as e:
                self._status_bar.showMessage(f"Error: {e}", 3000)

    @Slot()
    def _on_add_frame_dialog(self) -> None:
        """Open dialog to configure frame properties before creation."""
        dialog = FrameDialog(
            self,
            materials_repo=self._materials_repository,
            sections_repo=self._sections_repository,
            title="Frame Properties",
        )

        if dialog.exec() == FrameDialog.DialogCode.Accepted:
            self._default_material = dialog.get_material_name()
            self._default_section = dialog.get_section_name()
            # Switch to frame tool for drawing
            self._set_tool(DrawingTool.FRAME)
            self._status_bar.showMessage(
                f"Frame tool active: {self._default_section} ({self._default_material}). Click two nodes.",
                5000,
            )

    @Slot()
    def _on_run_analysis(self) -> None:
        """Run structural analysis."""
        # Check if model is valid for analysis
        if self._model.node_count < 2:
            QMessageBox.warning(
                self,
                "Cannot Run Analysis",
                "Model must have at least 2 nodes.",
            )
            return

        if self._model.frame_count < 1:
            QMessageBox.warning(
                self,
                "Cannot Run Analysis",
                "Model must have at least 1 frame.",
            )
            return

        # Check for supports
        has_support = any(node.is_supported for node in self._model.nodes)
        if not has_support:
            QMessageBox.warning(
                self,
                "Cannot Run Analysis",
                "Model must have at least one supported node.",
            )
            return

        self._status_bar.showMessage("Running analysis...", 0)

        # Prepare materials and sections dictionaries
        materials = {m.name: m for m in self._materials_repository.get_all()}
        sections = {s.name: s for s in self._sections_repository.get_all()}

        # Create default load case (self-weight)
        load_case = LoadCase(
            name="Self-Weight",
            load_type=LoadCaseType.DEAD,
            self_weight_multiplier=1.0,
        )

        # Progress callback
        def on_progress(step: int, total: int, message: str) -> None:
            self._status_bar.showMessage(f"Analysis: {message} ({step}/{total})", 0)

        try:
            # Run analysis
            results = self._analysis_service.analyze(
                model=self._model,
                materials=materials,
                sections=sections,
                load_case=load_case,
                nodal_loads=[],
                distributed_loads=[],
                progress_callback=on_progress,
            )

            self._analysis_results = results

            if results.success:
                self._status_bar.showMessage("Analysis completed successfully", 3000)
                # Show results panel
                self._results_panel.set_results(results)
                self._results_dock.show()
                # Update viewport to show deformed shape if available
                self._viewport.set_results(results)
            else:
                QMessageBox.warning(
                    self,
                    "Analysis Failed",
                    f"Analysis failed:\n{results.error_message}",
                )
                self._status_bar.showMessage("Analysis failed", 3000)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Analysis Error",
                f"An error occurred during analysis:\n{e}",
            )
            self._status_bar.showMessage("Analysis error", 3000)

    @Slot()
    def _on_view_results(self) -> None:
        """View analysis results."""
        if self._analysis_results is None:
            QMessageBox.information(
                self,
                "No Results",
                "No analysis results available.\nRun analysis first (F5).",
            )
            return

        # Show results dock if hidden
        self._results_dock.show()
        self._results_panel.set_results(self._analysis_results)
        self._status_bar.showMessage("Viewing results", 2000)

    @Slot(int)
    def _on_tree_node_selected(self, node_id: int) -> None:
        """Handle node selection from model tree."""
        self._show_node_properties(node_id)

    @Slot(int)
    def _on_tree_frame_selected(self, frame_id: int) -> None:
        """Handle frame selection from model tree."""
        self._show_frame_properties(frame_id)

    @Slot(int)
    def _on_edit_node(self, node_id: int) -> None:
        """Open dialog to edit an existing node."""
        try:
            node = self._model.get_node(node_id)
            dialog = NodeDialog(self, title=f"Edit Node {node_id}", node=node)

            if dialog.exec() == NodeDialog.DialogCode.Accepted:
                data = dialog.get_node_data()
                node.move_to(data["x"], data["y"], data["z"])
                node.restraint = data["restraint"]
                self._on_model_changed()
                self._show_node_properties(node_id)
                self._status_bar.showMessage(f"Node {node_id} updated", 2000)
        except Exception as e:
            self._status_bar.showMessage(f"Error: {e}", 3000)

    @Slot(int)
    def _on_edit_frame(self, frame_id: int) -> None:
        """Open dialog to edit an existing frame."""
        try:
            frame = self._model.get_frame(frame_id)
            dialog = FrameDialog(
                self,
                materials_repo=self._materials_repository,
                sections_repo=self._sections_repository,
                title=f"Edit Frame {frame_id}",
                frame=frame,
            )

            if dialog.exec() == FrameDialog.DialogCode.Accepted:
                frame.material_name = dialog.get_material_name()
                frame.section_name = dialog.get_section_name()
                frame.rotation = dialog.get_rotation()
                frame.releases = dialog.get_releases()
                frame.label = dialog.get_label()
                self._on_model_changed()
                self._show_frame_properties(frame_id)
                self._status_bar.showMessage(f"Frame {frame_id} updated", 2000)
        except Exception as e:
            self._status_bar.showMessage(f"Error: {e}", 3000)

    @Slot(int)
    def _on_delete_node(self, node_id: int) -> None:
        """Delete a node from the model."""
        try:
            self._model.remove_node(node_id)
            self._property_panel.clear()
            self._on_model_changed()
            self._status_bar.showMessage(f"Node {node_id} deleted", 2000)
        except Exception as e:
            self._status_bar.showMessage(f"Error: {e}", 3000)

    @Slot(int)
    def _on_delete_frame(self, frame_id: int) -> None:
        """Delete a frame from the model."""
        try:
            self._model.remove_frame(frame_id)
            self._property_panel.clear()
            self._on_model_changed()
            self._status_bar.showMessage(f"Frame {frame_id} deleted", 2000)
        except Exception as e:
            self._status_bar.showMessage(f"Error: {e}", 3000)

    @Slot(int, dict)
    def _on_node_property_changed(self, node_id: int, properties: dict) -> None:
        """Handle property change from property panel."""
        try:
            node = self._model.get_node(node_id)

            if "x" in properties or "y" in properties or "z" in properties:
                x = properties.get("x", node.x)
                y = properties.get("y", node.y)
                z = properties.get("z", node.z)
                node.move_to(x, y, z)

            if "restraint" in properties:
                node.restraint = properties["restraint"]

            self._on_model_changed()
        except Exception as e:
            self._status_bar.showMessage(f"Error: {e}", 3000)

    @Slot(int, dict)
    def _on_frame_property_changed(self, frame_id: int, properties: dict) -> None:
        """Handle property change from property panel."""
        try:
            frame = self._model.get_frame(frame_id)

            if "rotation" in properties:
                frame.rotation = properties["rotation"]
            if "label" in properties:
                frame.label = properties["label"]
            if "releases" in properties:
                frame.releases = properties["releases"]

            self._on_model_changed()
        except Exception as e:
            self._status_bar.showMessage(f"Error: {e}", 3000)

    def get_model(self) -> StructuralModel:
        """Get the current structural model."""
        return self._model

    def set_model(self, model: StructuralModel) -> None:
        """Set a new structural model."""
        self._model = model
        self._undo_service.clear()
        self._on_model_changed()


def run_main_window() -> int:
    """Run the main window application."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    window = MainWindow()
    window.show()

    return app.exec()

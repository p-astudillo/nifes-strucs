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
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from paz.application.commands import CreateNodeCommand, CreateFrameCommand
from paz.application.services import UndoRedoService
from paz.core.grid_config import GridConfig
from paz.domain.model import StructuralModel
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
        self._default_material = "Steel"
        self._default_section = "W14x22"

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

        # View menu
        view_menu = menubar.addMenu("&View")

        reset_view_action = QAction("&Reset View", self)
        reset_view_action.setShortcut("R")
        reset_view_action.triggered.connect(self._on_reset_view)
        view_menu.addAction(reset_view_action)

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

        self._model_tree = QTreeWidget()
        self._model_tree.setHeaderLabels(["Element", "Count"])
        self._model_tree.setColumnCount(2)
        model_dock.setWidget(self._model_tree)

        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, model_dock)

        # Properties dock (right)
        props_dock = QDockWidget("Properties", self)
        props_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        props_widget = QWidget()
        props_layout = QVBoxLayout(props_widget)
        self._props_label = QLabel("Select an element to see properties")
        self._props_label.setWordWrap(True)
        props_layout.addWidget(self._props_label)
        props_layout.addStretch()
        props_dock.setWidget(props_widget)

        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, props_dock)

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
            text = (
                f"Node {node.id}\n\n"
                f"X: {node.x:.4f} m\n"
                f"Y: {node.y:.4f} m\n"
                f"Z: {node.z:.4f} m\n\n"
                f"Restraint:\n"
                f"  Ux: {'Fixed' if node.restraint.ux else 'Free'}\n"
                f"  Uy: {'Fixed' if node.restraint.uy else 'Free'}\n"
                f"  Uz: {'Fixed' if node.restraint.uz else 'Free'}\n"
                f"  Rx: {'Fixed' if node.restraint.rx else 'Free'}\n"
                f"  Ry: {'Fixed' if node.restraint.ry else 'Free'}\n"
                f"  Rz: {'Fixed' if node.restraint.rz else 'Free'}"
            )
            self._props_label.setText(text)
        except Exception:
            pass

    def _on_model_changed(self) -> None:
        """Handle model data change."""
        self._viewport.set_model(self._model)
        self._update_model_tree()
        self._update_status_bar()
        self._update_undo_redo_actions()
        self.model_changed.emit()

    def _update_undo_redo_actions(self) -> None:
        """Update undo/redo action enabled states."""
        self._undo_action.setEnabled(self._undo_service.can_undo)
        self._redo_action.setEnabled(self._undo_service.can_redo)

    def _update_model_tree(self) -> None:
        """Update the model tree widget."""
        self._model_tree.clear()

        # Nodes
        nodes_item = QTreeWidgetItem(["Nodes", str(self._model.node_count)])
        for node in self._model.nodes:
            node_item = QTreeWidgetItem([f"Node {node.id}", f"({node.x:.2f}, {node.y:.2f}, {node.z:.2f})"])
            nodes_item.addChild(node_item)
        self._model_tree.addTopLevelItem(nodes_item)

        # Frames
        frames_item = QTreeWidgetItem(["Frames", str(self._model.frame_count)])
        for frame in self._model.frames:
            frame_item = QTreeWidgetItem([f"Frame {frame.id}", f"{frame.node_i_id} -> {frame.node_j_id}"])
            frames_item.addChild(frame_item)
        self._model_tree.addTopLevelItem(frames_item)

        # Expand nodes and frames
        nodes_item.setExpanded(True)
        frames_item.setExpanded(True)

    def _update_status_bar(self) -> None:
        """Update status bar counts."""
        self._count_label.setText(f"Nodes: {self._model.node_count}  Frames: {self._model.frame_count}")

    @Slot()
    def _on_new_project(self) -> None:
        """Create a new empty project."""
        reply = QMessageBox.question(
            self,
            "New Project",
            "Clear current model and start new project?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._model.clear()
            self._undo_service.clear()
            self._on_model_changed()
            self._status_bar.showMessage("New project created", 2000)

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
        # TODO: Implement selection and deletion
        self._status_bar.showMessage("Delete: No selection", 2000)

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

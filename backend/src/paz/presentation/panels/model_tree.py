"""
Model tree widget for displaying structural model hierarchy.

Shows nodes, frames, materials, and sections with interactive selection
and context menu support.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


if TYPE_CHECKING:
    from paz.domain.model import StructuralModel


class ElementType(Enum):
    """Type of element in the model tree."""

    CATEGORY = auto()
    NODE = auto()
    FRAME = auto()
    MATERIAL = auto()
    SECTION = auto()


class ModelTreeWidget(QWidget):
    """
    Tree widget displaying structural model hierarchy.

    Shows categorized lists of:
    - Nodes with coordinates
    - Frames with node connections
    - Materials (from repository)
    - Sections (from repository)

    Signals:
        node_selected(int): Emitted when a node is selected
        frame_selected(int): Emitted when a frame is selected
        node_double_clicked(int): Emitted when a node is double-clicked (edit)
        frame_double_clicked(int): Emitted when a frame is double-clicked (edit)
        delete_node_requested(int): Emitted when delete is requested for a node
        delete_frame_requested(int): Emitted when delete is requested for a frame
    """

    node_selected = Signal(int)
    frame_selected = Signal(int)
    node_double_clicked = Signal(int)
    frame_double_clicked = Signal(int)
    delete_node_requested = Signal(int)
    delete_frame_requested = Signal(int)

    # Role for storing element data
    ELEMENT_TYPE_ROLE = Qt.ItemDataRole.UserRole
    ELEMENT_ID_ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the model tree."""
        super().__init__(parent)

        self._model: StructuralModel | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create the tree widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Element", "Info"])
        self._tree.setColumnCount(2)
        self._tree.setAlternatingRowColors(True)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)

        # Connect signals
        self._tree.itemSelectionChanged.connect(self._on_selection_changed)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)

        layout.addWidget(self._tree)

        # Create category items
        self._nodes_item = QTreeWidgetItem(["Nodes", "0"])
        self._nodes_item.setData(0, self.ELEMENT_TYPE_ROLE, ElementType.CATEGORY)
        self._nodes_item.setFlags(
            self._nodes_item.flags() & ~Qt.ItemFlag.ItemIsSelectable
        )

        self._frames_item = QTreeWidgetItem(["Frames", "0"])
        self._frames_item.setData(0, self.ELEMENT_TYPE_ROLE, ElementType.CATEGORY)
        self._frames_item.setFlags(
            self._frames_item.flags() & ~Qt.ItemFlag.ItemIsSelectable
        )

        self._materials_item = QTreeWidgetItem(["Materials", "0"])
        self._materials_item.setData(0, self.ELEMENT_TYPE_ROLE, ElementType.CATEGORY)
        self._materials_item.setFlags(
            self._materials_item.flags() & ~Qt.ItemFlag.ItemIsSelectable
        )

        self._sections_item = QTreeWidgetItem(["Sections", "0"])
        self._sections_item.setData(0, self.ELEMENT_TYPE_ROLE, ElementType.CATEGORY)
        self._sections_item.setFlags(
            self._sections_item.flags() & ~Qt.ItemFlag.ItemIsSelectable
        )

        self._tree.addTopLevelItem(self._nodes_item)
        self._tree.addTopLevelItem(self._frames_item)
        self._tree.addTopLevelItem(self._materials_item)
        self._tree.addTopLevelItem(self._sections_item)

        # Expand nodes and frames by default
        self._nodes_item.setExpanded(True)
        self._frames_item.setExpanded(True)

        # Adjust column widths
        self._tree.setColumnWidth(0, 150)

    def set_model(self, model: StructuralModel) -> None:
        """
        Set the structural model to display.

        Args:
            model: The structural model
        """
        self._model = model
        self.update_tree()

    def update_tree(self) -> None:
        """Update tree contents from the current model."""
        if self._model is None:
            return

        # Clear children
        self._nodes_item.takeChildren()
        self._frames_item.takeChildren()

        # Add nodes
        for node in self._model.nodes:
            item = QTreeWidgetItem([
                f"Node {node.id}",
                f"({node.x:.2f}, {node.y:.2f}, {node.z:.2f})",
            ])
            item.setData(0, self.ELEMENT_TYPE_ROLE, ElementType.NODE)
            item.setData(0, self.ELEMENT_ID_ROLE, node.id)

            # Add restraint indicator
            if node.is_supported:
                item.setText(0, f"Node {node.id} [S]")

            self._nodes_item.addChild(item)

        # Add frames
        for frame in self._model.frames:
            label = f"Frame {frame.id}"
            if frame.label:
                label = f"{label} ({frame.label})"

            item = QTreeWidgetItem([
                label,
                f"{frame.node_i_id} -> {frame.node_j_id}",
            ])
            item.setData(0, self.ELEMENT_TYPE_ROLE, ElementType.FRAME)
            item.setData(0, self.ELEMENT_ID_ROLE, frame.id)

            # Add section/material info
            item.setToolTip(0, f"{frame.section_name} / {frame.material_name}")

            self._frames_item.addChild(item)

        # Update counts
        self._nodes_item.setText(1, str(self._model.node_count))
        self._frames_item.setText(1, str(self._model.frame_count))

    def set_materials(self, materials: list[str]) -> None:
        """
        Set the list of available materials.

        Args:
            materials: List of material names
        """
        self._materials_item.takeChildren()

        for name in materials:
            item = QTreeWidgetItem([name, ""])
            item.setData(0, self.ELEMENT_TYPE_ROLE, ElementType.MATERIAL)
            self._materials_item.addChild(item)

        self._materials_item.setText(1, str(len(materials)))

    def set_sections(self, sections: list[str]) -> None:
        """
        Set the list of available sections.

        Args:
            sections: List of section names
        """
        self._sections_item.takeChildren()

        for name in sections:
            item = QTreeWidgetItem([name, ""])
            item.setData(0, self.ELEMENT_TYPE_ROLE, ElementType.SECTION)
            self._sections_item.addChild(item)

        self._sections_item.setText(1, str(len(sections)))

    def select_node(self, node_id: int) -> None:
        """
        Select a node in the tree.

        Args:
            node_id: ID of the node to select
        """
        for i in range(self._nodes_item.childCount()):
            item = self._nodes_item.child(i)
            if item.data(0, self.ELEMENT_ID_ROLE) == node_id:
                self._tree.setCurrentItem(item)
                break

    def select_frame(self, frame_id: int) -> None:
        """
        Select a frame in the tree.

        Args:
            frame_id: ID of the frame to select
        """
        for i in range(self._frames_item.childCount()):
            item = self._frames_item.child(i)
            if item.data(0, self.ELEMENT_ID_ROLE) == frame_id:
                self._tree.setCurrentItem(item)
                break

    def clear_selection(self) -> None:
        """Clear the current selection."""
        self._tree.clearSelection()

    def _on_selection_changed(self) -> None:
        """Handle selection change."""
        items = self._tree.selectedItems()
        if not items:
            return

        item = items[0]
        elem_type = item.data(0, self.ELEMENT_TYPE_ROLE)
        elem_id = item.data(0, self.ELEMENT_ID_ROLE)

        if elem_type == ElementType.NODE and elem_id is not None:
            self.node_selected.emit(elem_id)
        elif elem_type == ElementType.FRAME and elem_id is not None:
            self.frame_selected.emit(elem_id)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item double-click."""
        elem_type = item.data(0, self.ELEMENT_TYPE_ROLE)
        elem_id = item.data(0, self.ELEMENT_ID_ROLE)

        if elem_type == ElementType.NODE and elem_id is not None:
            self.node_double_clicked.emit(elem_id)
        elif elem_type == ElementType.FRAME and elem_id is not None:
            self.frame_double_clicked.emit(elem_id)

    def _on_context_menu(self, pos) -> None:
        """Handle context menu request."""
        item = self._tree.itemAt(pos)
        if not item:
            return

        elem_type = item.data(0, self.ELEMENT_TYPE_ROLE)
        elem_id = item.data(0, self.ELEMENT_ID_ROLE)

        if elem_type not in (ElementType.NODE, ElementType.FRAME):
            return

        menu = QMenu(self)

        if elem_type == ElementType.NODE:
            edit_action = QAction("Edit Node...", self)
            edit_action.triggered.connect(lambda: self.node_double_clicked.emit(elem_id))
            menu.addAction(edit_action)

            menu.addSeparator()

            delete_action = QAction("Delete Node", self)
            delete_action.triggered.connect(lambda: self.delete_node_requested.emit(elem_id))
            menu.addAction(delete_action)

        elif elem_type == ElementType.FRAME:
            edit_action = QAction("Edit Frame...", self)
            edit_action.triggered.connect(lambda: self.frame_double_clicked.emit(elem_id))
            menu.addAction(edit_action)

            menu.addSeparator()

            delete_action = QAction("Delete Frame", self)
            delete_action.triggered.connect(lambda: self.delete_frame_requested.emit(elem_id))
            menu.addAction(delete_action)

        menu.exec(self._tree.mapToGlobal(pos))

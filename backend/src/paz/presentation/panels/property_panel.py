"""
Property panel for viewing and editing element properties.

Displays properties for selected nodes and frames with inline editing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from paz.domain.model.restraint import Restraint


if TYPE_CHECKING:
    from paz.domain.model.frame import Frame
    from paz.domain.model.node import Node


class PropertyPanel(QWidget):
    """
    Panel for viewing and editing element properties.

    Supports:
    - Node properties: coordinates, restraints
    - Frame properties: material, section, rotation, releases, label

    Signals:
        node_modified(int, dict): Node ID and new property values
        frame_modified(int, dict): Frame ID and new property values
    """

    node_modified = Signal(int, dict)
    frame_modified = Signal(int, dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the property panel."""
        super().__init__(parent)

        self._current_node: Node | None = None
        self._current_frame: Frame | None = None
        self._updating = False  # Prevent recursive updates

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)

        # Empty state label
        self._empty_label = QLabel("Select an element to view properties")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: gray; padding: 20px;")
        self._content_layout.addWidget(self._empty_label)

        # Node properties group (hidden by default)
        self._node_group = self._create_node_group()
        self._node_group.hide()
        self._content_layout.addWidget(self._node_group)

        # Frame properties group (hidden by default)
        self._frame_group = self._create_frame_group()
        self._frame_group.hide()
        self._content_layout.addWidget(self._frame_group)

        self._content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_node_group(self) -> QGroupBox:
        """Create node properties group."""
        group = QGroupBox("Node Properties")
        layout = QFormLayout(group)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        # ID (readonly)
        self._node_id_label = QLabel("-")
        layout.addRow("ID:", self._node_id_label)

        # Coordinates
        self._node_x = QDoubleSpinBox()
        self._node_x.setRange(-1e6, 1e6)
        self._node_x.setDecimals(4)
        self._node_x.setSuffix(" m")
        self._node_x.valueChanged.connect(self._on_node_coord_changed)
        layout.addRow("X:", self._node_x)

        self._node_y = QDoubleSpinBox()
        self._node_y.setRange(-1e6, 1e6)
        self._node_y.setDecimals(4)
        self._node_y.setSuffix(" m")
        self._node_y.valueChanged.connect(self._on_node_coord_changed)
        layout.addRow("Y:", self._node_y)

        self._node_z = QDoubleSpinBox()
        self._node_z.setRange(-1e6, 1e6)
        self._node_z.setDecimals(4)
        self._node_z.setSuffix(" m")
        self._node_z.valueChanged.connect(self._on_node_coord_changed)
        layout.addRow("Z:", self._node_z)

        # Restraint preset
        self._restraint_preset = QComboBox()
        self._restraint_preset.addItems(["Free", "Fixed", "Pinned", "Roller X", "Roller Y"])
        self._restraint_preset.currentTextChanged.connect(self._on_restraint_preset_changed)
        layout.addRow("Restraint:", self._restraint_preset)

        # Individual restraints
        restraint_widget = QWidget()
        restraint_layout = QHBoxLayout(restraint_widget)
        restraint_layout.setContentsMargins(0, 0, 0, 0)
        restraint_layout.setSpacing(8)

        self._restraint_ux = QCheckBox("Ux")
        self._restraint_uy = QCheckBox("Uy")
        self._restraint_uz = QCheckBox("Uz")
        self._restraint_rx = QCheckBox("Rx")
        self._restraint_ry = QCheckBox("Ry")
        self._restraint_rz = QCheckBox("Rz")

        for cb in [self._restraint_ux, self._restraint_uy, self._restraint_uz,
                   self._restraint_rx, self._restraint_ry, self._restraint_rz]:
            cb.stateChanged.connect(self._on_restraint_checkbox_changed)
            restraint_layout.addWidget(cb)

        layout.addRow("", restraint_widget)

        return group

    def _create_frame_group(self) -> QGroupBox:
        """Create frame properties group."""
        group = QGroupBox("Frame Properties")
        layout = QFormLayout(group)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        # ID (readonly)
        self._frame_id_label = QLabel("-")
        layout.addRow("ID:", self._frame_id_label)

        # Nodes (readonly)
        self._frame_nodes_label = QLabel("-")
        layout.addRow("Nodes:", self._frame_nodes_label)

        # Length (readonly)
        self._frame_length_label = QLabel("-")
        layout.addRow("Length:", self._frame_length_label)

        # Material
        self._frame_material = QLineEdit()
        self._frame_material.setReadOnly(True)
        self._frame_material.setStyleSheet("background-color: #f5f5f5;")
        layout.addRow("Material:", self._frame_material)

        # Section
        self._frame_section = QLineEdit()
        self._frame_section.setReadOnly(True)
        self._frame_section.setStyleSheet("background-color: #f5f5f5;")
        layout.addRow("Section:", self._frame_section)

        # Rotation
        self._frame_rotation = QDoubleSpinBox()
        self._frame_rotation.setRange(-180, 180)
        self._frame_rotation.setDecimals(2)
        self._frame_rotation.setSuffix(" deg")
        self._frame_rotation.valueChanged.connect(self._on_frame_rotation_changed)
        layout.addRow("Rotation:", self._frame_rotation)

        # Label
        self._frame_label = QLineEdit()
        self._frame_label.setPlaceholderText("Optional label")
        self._frame_label.editingFinished.connect(self._on_frame_label_changed)
        layout.addRow("Label:", self._frame_label)

        # Releases preset
        self._releases_preset = QComboBox()
        self._releases_preset.addItems([
            "Fixed-Fixed",
            "Pinned-Pinned",
            "Fixed-Pinned",
            "Pinned-Fixed",
        ])
        self._releases_preset.currentTextChanged.connect(self._on_releases_preset_changed)
        layout.addRow("Releases:", self._releases_preset)

        # Releases summary (readonly)
        self._releases_summary = QLabel("-")
        self._releases_summary.setWordWrap(True)
        self._releases_summary.setStyleSheet("color: gray; font-size: 11px;")
        layout.addRow("", self._releases_summary)

        return group

    def show_node(self, node: Node) -> None:
        """
        Display properties for a node.

        Args:
            node: The node to display
        """
        self._current_node = node
        self._current_frame = None

        self._updating = True

        # Update UI
        self._empty_label.hide()
        self._frame_group.hide()
        self._node_group.show()

        # Set values
        self._node_id_label.setText(str(node.id))
        self._node_x.setValue(node.x)
        self._node_y.setValue(node.y)
        self._node_z.setValue(node.z)

        # Set restraint checkboxes
        self._restraint_ux.setChecked(node.restraint.ux)
        self._restraint_uy.setChecked(node.restraint.uy)
        self._restraint_uz.setChecked(node.restraint.uz)
        self._restraint_rx.setChecked(node.restraint.rx)
        self._restraint_ry.setChecked(node.restraint.ry)
        self._restraint_rz.setChecked(node.restraint.rz)

        # Update preset combo
        self._update_restraint_preset()

        self._updating = False

    def show_frame(self, frame: Frame, length: float | None = None) -> None:
        """
        Display properties for a frame.

        Args:
            frame: The frame to display
            length: Optional pre-calculated length
        """
        self._current_node = None
        self._current_frame = frame

        self._updating = True

        # Update UI
        self._empty_label.hide()
        self._node_group.hide()
        self._frame_group.show()

        # Set values
        self._frame_id_label.setText(str(frame.id))
        self._frame_nodes_label.setText(f"{frame.node_i_id} -> {frame.node_j_id}")

        if length is not None:
            self._frame_length_label.setText(f"{length:.4f} m")
        else:
            try:
                calc_length = frame.length()
                self._frame_length_label.setText(f"{calc_length:.4f} m")
            except Exception:
                self._frame_length_label.setText("-")

        self._frame_material.setText(frame.material_name)
        self._frame_section.setText(frame.section_name)
        self._frame_rotation.setValue(frame.rotation * 180.0 / 3.14159265)  # rad to deg
        self._frame_label.setText(frame.label)

        # Update releases preset
        self._update_releases_preset()
        self._update_releases_summary()

        self._updating = False

    def clear(self) -> None:
        """Clear the property display."""
        self._current_node = None
        self._current_frame = None

        self._node_group.hide()
        self._frame_group.hide()
        self._empty_label.show()

    def _update_restraint_preset(self) -> None:
        """Update restraint preset combo based on checkbox states."""
        r = self._current_node.restraint if self._current_node else None
        if not r:
            return

        # Check for known presets
        if r.is_free:
            self._restraint_preset.setCurrentText("Free")
        elif r.is_fully_fixed:
            self._restraint_preset.setCurrentText("Fixed")
        elif r.ux and r.uy and r.uz and not r.rx and not r.ry and not r.rz:
            self._restraint_preset.setCurrentText("Pinned")
        elif r.uy and r.uz and not r.ux and not r.rx and not r.ry and not r.rz:
            self._restraint_preset.setCurrentText("Roller X")
        elif r.ux and r.uz and not r.uy and not r.rx and not r.ry and not r.rz:
            self._restraint_preset.setCurrentText("Roller Y")
        # If no preset matches, leave as-is

    def _update_releases_preset(self) -> None:
        """Update releases preset combo based on current releases."""
        if not self._current_frame:
            return

        rel = self._current_frame.releases

        if rel.is_fully_fixed():
            self._releases_preset.setCurrentText("Fixed-Fixed")
        elif (rel.M2_i and rel.M3_i and rel.M2_j and rel.M3_j and
              not rel.P_i and not rel.P_j):
            self._releases_preset.setCurrentText("Pinned-Pinned")
        elif (rel.M2_j and rel.M3_j and
              not rel.M2_i and not rel.M3_i):
            self._releases_preset.setCurrentText("Fixed-Pinned")
        elif (rel.M2_i and rel.M3_i and
              not rel.M2_j and not rel.M3_j):
            self._releases_preset.setCurrentText("Pinned-Fixed")

    def _update_releases_summary(self) -> None:
        """Update releases summary text."""
        if not self._current_frame:
            return

        rel = self._current_frame.releases
        parts = []

        if rel.M2_i or rel.M3_i:
            parts.append("i: moment released")
        if rel.M2_j or rel.M3_j:
            parts.append("j: moment released")
        if rel.P_i:
            parts.append("i: axial released")
        if rel.P_j:
            parts.append("j: axial released")

        if parts:
            self._releases_summary.setText(", ".join(parts))
        else:
            self._releases_summary.setText("All DOFs fixed")

    def _on_node_coord_changed(self) -> None:
        """Handle node coordinate change."""
        if self._updating or not self._current_node:
            return

        self.node_modified.emit(self._current_node.id, {
            "x": self._node_x.value(),
            "y": self._node_y.value(),
            "z": self._node_z.value(),
        })

    def _on_restraint_preset_changed(self, text: str) -> None:
        """Handle restraint preset change."""
        if self._updating or not self._current_node:
            return

        self._updating = True

        if text == "Free":
            for cb in [self._restraint_ux, self._restraint_uy, self._restraint_uz,
                       self._restraint_rx, self._restraint_ry, self._restraint_rz]:
                cb.setChecked(False)
        elif text == "Fixed":
            for cb in [self._restraint_ux, self._restraint_uy, self._restraint_uz,
                       self._restraint_rx, self._restraint_ry, self._restraint_rz]:
                cb.setChecked(True)
        elif text == "Pinned":
            self._restraint_ux.setChecked(True)
            self._restraint_uy.setChecked(True)
            self._restraint_uz.setChecked(True)
            self._restraint_rx.setChecked(False)
            self._restraint_ry.setChecked(False)
            self._restraint_rz.setChecked(False)
        elif text == "Roller X":
            self._restraint_ux.setChecked(False)
            self._restraint_uy.setChecked(True)
            self._restraint_uz.setChecked(True)
            self._restraint_rx.setChecked(False)
            self._restraint_ry.setChecked(False)
            self._restraint_rz.setChecked(False)
        elif text == "Roller Y":
            self._restraint_ux.setChecked(True)
            self._restraint_uy.setChecked(False)
            self._restraint_uz.setChecked(True)
            self._restraint_rx.setChecked(False)
            self._restraint_ry.setChecked(False)
            self._restraint_rz.setChecked(False)

        self._updating = False
        self._emit_restraint_change()

    def _on_restraint_checkbox_changed(self) -> None:
        """Handle individual restraint checkbox change."""
        if self._updating or not self._current_node:
            return

        self._update_restraint_preset()
        self._emit_restraint_change()

    def _emit_restraint_change(self) -> None:
        """Emit node modification signal for restraint change."""
        if not self._current_node:
            return

        restraint = Restraint(
            ux=self._restraint_ux.isChecked(),
            uy=self._restraint_uy.isChecked(),
            uz=self._restraint_uz.isChecked(),
            rx=self._restraint_rx.isChecked(),
            ry=self._restraint_ry.isChecked(),
            rz=self._restraint_rz.isChecked(),
        )
        self.node_modified.emit(self._current_node.id, {"restraint": restraint})

    def _on_frame_rotation_changed(self) -> None:
        """Handle frame rotation change."""
        if self._updating or not self._current_frame:
            return

        rotation_rad = self._frame_rotation.value() * 3.14159265 / 180.0
        self.frame_modified.emit(self._current_frame.id, {"rotation": rotation_rad})

    def _on_frame_label_changed(self) -> None:
        """Handle frame label change."""
        if self._updating or not self._current_frame:
            return

        self.frame_modified.emit(self._current_frame.id, {"label": self._frame_label.text()})

    def _on_releases_preset_changed(self, text: str) -> None:
        """Handle releases preset change."""
        if self._updating or not self._current_frame:
            return

        from paz.domain.model.frame import FrameReleases

        if text == "Fixed-Fixed":
            releases = FrameReleases.fixed_fixed()
        elif text == "Pinned-Pinned":
            releases = FrameReleases.pinned_pinned()
        elif text == "Fixed-Pinned":
            releases = FrameReleases.fixed_pinned()
        elif text == "Pinned-Fixed":
            releases = FrameReleases.pinned_fixed()
        else:
            return

        self._update_releases_summary()
        self.frame_modified.emit(self._current_frame.id, {"releases": releases})

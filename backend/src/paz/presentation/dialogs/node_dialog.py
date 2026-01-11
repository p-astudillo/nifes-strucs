"""
Node editing dialog for PAZ structural analysis software.

Provides UI for creating and editing structural nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from paz.domain.model.node import Node
from paz.domain.model.restraint import (
    FREE,
    FIXED,
    PINNED,
    ROLLER_X,
    ROLLER_Y,
    ROLLER_Z,
    Restraint,
)


if TYPE_CHECKING:
    pass


class NodeDialog(QDialog):
    """
    Dialog for creating or editing a node.

    Provides:
    - X, Y, Z coordinate inputs
    - Restraint configuration (presets + custom)
    """

    def __init__(
        self,
        parent=None,
        node: Node | None = None,
        title: str = "Node Properties",
    ) -> None:
        """
        Initialize the node dialog.

        Args:
            parent: Parent widget
            node: Existing node to edit (None for new node)
            title: Dialog title
        """
        super().__init__(parent)

        self._node = node
        self._is_new = node is None

        self.setWindowTitle(title)
        self.setMinimumWidth(350)

        self._setup_ui()

        if node is not None:
            self._load_node(node)

    def _setup_ui(self) -> None:
        """Create the dialog UI."""
        layout = QVBoxLayout(self)

        # Coordinates group
        coords_group = QGroupBox("Coordinates")
        coords_layout = QFormLayout(coords_group)

        self._x_spin = QDoubleSpinBox()
        self._x_spin.setRange(-1e9, 1e9)
        self._x_spin.setDecimals(6)
        self._x_spin.setSuffix(" m")
        coords_layout.addRow("X:", self._x_spin)

        self._y_spin = QDoubleSpinBox()
        self._y_spin.setRange(-1e9, 1e9)
        self._y_spin.setDecimals(6)
        self._y_spin.setSuffix(" m")
        coords_layout.addRow("Y:", self._y_spin)

        self._z_spin = QDoubleSpinBox()
        self._z_spin.setRange(-1e9, 1e9)
        self._z_spin.setDecimals(6)
        self._z_spin.setSuffix(" m")
        coords_layout.addRow("Z:", self._z_spin)

        layout.addWidget(coords_group)

        # Restraint group
        restraint_group = QGroupBox("Restraint (Boundary Conditions)")
        restraint_layout = QVBoxLayout(restraint_group)

        # Preset selector
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        self._preset_combo = QComboBox()
        self._preset_combo.addItem("Free", FREE)
        self._preset_combo.addItem("Fixed", FIXED)
        self._preset_combo.addItem("Pinned", PINNED)
        self._preset_combo.addItem("Roller X", ROLLER_X)
        self._preset_combo.addItem("Roller Y", ROLLER_Y)
        self._preset_combo.addItem("Roller Z", ROLLER_Z)
        self._preset_combo.addItem("Custom", None)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self._preset_combo)
        preset_layout.addStretch()
        restraint_layout.addLayout(preset_layout)

        # Individual DOF checkboxes
        dof_layout = QHBoxLayout()

        # Translations
        trans_layout = QVBoxLayout()
        trans_layout.addWidget(QLabel("Translations:"))
        self._ux_check = QCheckBox("Ux")
        self._ux_check.stateChanged.connect(self._on_dof_changed)
        trans_layout.addWidget(self._ux_check)
        self._uy_check = QCheckBox("Uy")
        self._uy_check.stateChanged.connect(self._on_dof_changed)
        trans_layout.addWidget(self._uy_check)
        self._uz_check = QCheckBox("Uz")
        self._uz_check.stateChanged.connect(self._on_dof_changed)
        trans_layout.addWidget(self._uz_check)
        dof_layout.addLayout(trans_layout)

        # Rotations
        rot_layout = QVBoxLayout()
        rot_layout.addWidget(QLabel("Rotations:"))
        self._rx_check = QCheckBox("Rx")
        self._rx_check.stateChanged.connect(self._on_dof_changed)
        rot_layout.addWidget(self._rx_check)
        self._ry_check = QCheckBox("Ry")
        self._ry_check.stateChanged.connect(self._on_dof_changed)
        rot_layout.addWidget(self._ry_check)
        self._rz_check = QCheckBox("Rz")
        self._rz_check.stateChanged.connect(self._on_dof_changed)
        rot_layout.addWidget(self._rz_check)
        dof_layout.addLayout(rot_layout)

        dof_layout.addStretch()
        restraint_layout.addLayout(dof_layout)

        layout.addWidget(restraint_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_node(self, node: Node) -> None:
        """Load node data into the dialog."""
        self._x_spin.setValue(node.x)
        self._y_spin.setValue(node.y)
        self._z_spin.setValue(node.z)

        self._set_restraint(node.restraint)

    def _set_restraint(self, restraint: Restraint) -> None:
        """Set restraint checkboxes."""
        # Block signals to prevent triggering _on_dof_changed
        self._ux_check.blockSignals(True)
        self._uy_check.blockSignals(True)
        self._uz_check.blockSignals(True)
        self._rx_check.blockSignals(True)
        self._ry_check.blockSignals(True)
        self._rz_check.blockSignals(True)

        self._ux_check.setChecked(restraint.ux)
        self._uy_check.setChecked(restraint.uy)
        self._uz_check.setChecked(restraint.uz)
        self._rx_check.setChecked(restraint.rx)
        self._ry_check.setChecked(restraint.ry)
        self._rz_check.setChecked(restraint.rz)

        # Unblock signals
        self._ux_check.blockSignals(False)
        self._uy_check.blockSignals(False)
        self._uz_check.blockSignals(False)
        self._rx_check.blockSignals(False)
        self._ry_check.blockSignals(False)
        self._rz_check.blockSignals(False)

        # Update preset combo to match
        self._update_preset_combo(restraint)

    def _update_preset_combo(self, restraint: Restraint) -> None:
        """Update preset combo to match current restraint."""
        self._preset_combo.blockSignals(True)

        presets = [FREE, FIXED, PINNED, ROLLER_X, ROLLER_Y, ROLLER_Z]
        for i, preset in enumerate(presets):
            if restraint == preset:
                self._preset_combo.setCurrentIndex(i)
                self._preset_combo.blockSignals(False)
                return

        # Custom
        self._preset_combo.setCurrentIndex(6)
        self._preset_combo.blockSignals(False)

    def _on_preset_changed(self, index: int) -> None:
        """Handle preset selection."""
        preset = self._preset_combo.currentData()
        if preset is not None:
            self._set_restraint(preset)

    def _on_dof_changed(self) -> None:
        """Handle DOF checkbox change."""
        restraint = self._get_restraint()
        self._update_preset_combo(restraint)

    def _get_restraint(self) -> Restraint:
        """Get restraint from checkboxes."""
        return Restraint(
            ux=self._ux_check.isChecked(),
            uy=self._uy_check.isChecked(),
            uz=self._uz_check.isChecked(),
            rx=self._rx_check.isChecked(),
            ry=self._ry_check.isChecked(),
            rz=self._rz_check.isChecked(),
        )

    def get_coordinates(self) -> tuple[float, float, float]:
        """Get the entered coordinates."""
        return (
            self._x_spin.value(),
            self._y_spin.value(),
            self._z_spin.value(),
        )

    def get_restraint(self) -> Restraint:
        """Get the configured restraint."""
        return self._get_restraint()

    def get_node_data(self) -> dict:
        """Get all node data as a dictionary."""
        x, y, z = self.get_coordinates()
        return {
            "x": x,
            "y": y,
            "z": z,
            "restraint": self.get_restraint(),
        }

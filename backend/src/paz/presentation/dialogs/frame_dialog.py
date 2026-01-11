"""
Frame editing dialog for PAZ structural analysis software.

Provides UI for creating and editing frame elements.
"""

from __future__ import annotations

import math
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
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from paz.domain.model.frame import Frame, FrameReleases
from paz.infrastructure.repositories.materials_repository import MaterialsRepository
from paz.infrastructure.repositories.sections_repository import SectionsRepository
from paz.presentation.dialogs.material_dialog import MaterialDialog
from paz.presentation.dialogs.section_dialog import SectionDialog


if TYPE_CHECKING:
    pass


class FrameDialog(QDialog):
    """
    Dialog for creating or editing a frame element.

    Provides:
    - Material selection
    - Section selection
    - Rotation angle
    - End releases configuration
    - Label
    """

    def __init__(
        self,
        parent=None,
        frame: Frame | None = None,
        materials_repo: MaterialsRepository | None = None,
        sections_repo: SectionsRepository | None = None,
        title: str = "Frame Properties",
    ) -> None:
        """
        Initialize the frame dialog.

        Args:
            parent: Parent widget
            frame: Existing frame to edit (None for new frame)
            materials_repo: Materials repository
            sections_repo: Sections repository
            title: Dialog title
        """
        super().__init__(parent)

        self._frame = frame
        self._is_new = frame is None
        self._materials_repo = materials_repo or MaterialsRepository()
        self._sections_repo = sections_repo or SectionsRepository()

        # Current selections
        self._material_name = frame.material_name if frame else "A36"
        self._section_name = frame.section_name if frame else "W14X22"

        self.setWindowTitle(title)
        self.setMinimumWidth(400)

        self._setup_ui()

        if frame is not None:
            self._load_frame(frame)

    def _setup_ui(self) -> None:
        """Create the dialog UI."""
        layout = QVBoxLayout(self)

        # Properties group
        props_group = QGroupBox("Properties")
        props_layout = QFormLayout(props_group)

        # Material selector
        material_layout = QHBoxLayout()
        self._material_label = QLabel(self._material_name)
        self._material_label.setMinimumWidth(150)
        material_layout.addWidget(self._material_label)
        self._material_btn = QPushButton("Select...")
        self._material_btn.clicked.connect(self._on_select_material)
        material_layout.addWidget(self._material_btn)
        material_layout.addStretch()
        props_layout.addRow("Material:", material_layout)

        # Section selector
        section_layout = QHBoxLayout()
        self._section_label = QLabel(self._section_name)
        self._section_label.setMinimumWidth(150)
        section_layout.addWidget(self._section_label)
        self._section_btn = QPushButton("Select...")
        self._section_btn.clicked.connect(self._on_select_section)
        section_layout.addWidget(self._section_btn)
        section_layout.addStretch()
        props_layout.addRow("Section:", section_layout)

        # Rotation
        self._rotation_spin = QDoubleSpinBox()
        self._rotation_spin.setRange(-180, 180)
        self._rotation_spin.setDecimals(2)
        self._rotation_spin.setSuffix(" deg")
        props_layout.addRow("Rotation:", self._rotation_spin)

        # Label
        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("Optional label...")
        props_layout.addRow("Label:", self._label_edit)

        layout.addWidget(props_group)

        # Releases group
        releases_group = QGroupBox("End Releases")
        releases_layout = QVBoxLayout(releases_group)

        # Preset selector
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        self._releases_combo = QComboBox()
        self._releases_combo.addItem("Fixed-Fixed", "fixed_fixed")
        self._releases_combo.addItem("Pinned-Pinned", "pinned_pinned")
        self._releases_combo.addItem("Fixed-Pinned", "fixed_pinned")
        self._releases_combo.addItem("Pinned-Fixed", "pinned_fixed")
        self._releases_combo.addItem("Custom", "custom")
        self._releases_combo.currentIndexChanged.connect(self._on_releases_preset_changed)
        preset_layout.addWidget(self._releases_combo)
        preset_layout.addStretch()
        releases_layout.addLayout(preset_layout)

        # Custom releases (initially hidden)
        self._custom_releases_widget = QGroupBox("Custom Releases")
        custom_layout = QHBoxLayout(self._custom_releases_widget)

        # End i
        end_i_layout = QVBoxLayout()
        end_i_layout.addWidget(QLabel("End i:"))
        self._m2_i_check = QCheckBox("M2 (moment)")
        end_i_layout.addWidget(self._m2_i_check)
        self._m3_i_check = QCheckBox("M3 (moment)")
        end_i_layout.addWidget(self._m3_i_check)
        self._t_i_check = QCheckBox("T (torsion)")
        end_i_layout.addWidget(self._t_i_check)
        custom_layout.addLayout(end_i_layout)

        # End j
        end_j_layout = QVBoxLayout()
        end_j_layout.addWidget(QLabel("End j:"))
        self._m2_j_check = QCheckBox("M2 (moment)")
        end_j_layout.addWidget(self._m2_j_check)
        self._m3_j_check = QCheckBox("M3 (moment)")
        end_j_layout.addWidget(self._m3_j_check)
        self._t_j_check = QCheckBox("T (torsion)")
        end_j_layout.addWidget(self._t_j_check)
        custom_layout.addLayout(end_j_layout)

        custom_layout.addStretch()
        releases_layout.addWidget(self._custom_releases_widget)
        self._custom_releases_widget.setVisible(False)

        layout.addWidget(releases_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_frame(self, frame: Frame) -> None:
        """Load frame data into the dialog."""
        self._material_name = frame.material_name
        self._material_label.setText(frame.material_name)

        self._section_name = frame.section_name
        self._section_label.setText(frame.section_name)

        # Convert radians to degrees
        self._rotation_spin.setValue(math.degrees(frame.rotation))

        self._label_edit.setText(frame.label)

        self._set_releases(frame.releases)

    def _set_releases(self, releases: FrameReleases) -> None:
        """Set releases checkboxes."""
        self._m2_i_check.setChecked(releases.M2_i)
        self._m3_i_check.setChecked(releases.M3_i)
        self._t_i_check.setChecked(releases.T_i)
        self._m2_j_check.setChecked(releases.M2_j)
        self._m3_j_check.setChecked(releases.M3_j)
        self._t_j_check.setChecked(releases.T_j)

        # Update preset combo
        if releases.is_fully_fixed():
            self._releases_combo.setCurrentIndex(0)  # Fixed-Fixed
        elif releases == FrameReleases.pinned_pinned():
            self._releases_combo.setCurrentIndex(1)
        elif releases == FrameReleases.fixed_pinned():
            self._releases_combo.setCurrentIndex(2)
        elif releases == FrameReleases.pinned_fixed():
            self._releases_combo.setCurrentIndex(3)
        else:
            self._releases_combo.setCurrentIndex(4)  # Custom
            self._custom_releases_widget.setVisible(True)

    def _on_releases_preset_changed(self, index: int) -> None:
        """Handle releases preset change."""
        preset = self._releases_combo.currentData()

        if preset == "custom":
            self._custom_releases_widget.setVisible(True)
        else:
            self._custom_releases_widget.setVisible(False)

            if preset == "fixed_fixed":
                releases = FrameReleases.fixed_fixed()
            elif preset == "pinned_pinned":
                releases = FrameReleases.pinned_pinned()
            elif preset == "fixed_pinned":
                releases = FrameReleases.fixed_pinned()
            elif preset == "pinned_fixed":
                releases = FrameReleases.pinned_fixed()
            else:
                releases = FrameReleases()

            self._set_releases(releases)

    def _on_select_material(self) -> None:
        """Open material selection dialog."""
        dialog = MaterialDialog(
            self,
            repository=self._materials_repo,
            current_material=self._material_name,
        )

        if dialog.exec() == MaterialDialog.DialogCode.Accepted:
            name = dialog.get_selected_material_name()
            if name:
                self._material_name = name
                self._material_label.setText(name)

    def _on_select_section(self) -> None:
        """Open section selection dialog."""
        dialog = SectionDialog(
            self,
            repository=self._sections_repo,
            current_section=self._section_name,
        )

        if dialog.exec() == SectionDialog.DialogCode.Accepted:
            name = dialog.get_selected_section_name()
            if name:
                self._section_name = name
                self._section_label.setText(name)

    def get_material_name(self) -> str:
        """Get selected material name."""
        return self._material_name

    def get_section_name(self) -> str:
        """Get selected section name."""
        return self._section_name

    def get_rotation(self) -> float:
        """Get rotation in radians."""
        return math.radians(self._rotation_spin.value())

    def get_label(self) -> str:
        """Get label text."""
        return self._label_edit.text()

    def get_releases(self) -> FrameReleases:
        """Get configured releases."""
        preset = self._releases_combo.currentData()

        if preset == "fixed_fixed":
            return FrameReleases.fixed_fixed()
        elif preset == "pinned_pinned":
            return FrameReleases.pinned_pinned()
        elif preset == "fixed_pinned":
            return FrameReleases.fixed_pinned()
        elif preset == "pinned_fixed":
            return FrameReleases.pinned_fixed()
        else:
            # Custom
            return FrameReleases(
                M2_i=self._m2_i_check.isChecked(),
                M3_i=self._m3_i_check.isChecked(),
                T_i=self._t_i_check.isChecked(),
                M2_j=self._m2_j_check.isChecked(),
                M3_j=self._m3_j_check.isChecked(),
                T_j=self._t_j_check.isChecked(),
            )

    def get_frame_data(self) -> dict:
        """Get all frame data as a dictionary."""
        return {
            "material_name": self.get_material_name(),
            "section_name": self.get_section_name(),
            "rotation": self.get_rotation(),
            "label": self.get_label(),
            "releases": self.get_releases(),
        }

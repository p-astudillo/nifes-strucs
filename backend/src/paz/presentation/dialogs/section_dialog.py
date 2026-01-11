"""
Section selection dialog for PAZ structural analysis software.

Provides UI for browsing, searching, and selecting structural sections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from paz.domain.sections.section import Section, SectionShape
from paz.infrastructure.repositories.sections_repository import SectionsRepository


if TYPE_CHECKING:
    pass


class SectionDialog(QDialog):
    """
    Dialog for selecting a section from the library.

    Provides:
    - Filter by section shape (W, HSS, L, C, etc.)
    - Search by designation
    - View section properties
    - Select and confirm section
    """

    section_selected = Signal(str)  # Emits section name

    def __init__(
        self,
        parent=None,
        repository: SectionsRepository | None = None,
        current_section: str | None = None,
    ) -> None:
        """
        Initialize the section dialog.

        Args:
            parent: Parent widget
            repository: Sections repository (creates new if None)
            current_section: Currently selected section name
        """
        super().__init__(parent)

        self._repository = repository or SectionsRepository()
        self._current_section = current_section
        self._selected_section: Section | None = None

        self.setWindowTitle("Select Section")
        self.setMinimumSize(600, 500)

        self._setup_ui()
        self._load_sections()

        # Select current section if provided
        if current_section:
            self._select_section_by_name(current_section)

    def _setup_ui(self) -> None:
        """Create the dialog UI."""
        layout = QVBoxLayout(self)

        # Filter row
        filter_layout = QHBoxLayout()

        # Shape filter
        filter_layout.addWidget(QLabel("Shape:"))
        self._shape_combo = QComboBox()
        self._shape_combo.addItem("All Shapes", None)
        for shape in SectionShape:
            if shape != SectionShape.CUSTOM:
                self._shape_combo.addItem(shape.value, shape)
        self._shape_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self._shape_combo)

        filter_layout.addSpacing(20)

        # Search
        filter_layout.addWidget(QLabel("Search:"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search by designation (e.g., W14X30)...")
        self._search_edit.textChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self._search_edit)

        layout.addLayout(filter_layout)

        # Main content: list + properties
        content_layout = QHBoxLayout()

        # Section list
        self._section_list = QListWidget()
        self._section_list.currentItemChanged.connect(self._on_selection_changed)
        self._section_list.itemDoubleClicked.connect(self._on_double_click)
        content_layout.addWidget(self._section_list, stretch=1)

        # Properties panel
        props_widget = QVBoxLayout()

        # Geometric properties
        geom_group = QGroupBox("Geometric Properties")
        geom_layout = QFormLayout(geom_group)

        self._name_label = QLabel("-")
        geom_layout.addRow("Designation:", self._name_label)

        self._shape_label = QLabel("-")
        geom_layout.addRow("Shape:", self._shape_label)

        self._a_label = QLabel("-")
        geom_layout.addRow("A (cm2):", self._a_label)

        self._d_label = QLabel("-")
        geom_layout.addRow("d (mm):", self._d_label)

        self._bf_label = QLabel("-")
        geom_layout.addRow("bf (mm):", self._bf_label)

        self._tw_label = QLabel("-")
        geom_layout.addRow("tw (mm):", self._tw_label)

        self._tf_label = QLabel("-")
        geom_layout.addRow("tf (mm):", self._tf_label)

        self._w_label = QLabel("-")
        geom_layout.addRow("Weight (kg/m):", self._w_label)

        props_widget.addWidget(geom_group)

        # Inertia properties
        inertia_group = QGroupBox("Section Properties")
        inertia_layout = QFormLayout(inertia_group)

        self._ix_label = QLabel("-")
        inertia_layout.addRow("Ix (cm4):", self._ix_label)

        self._iy_label = QLabel("-")
        inertia_layout.addRow("Iy (cm4):", self._iy_label)

        self._sx_label = QLabel("-")
        inertia_layout.addRow("Sx (cm3):", self._sx_label)

        self._sy_label = QLabel("-")
        inertia_layout.addRow("Sy (cm3):", self._sy_label)

        self._rx_label = QLabel("-")
        inertia_layout.addRow("rx (mm):", self._rx_label)

        self._ry_label = QLabel("-")
        inertia_layout.addRow("ry (mm):", self._ry_label)

        self._zx_label = QLabel("-")
        inertia_layout.addRow("Zx (cm3):", self._zx_label)

        self._zy_label = QLabel("-")
        inertia_layout.addRow("Zy (cm3):", self._zy_label)

        self._j_label = QLabel("-")
        inertia_layout.addRow("J (cm4):", self._j_label)

        props_widget.addWidget(inertia_group)

        props_widget.addStretch()

        content_layout.addLayout(props_widget, stretch=1)

        layout.addLayout(content_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self._ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setEnabled(False)
        layout.addWidget(button_box)

    def _load_sections(self) -> None:
        """Load sections into the list."""
        self._section_list.clear()

        # Get filter values
        shape_filter = self._shape_combo.currentData()
        search_text = self._search_edit.text().upper()

        # Get sections
        if shape_filter is not None:
            sections = self._repository.filter_by_shape(shape_filter)
        else:
            sections = self._repository.all()

        # Apply search filter
        if search_text:
            sections = [
                s for s in sections
                if search_text in s.name.upper()
            ]

        # Sort by name
        sections.sort(key=lambda s: s.name)

        # Add to list
        for section in sections:
            item = QListWidgetItem(section.name)
            item.setData(Qt.ItemDataRole.UserRole, section)
            self._section_list.addItem(item)

    def _on_filter_changed(self) -> None:
        """Handle filter change."""
        self._load_sections()

    def _on_selection_changed(self, current: QListWidgetItem | None, _previous) -> None:
        """Handle selection change in the list."""
        if current is None:
            self._clear_properties()
            self._ok_button.setEnabled(False)
            return

        section: Section = current.data(Qt.ItemDataRole.UserRole)
        self._selected_section = section
        self._show_properties(section)
        self._ok_button.setEnabled(True)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        """Handle double click on section."""
        self.accept()

    def _show_properties(self, section: Section) -> None:
        """Display section properties."""
        self._name_label.setText(section.name)
        self._shape_label.setText(section.shape.value)

        # Convert from m2 to cm2 (multiply by 1e4)
        self._a_label.setText(f"{section.A * 1e4:.2f}")

        # Convert from m to mm (multiply by 1000)
        if section.d is not None:
            self._d_label.setText(f"{section.d * 1000:.1f}")
        else:
            self._d_label.setText("-")

        if section.bf is not None:
            self._bf_label.setText(f"{section.bf * 1000:.1f}")
        else:
            self._bf_label.setText("-")

        if section.tw is not None:
            self._tw_label.setText(f"{section.tw * 1000:.2f}")
        else:
            self._tw_label.setText("-")

        if section.tf is not None:
            self._tf_label.setText(f"{section.tf * 1000:.2f}")
        else:
            self._tf_label.setText("-")

        if section.W is not None:
            self._w_label.setText(f"{section.W:.1f}")
        else:
            self._w_label.setText("-")

        # Convert from m4 to cm4 (multiply by 1e8)
        self._ix_label.setText(f"{section.Ix * 1e8:.0f}")
        self._iy_label.setText(f"{section.Iy * 1e8:.0f}")

        # Convert from m3 to cm3 (multiply by 1e6)
        if section.Sx is not None:
            self._sx_label.setText(f"{section.Sx * 1e6:.0f}")
        else:
            self._sx_label.setText("-")

        if section.Sy is not None:
            self._sy_label.setText(f"{section.Sy * 1e6:.0f}")
        else:
            self._sy_label.setText("-")

        # Convert from m to mm
        self._rx_label.setText(f"{section.rx_calculated * 1000:.1f}")
        self._ry_label.setText(f"{section.ry_calculated * 1000:.1f}")

        if section.Zx is not None:
            self._zx_label.setText(f"{section.Zx * 1e6:.0f}")
        else:
            self._zx_label.setText("-")

        if section.Zy is not None:
            self._zy_label.setText(f"{section.Zy * 1e6:.0f}")
        else:
            self._zy_label.setText("-")

        if section.J is not None:
            self._j_label.setText(f"{section.J * 1e8:.1f}")
        else:
            self._j_label.setText("-")

    def _clear_properties(self) -> None:
        """Clear the properties display."""
        self._name_label.setText("-")
        self._shape_label.setText("-")
        self._a_label.setText("-")
        self._d_label.setText("-")
        self._bf_label.setText("-")
        self._tw_label.setText("-")
        self._tf_label.setText("-")
        self._w_label.setText("-")
        self._ix_label.setText("-")
        self._iy_label.setText("-")
        self._sx_label.setText("-")
        self._sy_label.setText("-")
        self._rx_label.setText("-")
        self._ry_label.setText("-")
        self._zx_label.setText("-")
        self._zy_label.setText("-")
        self._j_label.setText("-")
        self._selected_section = None

    def _select_section_by_name(self, name: str) -> None:
        """Select a section by name in the list."""
        for i in range(self._section_list.count()):
            item = self._section_list.item(i)
            if item and item.text() == name:
                self._section_list.setCurrentItem(item)
                break

    def get_selected_section(self) -> Section | None:
        """Get the selected section."""
        return self._selected_section

    def get_selected_section_name(self) -> str | None:
        """Get the selected section name."""
        if self._selected_section:
            return self._selected_section.name
        return None

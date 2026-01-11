"""
Material selection dialog for PAZ structural analysis software.

Provides UI for browsing, searching, and selecting materials.
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

from paz.domain.materials.material import Material, MaterialType
from paz.infrastructure.repositories.materials_repository import MaterialsRepository


if TYPE_CHECKING:
    pass


class MaterialDialog(QDialog):
    """
    Dialog for selecting a material from the library.

    Provides:
    - Filter by material type (Steel, Concrete, etc.)
    - Search by name
    - View material properties
    - Select and confirm material
    """

    material_selected = Signal(str)  # Emits material name

    def __init__(
        self,
        parent=None,
        repository: MaterialsRepository | None = None,
        current_material: str | None = None,
    ) -> None:
        """
        Initialize the material dialog.

        Args:
            parent: Parent widget
            repository: Materials repository (creates new if None)
            current_material: Currently selected material name
        """
        super().__init__(parent)

        self._repository = repository or MaterialsRepository()
        self._current_material = current_material
        self._selected_material: Material | None = None

        self.setWindowTitle("Select Material")
        self.setMinimumSize(500, 400)

        self._setup_ui()
        self._load_materials()

        # Select current material if provided
        if current_material:
            self._select_material_by_name(current_material)

    def _setup_ui(self) -> None:
        """Create the dialog UI."""
        layout = QVBoxLayout(self)

        # Filter row
        filter_layout = QHBoxLayout()

        # Type filter
        filter_layout.addWidget(QLabel("Type:"))
        self._type_combo = QComboBox()
        self._type_combo.addItem("All Types", None)
        for mat_type in MaterialType:
            self._type_combo.addItem(mat_type.value.title(), mat_type)
        self._type_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self._type_combo)

        filter_layout.addSpacing(20)

        # Search
        filter_layout.addWidget(QLabel("Search:"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search by name...")
        self._search_edit.textChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self._search_edit)

        layout.addLayout(filter_layout)

        # Main content: list + properties
        content_layout = QHBoxLayout()

        # Material list
        self._material_list = QListWidget()
        self._material_list.currentItemChanged.connect(self._on_selection_changed)
        self._material_list.itemDoubleClicked.connect(self._on_double_click)
        content_layout.addWidget(self._material_list, stretch=1)

        # Properties panel
        props_group = QGroupBox("Properties")
        props_layout = QFormLayout(props_group)

        self._name_label = QLabel("-")
        props_layout.addRow("Name:", self._name_label)

        self._type_label = QLabel("-")
        props_layout.addRow("Type:", self._type_label)

        self._standard_label = QLabel("-")
        props_layout.addRow("Standard:", self._standard_label)

        self._e_label = QLabel("-")
        props_layout.addRow("E (GPa):", self._e_label)

        self._g_label = QLabel("-")
        props_layout.addRow("G (GPa):", self._g_label)

        self._nu_label = QLabel("-")
        props_layout.addRow("Poisson (nu):", self._nu_label)

        self._rho_label = QLabel("-")
        props_layout.addRow("Density (kg/m3):", self._rho_label)

        self._fy_label = QLabel("-")
        props_layout.addRow("fy (MPa):", self._fy_label)

        self._fu_label = QLabel("-")
        props_layout.addRow("fu (MPa):", self._fu_label)

        self._fc_label = QLabel("-")
        props_layout.addRow("f'c (MPa):", self._fc_label)

        self._desc_label = QLabel("-")
        self._desc_label.setWordWrap(True)
        props_layout.addRow("Description:", self._desc_label)

        content_layout.addWidget(props_group, stretch=1)

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

    def _load_materials(self) -> None:
        """Load materials into the list."""
        self._material_list.clear()

        # Get filter values
        type_filter = self._type_combo.currentData()
        search_text = self._search_edit.text().lower()

        # Get materials
        if type_filter is not None:
            materials = self._repository.filter_by_type(type_filter)
        else:
            materials = self._repository.all()

        # Apply search filter
        if search_text:
            materials = [
                m for m in materials
                if search_text in m.name.lower() or search_text in m.description.lower()
            ]

        # Sort by name
        materials.sort(key=lambda m: m.name)

        # Add to list
        for material in materials:
            item = QListWidgetItem(material.name)
            item.setData(Qt.ItemDataRole.UserRole, material)
            self._material_list.addItem(item)

    def _on_filter_changed(self) -> None:
        """Handle filter change."""
        self._load_materials()

    def _on_selection_changed(self, current: QListWidgetItem | None, _previous) -> None:
        """Handle selection change in the list."""
        if current is None:
            self._clear_properties()
            self._ok_button.setEnabled(False)
            return

        material: Material = current.data(Qt.ItemDataRole.UserRole)
        self._selected_material = material
        self._show_properties(material)
        self._ok_button.setEnabled(True)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        """Handle double click on material."""
        self.accept()

    def _show_properties(self, material: Material) -> None:
        """Display material properties."""
        self._name_label.setText(material.name)
        self._type_label.setText(material.material_type.value.title())
        self._standard_label.setText(material.standard.value)

        # Convert from kPa to GPa (divide by 1e6)
        self._e_label.setText(f"{material.E / 1e6:.1f}")
        self._g_label.setText(f"{material.G / 1e6:.1f}")
        self._nu_label.setText(f"{material.nu:.3f}")
        self._rho_label.setText(f"{material.rho:.0f}")

        # Convert from kPa to MPa (divide by 1e3)
        if material.fy is not None:
            self._fy_label.setText(f"{material.fy / 1e3:.0f}")
        else:
            self._fy_label.setText("-")

        if material.fu is not None:
            self._fu_label.setText(f"{material.fu / 1e3:.0f}")
        else:
            self._fu_label.setText("-")

        if material.fc is not None:
            self._fc_label.setText(f"{material.fc / 1e3:.0f}")
        else:
            self._fc_label.setText("-")

        self._desc_label.setText(material.description or "-")

    def _clear_properties(self) -> None:
        """Clear the properties display."""
        self._name_label.setText("-")
        self._type_label.setText("-")
        self._standard_label.setText("-")
        self._e_label.setText("-")
        self._g_label.setText("-")
        self._nu_label.setText("-")
        self._rho_label.setText("-")
        self._fy_label.setText("-")
        self._fu_label.setText("-")
        self._fc_label.setText("-")
        self._desc_label.setText("-")
        self._selected_material = None

    def _select_material_by_name(self, name: str) -> None:
        """Select a material by name in the list."""
        for i in range(self._material_list.count()):
            item = self._material_list.item(i)
            if item and item.text() == name:
                self._material_list.setCurrentItem(item)
                break

    def get_selected_material(self) -> Material | None:
        """Get the selected material."""
        return self._selected_material

    def get_selected_material_name(self) -> str | None:
        """Get the selected material name."""
        if self._selected_material:
            return self._selected_material.name
        return None

"""
Results panel showing analysis result summaries and controls.

Displays tables of maximum forces and provides interaction
for highlighting specific elements.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from paz.presentation.viewport.force_diagrams import ForceType


if TYPE_CHECKING:
    from paz.domain.results import AnalysisResults


class ResultsPanel(QWidget):
    """
    Panel displaying analysis results summary.

    Shows:
    - Force type selector
    - Table of global maximum values
    - Per-frame maximum values
    - Buttons to highlight max elements

    Signals:
        force_type_changed(ForceType): Emitted when force type selection changes
        highlight_frame(int): Emitted to highlight a specific frame
        clear_highlight(): Emitted to clear frame highlighting
        filter_changed(float, float): Emitted when filter range changes (min, max)
                                      Use None values to clear filter
    """

    force_type_changed = Signal(object)  # ForceType enum
    highlight_frame = Signal(int)
    clear_highlight = Signal()
    filter_changed = Signal(object, object)  # (min, max) - use object for None support

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the results panel."""
        super().__init__(parent)

        self._results: AnalysisResults | None = None
        self._current_force_type = ForceType.M3

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Force type selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Force Type:"))

        self._force_type_combo = QComboBox()
        self._force_type_combo.addItems(["M3", "V2", "P", "M2", "V3", "T"])
        self._force_type_combo.currentTextChanged.connect(self._on_force_type_changed)
        selector_layout.addWidget(self._force_type_combo)
        selector_layout.addStretch()

        layout.addLayout(selector_layout)

        # Global extremes group
        extremes_group = QGroupBox("Global Extremes")
        extremes_layout = QVBoxLayout(extremes_group)

        self._extremes_table = QTableWidget(3, 2)
        self._extremes_table.setHorizontalHeaderLabels(["Property", "Value"])
        self._extremes_table.verticalHeader().setVisible(False)
        self._extremes_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._extremes_table.setMaximumHeight(120)

        # Set row labels
        self._extremes_table.setItem(0, 0, QTableWidgetItem("Maximum"))
        self._extremes_table.setItem(1, 0, QTableWidgetItem("Minimum"))
        self._extremes_table.setItem(2, 0, QTableWidgetItem("Abs. Max"))
        self._extremes_table.setItem(0, 1, QTableWidgetItem("-"))
        self._extremes_table.setItem(1, 1, QTableWidgetItem("-"))
        self._extremes_table.setItem(2, 1, QTableWidgetItem("-"))

        extremes_layout.addWidget(self._extremes_table)
        layout.addWidget(extremes_group)

        # Frame results group
        frame_group = QGroupBox("Frame Results (Top 10)")
        frame_layout = QVBoxLayout(frame_group)

        self._frame_table = QTableWidget(0, 4)
        self._frame_table.setHorizontalHeaderLabels(
            ["Frame", "Max", "Min", "Abs Max"]
        )
        self._frame_table.verticalHeader().setVisible(False)
        self._frame_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._frame_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._frame_table.itemSelectionChanged.connect(self._on_frame_selected)

        frame_layout.addWidget(self._frame_table)

        # Buttons
        btn_layout = QHBoxLayout()
        self._highlight_max_btn = QPushButton("Highlight Max Frame")
        self._highlight_max_btn.clicked.connect(self._on_highlight_max)
        btn_layout.addWidget(self._highlight_max_btn)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self._on_clear_highlight)
        btn_layout.addWidget(self._clear_btn)

        frame_layout.addLayout(btn_layout)
        layout.addWidget(frame_group)

        # Filter group
        filter_group = QGroupBox("Filter by Range")
        filter_layout = QVBoxLayout(filter_group)

        # Enable filter checkbox
        self._filter_enabled = QCheckBox("Enable filter")
        self._filter_enabled.stateChanged.connect(self._on_filter_toggled)
        filter_layout.addWidget(self._filter_enabled)

        # Min value
        min_layout = QHBoxLayout()
        min_layout.addWidget(QLabel("Min:"))
        self._min_spin = QDoubleSpinBox()
        self._min_spin.setRange(0.0, 1e9)
        self._min_spin.setDecimals(2)
        self._min_spin.setValue(0.0)
        self._min_spin.setEnabled(False)
        self._min_spin.valueChanged.connect(self._on_filter_value_changed)
        min_layout.addWidget(self._min_spin)
        filter_layout.addLayout(min_layout)

        # Max value
        max_layout = QHBoxLayout()
        max_layout.addWidget(QLabel("Max:"))
        self._max_spin = QDoubleSpinBox()
        self._max_spin.setRange(0.0, 1e9)
        self._max_spin.setDecimals(2)
        self._max_spin.setValue(1000.0)
        self._max_spin.setEnabled(False)
        self._max_spin.valueChanged.connect(self._on_filter_value_changed)
        max_layout.addWidget(self._max_spin)
        filter_layout.addLayout(max_layout)

        layout.addWidget(filter_group)

        layout.addStretch()

    def set_results(self, results: AnalysisResults | None) -> None:
        """
        Set analysis results to display.

        Args:
            results: Analysis results or None to clear
        """
        self._results = results
        self._update_display()

    def get_force_type(self) -> ForceType:
        """Get currently selected force type."""
        return self._current_force_type

    def _on_force_type_changed(self, text: str) -> None:
        """Handle force type selection change."""
        force_map = {
            "M3": ForceType.M3,
            "V2": ForceType.V2,
            "P": ForceType.P,
            "M2": ForceType.M2,
            "V3": ForceType.V3,
            "T": ForceType.T,
        }
        self._current_force_type = force_map.get(text, ForceType.M3)
        self.force_type_changed.emit(self._current_force_type)
        self._update_display()

    def _on_frame_selected(self) -> None:
        """Handle frame table selection."""
        selected = self._frame_table.selectedItems()
        if selected:
            row = selected[0].row()
            frame_item = self._frame_table.item(row, 0)
            if frame_item:
                try:
                    frame_id = int(frame_item.text())
                    self.highlight_frame.emit(frame_id)
                except ValueError:
                    pass

    def _on_highlight_max(self) -> None:
        """Highlight frame with maximum value."""
        if self._results is None:
            return

        max_frame_id, _ = self._find_max_frame()
        if max_frame_id is not None:
            self.highlight_frame.emit(max_frame_id)

    def _on_clear_highlight(self) -> None:
        """Clear frame highlighting."""
        self._frame_table.clearSelection()
        self.clear_highlight.emit()

    def _on_filter_toggled(self, state: int) -> None:
        """Handle filter checkbox toggle."""
        enabled = state != 0
        self._min_spin.setEnabled(enabled)
        self._max_spin.setEnabled(enabled)

        if enabled:
            self.filter_changed.emit(
                self._min_spin.value(),
                self._max_spin.value(),
            )
        else:
            self.filter_changed.emit(None, None)

    def _on_filter_value_changed(self) -> None:
        """Handle filter value changes."""
        if self._filter_enabled.isChecked():
            self.filter_changed.emit(
                self._min_spin.value(),
                self._max_spin.value(),
            )

    def _update_display(self) -> None:
        """Update tables with current results."""
        if self._results is None:
            self._clear_tables()
            return

        # Update global extremes
        extremes = self._calculate_global_extremes()
        self._extremes_table.item(0, 1).setText(f"{extremes['max']:.2f}")
        self._extremes_table.item(1, 1).setText(f"{extremes['min']:.2f}")
        self._extremes_table.item(2, 1).setText(f"{extremes['abs_max']:.2f}")

        # Update frame table (top 10 by absolute max)
        frame_data = self._get_frame_summary()
        self._update_frame_table(frame_data)

    def _clear_tables(self) -> None:
        """Clear all table data."""
        self._extremes_table.item(0, 1).setText("-")
        self._extremes_table.item(1, 1).setText("-")
        self._extremes_table.item(2, 1).setText("-")
        self._frame_table.setRowCount(0)

    def _calculate_global_extremes(self) -> dict[str, float]:
        """Calculate global extreme values for current force type."""
        if self._results is None:
            return {"max": 0.0, "min": 0.0, "abs_max": 0.0}

        max_val = float("-inf")
        min_val = float("inf")

        for frame_result in self._results.frame_results.values():
            for forces in frame_result.forces:
                val = self._get_force_value(forces)
                max_val = max(max_val, val)
                min_val = min(min_val, val)

        if max_val == float("-inf"):
            max_val = 0.0
        if min_val == float("inf"):
            min_val = 0.0

        return {
            "max": max_val,
            "min": min_val,
            "abs_max": max(abs(max_val), abs(min_val)),
        }

    def _get_frame_summary(self) -> list[dict]:
        """Get summary data for each frame, sorted by absolute max."""
        if self._results is None:
            return []

        summaries = []
        for frame_id, frame_result in self._results.frame_results.items():
            max_val = float("-inf")
            min_val = float("inf")

            for forces in frame_result.forces:
                val = self._get_force_value(forces)
                max_val = max(max_val, val)
                min_val = min(min_val, val)

            if max_val == float("-inf"):
                max_val = 0.0
            if min_val == float("inf"):
                min_val = 0.0

            summaries.append({
                "frame_id": frame_id,
                "max": max_val,
                "min": min_val,
                "abs_max": max(abs(max_val), abs(min_val)),
            })

        # Sort by absolute max, descending
        summaries.sort(key=lambda x: x["abs_max"], reverse=True)

        return summaries[:10]  # Top 10

    def _update_frame_table(self, data: list[dict]) -> None:
        """Update frame table with summary data."""
        self._frame_table.setRowCount(len(data))

        for row, item in enumerate(data):
            self._frame_table.setItem(row, 0, QTableWidgetItem(str(item["frame_id"])))
            self._frame_table.setItem(row, 1, QTableWidgetItem(f"{item['max']:.2f}"))
            self._frame_table.setItem(row, 2, QTableWidgetItem(f"{item['min']:.2f}"))
            self._frame_table.setItem(row, 3, QTableWidgetItem(f"{item['abs_max']:.2f}"))

    def _find_max_frame(self) -> tuple[int | None, float]:
        """Find frame with maximum absolute value."""
        if self._results is None:
            return None, 0.0

        max_frame_id: int | None = None
        max_abs = 0.0

        for frame_id, frame_result in self._results.frame_results.items():
            for forces in frame_result.forces:
                val = abs(self._get_force_value(forces))
                if val > max_abs:
                    max_abs = val
                    max_frame_id = frame_id

        return max_frame_id, max_abs

    def _get_force_value(self, forces: object) -> float:
        """Get force value based on current force type."""
        if self._current_force_type == ForceType.P:
            return float(getattr(forces, "P", 0.0))
        if self._current_force_type == ForceType.V2:
            return float(getattr(forces, "V2", 0.0))
        if self._current_force_type == ForceType.V3:
            return float(getattr(forces, "V3", 0.0))
        if self._current_force_type == ForceType.T:
            return float(getattr(forces, "T", 0.0))
        if self._current_force_type == ForceType.M2:
            return float(getattr(forces, "M2", 0.0))
        if self._current_force_type == ForceType.M3:
            return float(getattr(forces, "M3", 0.0))
        return 0.0

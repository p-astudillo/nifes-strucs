"""
Color scale widget for displaying displacement value mapping.

Shows a color gradient bar with min/max values and unit labels.
"""

from __future__ import annotations

from typing import ClassVar

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class ColorScaleWidget(QWidget):
    """
    Widget displaying a color scale legend with min/max values.

    Shows a horizontal gradient bar with the current colormap and
    labels showing the value range.
    """

    # Predefined colormap color stops (normalized 0-1 position, RGB values)
    COLORMAPS: ClassVar[dict[str, list[tuple[float, tuple[int, int, int]]]]] = {
        "viridis": [
            (0.0, (68, 1, 84)),
            (0.25, (59, 82, 139)),
            (0.5, (33, 145, 140)),
            (0.75, (94, 201, 98)),
            (1.0, (253, 231, 37)),
        ],
        "rainbow": [
            (0.0, (150, 0, 90)),
            (0.17, (0, 0, 200)),
            (0.33, (0, 200, 200)),
            (0.5, (0, 255, 0)),
            (0.67, (255, 255, 0)),
            (0.83, (255, 128, 0)),
            (1.0, (255, 0, 0)),
        ],
        "coolwarm": [
            (0.0, (59, 76, 192)),
            (0.5, (220, 220, 220)),
            (1.0, (180, 4, 38)),
        ],
        "jet": [
            (0.0, (0, 0, 128)),
            (0.11, (0, 0, 255)),
            (0.25, (0, 128, 255)),
            (0.38, (0, 255, 255)),
            (0.5, (128, 255, 128)),
            (0.62, (255, 255, 0)),
            (0.75, (255, 128, 0)),
            (0.88, (255, 0, 0)),
            (1.0, (128, 0, 0)),
        ],
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the color scale widget."""
        super().__init__(parent)

        self._min_val: float = 0.0
        self._max_val: float = 1.0
        self._colormap: str = "viridis"
        self._unit: str = "mm"
        self._title: str = "Displacement"

        self.setFixedHeight(50)
        self.setMinimumWidth(300)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create the widget layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(2)

        # Title row
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)

        self._title_label = QLabel(f"{self._title} ({self._unit})")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet("font-weight: bold; font-size: 10px;")
        title_layout.addWidget(self._title_label)

        layout.addLayout(title_layout)

        # Color bar will be drawn in paintEvent

        # Value labels row
        labels_layout = QHBoxLayout()
        labels_layout.setContentsMargins(0, 0, 0, 0)

        self._min_label = QLabel(self._format_value(self._min_val))
        self._min_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._min_label.setStyleSheet("font-size: 9px;")
        labels_layout.addWidget(self._min_label)

        labels_layout.addStretch()

        self._max_label = QLabel(self._format_value(self._max_val))
        self._max_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._max_label.setStyleSheet("font-size: 9px;")
        labels_layout.addWidget(self._max_label)

        layout.addLayout(labels_layout)

    def set_range(self, min_val: float, max_val: float) -> None:
        """
        Set the value range.

        Args:
            min_val: Minimum value
            max_val: Maximum value
        """
        self._min_val = min_val
        self._max_val = max_val
        self._update_labels()
        self.update()

    def set_colormap(self, colormap: str) -> None:
        """
        Set the colormap name.

        Args:
            colormap: Colormap name (viridis, rainbow, coolwarm, jet)
        """
        if colormap in self.COLORMAPS:
            self._colormap = colormap
            self.update()

    def set_unit(self, unit: str) -> None:
        """
        Set the display unit.

        Args:
            unit: Unit string (e.g., "mm", "m", "in")
        """
        self._unit = unit
        self._update_labels()

    def set_title(self, title: str) -> None:
        """
        Set the title text.

        Args:
            title: Title string (e.g., "Displacement", "Ux", "Total")
        """
        self._title = title
        self._update_labels()

    def get_color_for_value(self, value: float) -> QColor:
        """
        Get the color for a specific value.

        Args:
            value: Value within the current range

        Returns:
            QColor corresponding to the value
        """
        if self._max_val == self._min_val:
            t = 0.5
        else:
            t = (value - self._min_val) / (self._max_val - self._min_val)

        t = max(0.0, min(1.0, t))

        return self._interpolate_color(t)

    def _update_labels(self) -> None:
        """Update label text."""
        self._min_label.setText(self._format_value(self._min_val))
        self._max_label.setText(self._format_value(self._max_val))
        self._title_label.setText(f"{self._title} ({self._unit})")

    def _format_value(self, value: float) -> str:
        """
        Format a value for display.

        Converts to mm if unit is mm, otherwise shows raw value.

        Args:
            value: Value in meters

        Returns:
            Formatted string
        """
        if self._unit == "mm":
            # Convert from m to mm
            return f"{value * 1000:.4f}"
        return f"{value:.6f}"

    def _interpolate_color(self, t: float) -> QColor:
        """
        Interpolate color from colormap at position t.

        Args:
            t: Position in range [0, 1]

        Returns:
            Interpolated QColor
        """
        stops = self.COLORMAPS.get(self._colormap, self.COLORMAPS["viridis"])

        # Find surrounding stops
        lower_stop = stops[0]
        upper_stop = stops[-1]

        for i, (pos, _color) in enumerate(stops):
            if pos <= t:
                lower_stop = stops[i]
            if pos >= t:
                upper_stop = stops[i]
                break

        # Interpolate between stops
        lower_pos, lower_color = lower_stop
        upper_pos, upper_color = upper_stop

        if upper_pos == lower_pos:
            factor = 0.0
        else:
            factor = (t - lower_pos) / (upper_pos - lower_pos)

        r = int(lower_color[0] + factor * (upper_color[0] - lower_color[0]))
        g = int(lower_color[1] + factor * (upper_color[1] - lower_color[1]))
        b = int(lower_color[2] + factor * (upper_color[2] - lower_color[2]))

        return QColor(r, g, b)

    def paintEvent(self, event: QPaintEvent | None) -> None:
        """Draw the color gradient bar."""
        super().paintEvent(event)  # type: ignore[arg-type]

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate bar rectangle (between title and labels)
        margin = 10
        bar_height = 12
        bar_top = 18
        bar_rect_left = margin
        bar_rect_right = self.width() - margin
        bar_width = bar_rect_right - bar_rect_left

        # Create gradient
        gradient = QLinearGradient(bar_rect_left, 0, bar_rect_right, 0)

        stops = self.COLORMAPS.get(self._colormap, self.COLORMAPS["viridis"])
        for pos, color in stops:
            gradient.setColorAt(pos, QColor(*color))

        # Draw gradient bar
        painter.fillRect(bar_rect_left, bar_top, bar_width, bar_height, gradient)

        # Draw border
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(bar_rect_left, bar_top, bar_width, bar_height)

        painter.end()

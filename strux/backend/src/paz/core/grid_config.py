"""
Grid configuration for structural modeling.

Defines grid spacing, snapping behavior, and display settings
for the modeling viewport.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SnapMode(Enum):
    """Snapping behavior modes."""

    NONE = "none"  # No snapping
    GRID = "grid"  # Snap to grid intersections
    NODE = "node"  # Snap to existing nodes
    BOTH = "both"  # Snap to grid and nodes


@dataclass
class GridAxisConfig:
    """Configuration for a single grid axis."""

    spacing: float = 1.0  # Major grid spacing in meters
    minor_divisions: int = 4  # Number of minor divisions between major lines
    visible: bool = True
    color: str = "#CCCCCC"  # Major line color
    minor_color: str = "#EEEEEE"  # Minor line color

    @property
    def minor_spacing(self) -> float:
        """Calculate minor grid spacing."""
        if self.minor_divisions <= 0:
            return self.spacing
        return self.spacing / self.minor_divisions

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "spacing": self.spacing,
            "minor_divisions": self.minor_divisions,
            "visible": self.visible,
            "color": self.color,
            "minor_color": self.minor_color,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GridAxisConfig:
        """Deserialize from dictionary."""
        return cls(
            spacing=data.get("spacing", 1.0),
            minor_divisions=data.get("minor_divisions", 4),
            visible=data.get("visible", True),
            color=data.get("color", "#CCCCCC"),
            minor_color=data.get("minor_color", "#EEEEEE"),
        )


@dataclass
class GridConfig:
    """
    Complete grid configuration for the modeling environment.

    Supports independent configuration for X, Y, and Z axes,
    snap settings, and display options.
    """

    # Axis configurations
    x_axis: GridAxisConfig = field(default_factory=GridAxisConfig)
    y_axis: GridAxisConfig = field(default_factory=GridAxisConfig)
    z_axis: GridAxisConfig = field(default_factory=lambda: GridAxisConfig(visible=False))

    # Global settings
    enabled: bool = True
    snap_mode: SnapMode = SnapMode.GRID
    snap_tolerance: float = 0.1  # Snap tolerance in meters

    # Display settings
    show_major: bool = True
    show_minor: bool = True
    major_line_width: float = 1.0
    minor_line_width: float = 0.5
    opacity: float = 0.5

    # Grid extent
    extent: float = 50.0  # Grid extends from -extent to +extent

    def set_uniform_spacing(self, spacing: float) -> None:
        """Set the same spacing for all axes."""
        self.x_axis.spacing = spacing
        self.y_axis.spacing = spacing
        self.z_axis.spacing = spacing

    def snap_coordinate(self, value: float, axis: str = "x") -> float:
        """
        Snap a coordinate value to the grid.

        Args:
            value: Coordinate value to snap
            axis: Which axis ('x', 'y', or 'z')

        Returns:
            Snapped coordinate value
        """
        if self.snap_mode == SnapMode.NONE:
            return value

        config = self._get_axis_config(axis)
        if not config.visible:
            return value

        # Determine snap spacing (use minor if showing minor grid)
        snap_spacing = config.minor_spacing if self.show_minor else config.spacing

        # Snap to nearest grid line
        snapped = round(value / snap_spacing) * snap_spacing

        # Only apply snap if within tolerance
        if abs(value - snapped) <= self.snap_tolerance:
            return snapped

        return value

    def snap_point(
        self, x: float, y: float, z: float
    ) -> tuple[float, float, float]:
        """
        Snap a 3D point to the grid.

        Args:
            x, y, z: Point coordinates

        Returns:
            Tuple of snapped (x, y, z) coordinates
        """
        return (
            self.snap_coordinate(x, "x"),
            self.snap_coordinate(y, "y"),
            self.snap_coordinate(z, "z"),
        )

    def _get_axis_config(self, axis: str) -> GridAxisConfig:
        """Get configuration for an axis."""
        if axis.lower() == "x":
            return self.x_axis
        if axis.lower() == "y":
            return self.y_axis
        if axis.lower() == "z":
            return self.z_axis
        return self.x_axis

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to dictionary."""
        return {
            "x_axis": self.x_axis.to_dict(),
            "y_axis": self.y_axis.to_dict(),
            "z_axis": self.z_axis.to_dict(),
            "enabled": self.enabled,
            "snap_mode": self.snap_mode.value,
            "snap_tolerance": self.snap_tolerance,
            "show_major": self.show_major,
            "show_minor": self.show_minor,
            "major_line_width": self.major_line_width,
            "minor_line_width": self.minor_line_width,
            "opacity": self.opacity,
            "extent": self.extent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GridConfig:
        """Deserialize configuration from dictionary."""
        return cls(
            x_axis=GridAxisConfig.from_dict(data.get("x_axis", {})),
            y_axis=GridAxisConfig.from_dict(data.get("y_axis", {})),
            z_axis=GridAxisConfig.from_dict(data.get("z_axis", {})),
            enabled=data.get("enabled", True),
            snap_mode=SnapMode(data.get("snap_mode", "grid")),
            snap_tolerance=data.get("snap_tolerance", 0.1),
            show_major=data.get("show_major", True),
            show_minor=data.get("show_minor", True),
            major_line_width=data.get("major_line_width", 1.0),
            minor_line_width=data.get("minor_line_width", 0.5),
            opacity=data.get("opacity", 0.5),
            extent=data.get("extent", 50.0),
        )

    def copy(self) -> GridConfig:
        """Create a copy of this configuration."""
        return GridConfig.from_dict(self.to_dict())


# Default configurations for common use cases
def create_metric_grid(spacing: float = 1.0) -> GridConfig:
    """Create a metric grid with standard settings."""
    config = GridConfig()
    config.set_uniform_spacing(spacing)
    config.x_axis.minor_divisions = 4  # 0.25m minor grid
    config.y_axis.minor_divisions = 4
    config.z_axis.minor_divisions = 4
    return config


def create_imperial_grid(spacing_ft: float = 1.0) -> GridConfig:
    """Create an imperial grid (spacing in feet, converted to meters)."""
    spacing_m = spacing_ft * 0.3048
    config = GridConfig()
    config.set_uniform_spacing(spacing_m)
    config.x_axis.minor_divisions = 12  # 1 inch divisions
    config.y_axis.minor_divisions = 12
    config.z_axis.minor_divisions = 12
    return config

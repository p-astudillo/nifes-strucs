"""
Grid layer renderer for the 3D viewport.

Renders major and minor grid lines on the XY, XZ, or YZ planes
based on GridConfig settings.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

import numpy as np
import pyvista as pv

if TYPE_CHECKING:
    from paz.core.grid_config import GridConfig


class GridPlane(Enum):
    """Grid plane orientation."""

    XY = "xy"  # Horizontal plane (floor)
    XZ = "xz"  # Vertical plane (front wall)
    YZ = "yz"  # Vertical plane (side wall)


@dataclass
class GridMeshes:
    """Container for grid meshes."""

    major: pv.PolyData | None = None
    minor: pv.PolyData | None = None


class GridLayer:
    """
    Renders grid lines in the 3D viewport.

    Creates PyVista meshes for major and minor grid lines
    that can be added to a plotter.
    """

    def __init__(self, config: GridConfig | None = None) -> None:
        """
        Initialize grid layer.

        Args:
            config: Grid configuration (uses defaults if not provided)
        """
        from paz.core.grid_config import GridConfig

        self._config = config or GridConfig()
        self._plane = GridPlane.XY
        self._z_offset = 0.0  # Vertical offset for XY plane

    @property
    def config(self) -> GridConfig:
        """Get current configuration."""
        return self._config

    @config.setter
    def config(self, value: GridConfig) -> None:
        """Set configuration."""
        self._config = value

    @property
    def plane(self) -> GridPlane:
        """Get current grid plane."""
        return self._plane

    @plane.setter
    def plane(self, value: GridPlane) -> None:
        """Set grid plane."""
        self._plane = value

    def set_z_offset(self, offset: float) -> None:
        """Set vertical offset for XY plane grid."""
        self._z_offset = offset

    def build_meshes(self) -> GridMeshes:
        """
        Build grid meshes based on current configuration.

        Returns:
            GridMeshes with major and minor line meshes
        """
        if not self._config.enabled:
            return GridMeshes()

        result = GridMeshes()

        if self._config.show_major:
            result.major = self._build_major_grid()

        if self._config.show_minor:
            result.minor = self._build_minor_grid()

        return result

    def _build_major_grid(self) -> pv.PolyData:
        """Build mesh for major grid lines."""
        return self._build_grid_lines(is_major=True)

    def _build_minor_grid(self) -> pv.PolyData:
        """Build mesh for minor grid lines (excluding major lines)."""
        return self._build_grid_lines(is_major=False)

    def _build_grid_lines(self, is_major: bool) -> pv.PolyData:
        """
        Build grid line mesh.

        Args:
            is_major: True for major lines, False for minor only

        Returns:
            PyVista PolyData with line segments
        """
        extent = self._config.extent

        if self._plane == GridPlane.XY:
            return self._build_xy_grid(extent, is_major)
        if self._plane == GridPlane.XZ:
            return self._build_xz_grid(extent, is_major)
        if self._plane == GridPlane.YZ:
            return self._build_yz_grid(extent, is_major)

        return pv.PolyData()

    def _build_xy_grid(self, extent: float, is_major: bool) -> pv.PolyData:
        """Build grid on XY plane (horizontal)."""
        x_config = self._config.x_axis
        y_config = self._config.y_axis

        points: list[list[float]] = []
        lines: list[list[int]] = []
        point_idx = 0

        # X-direction lines (parallel to X axis)
        if y_config.visible:
            spacing = y_config.spacing if is_major else y_config.minor_spacing
            y_positions = self._get_line_positions(extent, spacing, is_major, y_config)

            for y in y_positions:
                points.append([-extent, y, self._z_offset])
                points.append([extent, y, self._z_offset])
                lines.append([2, point_idx, point_idx + 1])
                point_idx += 2

        # Y-direction lines (parallel to Y axis)
        if x_config.visible:
            spacing = x_config.spacing if is_major else x_config.minor_spacing
            x_positions = self._get_line_positions(extent, spacing, is_major, x_config)

            for x in x_positions:
                points.append([x, -extent, self._z_offset])
                points.append([x, extent, self._z_offset])
                lines.append([2, point_idx, point_idx + 1])
                point_idx += 2

        return self._create_line_mesh(points, lines)

    def _build_xz_grid(self, extent: float, is_major: bool) -> pv.PolyData:
        """Build grid on XZ plane (vertical, front)."""
        x_config = self._config.x_axis
        z_config = self._config.z_axis

        points: list[list[float]] = []
        lines: list[list[int]] = []
        point_idx = 0

        # Horizontal lines (Z positions)
        if z_config.visible:
            spacing = z_config.spacing if is_major else z_config.minor_spacing
            z_positions = self._get_line_positions(extent, spacing, is_major, z_config)

            for z in z_positions:
                points.append([-extent, 0, z])
                points.append([extent, 0, z])
                lines.append([2, point_idx, point_idx + 1])
                point_idx += 2

        # Vertical lines (X positions)
        if x_config.visible:
            spacing = x_config.spacing if is_major else x_config.minor_spacing
            x_positions = self._get_line_positions(extent, spacing, is_major, x_config)

            for x in x_positions:
                points.append([x, 0, -extent])
                points.append([x, 0, extent])
                lines.append([2, point_idx, point_idx + 1])
                point_idx += 2

        return self._create_line_mesh(points, lines)

    def _build_yz_grid(self, extent: float, is_major: bool) -> pv.PolyData:
        """Build grid on YZ plane (vertical, side)."""
        y_config = self._config.y_axis
        z_config = self._config.z_axis

        points: list[list[float]] = []
        lines: list[list[int]] = []
        point_idx = 0

        # Horizontal lines (Z positions)
        if z_config.visible:
            spacing = z_config.spacing if is_major else z_config.minor_spacing
            z_positions = self._get_line_positions(extent, spacing, is_major, z_config)

            for z in z_positions:
                points.append([0, -extent, z])
                points.append([0, extent, z])
                lines.append([2, point_idx, point_idx + 1])
                point_idx += 2

        # Vertical lines (Y positions)
        if y_config.visible:
            spacing = y_config.spacing if is_major else y_config.minor_spacing
            y_positions = self._get_line_positions(extent, spacing, is_major, y_config)

            for y in y_positions:
                points.append([0, y, -extent])
                points.append([0, y, extent])
                lines.append([2, point_idx, point_idx + 1])
                point_idx += 2

        return self._create_line_mesh(points, lines)

    def _get_line_positions(
        self,
        extent: float,
        spacing: float,
        is_major: bool,
        axis_config: Any,
    ) -> list[float]:
        """
        Get positions for grid lines.

        For major lines: returns all major positions
        For minor lines: returns only minor positions (excluding majors)
        """
        if spacing <= 0:
            return []

        positions = []
        n_lines = int(extent / spacing) + 1

        for i in range(-n_lines, n_lines + 1):
            pos = i * spacing

            if is_major:
                # For major grid, only include major spacing positions
                if abs(pos) <= extent:
                    positions.append(pos)
            else:
                # For minor grid, exclude positions that fall on major lines
                major_spacing = axis_config.spacing
                is_on_major = abs(pos % major_spacing) < 1e-9 or abs(pos % major_spacing - major_spacing) < 1e-9

                if not is_on_major and abs(pos) <= extent:
                    positions.append(pos)

        return positions

    def _create_line_mesh(
        self, points: list[list[float]], lines: list[list[int]]
    ) -> pv.PolyData:
        """Create PyVista mesh from points and lines."""
        if not points:
            return pv.PolyData()

        points_array = np.array(points, dtype=np.float64)
        lines_array = np.hstack(lines) if lines else np.array([], dtype=np.int64)

        mesh = pv.PolyData(points_array)
        if len(lines_array) > 0:
            mesh.lines = lines_array  # type: ignore[assignment]

        return mesh

    def get_major_color(self) -> str:
        """Get color for major grid lines based on plane."""
        if self._plane == GridPlane.XY:
            return self._config.x_axis.color
        if self._plane == GridPlane.XZ:
            return self._config.x_axis.color
        return self._config.y_axis.color

    def get_minor_color(self) -> str:
        """Get color for minor grid lines based on plane."""
        if self._plane == GridPlane.XY:
            return self._config.x_axis.minor_color
        if self._plane == GridPlane.XZ:
            return self._config.x_axis.minor_color
        return self._config.y_axis.minor_color

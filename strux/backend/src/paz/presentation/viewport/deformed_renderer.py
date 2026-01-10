"""
Deformed shape renderer for structural analysis results.

Calculates and renders deformed geometry with color mapping based on
displacement values.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyvista as pv

from paz.presentation.viewport.render_modes import DisplacementComponent


if TYPE_CHECKING:
    from paz.domain.model import Frame, StructuralModel
    from paz.domain.results import AnalysisResults


class DeformedRenderer:
    """
    Renders deformed structural shapes from analysis results.

    Handles:
    - Calculating displaced node positions
    - Interpolating deformations along frames
    - Building PyVista mesh with scalar values for coloring
    """

    def __init__(self, interpolation_points: int = 10) -> None:
        """
        Initialize renderer.

        Args:
            interpolation_points: Number of points per frame for smooth deformation.
                Higher values give smoother curves but increase memory usage.
        """
        self._interpolation_points = max(2, interpolation_points)

    @property
    def interpolation_points(self) -> int:
        """Number of interpolation points per frame."""
        return self._interpolation_points

    @interpolation_points.setter
    def interpolation_points(self, value: int) -> None:
        """Set interpolation points (minimum 2)."""
        self._interpolation_points = max(2, value)

    def build_deformed_mesh(
        self,
        model: StructuralModel,
        results: AnalysisResults,
        scale: float,
        component: DisplacementComponent,
    ) -> tuple[pv.PolyData, np.ndarray]:
        """
        Build PyVista mesh of deformed structure.

        Args:
            model: Original structural model
            results: Analysis results with displacements
            scale: Deformation scale factor (1-10000)
            component: Which displacement component to use for coloring

        Returns:
            Tuple of (mesh, scalar_values) where scalars are displacement values
            for color mapping
        """
        if not model.frames:
            return pv.PolyData(), np.array([])

        # Pre-calculate displaced node positions
        displaced_positions = self._calculate_displaced_positions(model, results, scale)

        # Pre-allocate arrays
        n_frames = len(model.frames)
        n_points_per_frame = self._interpolation_points
        total_points = n_frames * n_points_per_frame
        total_lines = n_frames * (n_points_per_frame - 1)

        points = np.zeros((total_points, 3), dtype=np.float64)
        scalars = np.zeros(total_points, dtype=np.float64)
        lines = np.zeros(total_lines * 3, dtype=np.int64)

        line_index = 0
        valid_frames = 0

        for frame in model.frames:
            frame_points, frame_scalars = self._interpolate_frame(
                frame,
                model,
                results,
                scale,
                component,
                displaced_positions,
            )

            if frame_points is None:
                continue

            n_pts = len(frame_points)
            start_idx = valid_frames * n_points_per_frame

            points[start_idx : start_idx + n_pts] = frame_points
            scalars[start_idx : start_idx + n_pts] = frame_scalars

            # Create line connectivity for this frame
            for i in range(n_pts - 1):
                lines[line_index * 3] = 2
                lines[line_index * 3 + 1] = start_idx + i
                lines[line_index * 3 + 2] = start_idx + i + 1
                line_index += 1

            valid_frames += 1

        if valid_frames == 0:
            return pv.PolyData(), np.array([])

        # Trim arrays to actual size
        actual_points = valid_frames * n_points_per_frame
        actual_lines = valid_frames * (n_points_per_frame - 1)

        points = points[:actual_points]
        scalars = scalars[:actual_points]
        lines = lines[: actual_lines * 3]

        mesh = pv.PolyData(points)
        mesh.lines = lines  # type: ignore[assignment]

        return mesh, scalars

    def build_deformed_nodes(
        self,
        model: StructuralModel,
        results: AnalysisResults,
        scale: float,
        component: DisplacementComponent,
    ) -> tuple[pv.PolyData, np.ndarray]:
        """
        Build point cloud of deformed node positions.

        Args:
            model: Original structural model
            results: Analysis results with displacements
            scale: Deformation scale factor
            component: Displacement component for scalar values

        Returns:
            Tuple of (point_cloud, scalar_values)
        """
        if not model.nodes:
            return pv.PolyData(), np.array([])

        points = []
        scalars = []
        node_ids = []

        for node in model.nodes:
            disp = results.get_displacement(node.id)

            if disp is None:
                ux, uy, uz = 0.0, 0.0, 0.0
            else:
                ux, uy, uz = disp.Ux, disp.Uy, disp.Uz

            # Deformed position
            x_def = node.x + scale * ux
            y_def = node.y + scale * uy
            z_def = node.z + scale * uz

            points.append([x_def, y_def, z_def])
            scalars.append(self._get_scalar_value(ux, uy, uz, component))
            node_ids.append(node.id)

        points_array = np.array(points, dtype=np.float64)
        scalars_array = np.array(scalars, dtype=np.float64)

        point_cloud = pv.PolyData(points_array)
        point_cloud["node_id"] = np.array(node_ids, dtype=np.int64)  # type: ignore[assignment]

        return point_cloud, scalars_array

    def get_deformed_node_position(
        self,
        node_id: int,
        model: StructuralModel,
        results: AnalysisResults,
        scale: float,
    ) -> tuple[float, float, float]:
        """
        Get deformed position of a single node.

        Args:
            node_id: Node ID
            model: Structural model
            results: Analysis results
            scale: Deformation scale factor

        Returns:
            Tuple of (x, y, z) deformed coordinates
        """
        node = model.get_node(node_id)
        disp = results.get_displacement(node_id)

        if disp is None:
            return (node.x, node.y, node.z)

        return (
            node.x + scale * disp.Ux,
            node.y + scale * disp.Uy,
            node.z + scale * disp.Uz,
        )

    def get_displacement_range(
        self,
        results: AnalysisResults,
        component: DisplacementComponent,
    ) -> tuple[float, float]:
        """
        Get min/max displacement values for a component.

        Args:
            results: Analysis results
            component: Displacement component

        Returns:
            Tuple of (min_value, max_value)
        """
        if not results.displacements:
            return (0.0, 0.0)

        values = []
        for disp in results.displacements.values():
            scalar = self._get_scalar_value(disp.Ux, disp.Uy, disp.Uz, component)
            values.append(scalar)

        if not values:
            return (0.0, 0.0)

        return (min(values), max(values))

    def _calculate_displaced_positions(
        self,
        model: StructuralModel,
        results: AnalysisResults,
        scale: float,
    ) -> dict[int, tuple[float, float, float]]:
        """
        Pre-calculate displaced positions for all nodes.

        Args:
            model: Structural model
            results: Analysis results
            scale: Deformation scale factor

        Returns:
            Dictionary mapping node_id to displaced (x, y, z)
        """
        positions = {}

        for node in model.nodes:
            disp = results.get_displacement(node.id)

            if disp is None:
                positions[node.id] = (node.x, node.y, node.z)
            else:
                positions[node.id] = (
                    node.x + scale * disp.Ux,
                    node.y + scale * disp.Uy,
                    node.z + scale * disp.Uz,
                )

        return positions

    def _interpolate_frame(
        self,
        frame: Frame,
        _model: StructuralModel,
        results: AnalysisResults,
        _scale: float,
        component: DisplacementComponent,
        displaced_positions: dict[int, tuple[float, float, float]],
    ) -> tuple[np.ndarray | None, np.ndarray | None]:
        """
        Interpolate deformation along a frame element.

        Uses linear interpolation between end nodes.

        Args:
            frame: Frame element
            _model: Structural model (unused, positions pre-calculated)
            results: Analysis results
            _scale: Deformation scale (unused, positions pre-calculated)
            component: Displacement component for scalars
            displaced_positions: Pre-calculated displaced node positions

        Returns:
            Tuple of (points_array, scalars_array) or (None, None) if invalid
        """
        # Get displaced end positions
        pos_i = displaced_positions.get(frame.node_i_id)
        pos_j = displaced_positions.get(frame.node_j_id)

        if pos_i is None or pos_j is None:
            return None, None

        # Get displacement values for scalar interpolation
        disp_i = results.get_displacement(frame.node_i_id)
        disp_j = results.get_displacement(frame.node_j_id)

        if disp_i is None:
            ux_i, uy_i, uz_i = 0.0, 0.0, 0.0
        else:
            ux_i, uy_i, uz_i = disp_i.Ux, disp_i.Uy, disp_i.Uz

        if disp_j is None:
            ux_j, uy_j, uz_j = 0.0, 0.0, 0.0
        else:
            ux_j, uy_j, uz_j = disp_j.Ux, disp_j.Uy, disp_j.Uz

        # Interpolate along frame
        n_pts = self._interpolation_points
        points = np.zeros((n_pts, 3), dtype=np.float64)
        scalars = np.zeros(n_pts, dtype=np.float64)

        for i in range(n_pts):
            t = i / (n_pts - 1)

            # Interpolated position (using displaced positions)
            points[i, 0] = pos_i[0] + t * (pos_j[0] - pos_i[0])
            points[i, 1] = pos_i[1] + t * (pos_j[1] - pos_i[1])
            points[i, 2] = pos_i[2] + t * (pos_j[2] - pos_i[2])

            # Interpolated displacement for scalar
            ux = ux_i + t * (ux_j - ux_i)
            uy = uy_i + t * (uy_j - uy_i)
            uz = uz_i + t * (uz_j - uz_i)

            scalars[i] = self._get_scalar_value(ux, uy, uz, component)

        return points, scalars

    def _get_scalar_value(
        self,
        ux: float,
        uy: float,
        uz: float,
        component: DisplacementComponent,
    ) -> float:
        """
        Get scalar value for a displacement based on selected component.

        Args:
            ux: X displacement
            uy: Y displacement
            uz: Z displacement
            component: Which component to return

        Returns:
            Scalar value for color mapping
        """
        if component == DisplacementComponent.UX:
            return ux
        if component == DisplacementComponent.UY:
            return uy
        if component == DisplacementComponent.UZ:
            return uz
        # TOTAL - magnitude
        return float(np.sqrt(ux**2 + uy**2 + uz**2))

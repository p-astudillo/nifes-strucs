"""
Force diagram renderer for structural analysis results.

Renders internal force diagrams (M, V, P, T) along frame elements
with color mapping for positive/negative values.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

import numpy as np
import pyvista as pv


if TYPE_CHECKING:
    from paz.domain.model import Frame, StructuralModel
    from paz.domain.results import AnalysisResults, FrameResult


class ForceType(Enum):
    """Type of internal force to visualize."""

    P = "P"  # Axial force
    V2 = "V2"  # Shear in local 2
    V3 = "V3"  # Shear in local 3
    T = "T"  # Torsion
    M2 = "M2"  # Moment about local 2
    M3 = "M3"  # Moment about local 3


@dataclass
class DiagramSettings:
    """Settings for force diagram visualization."""

    force_type: ForceType = ForceType.M3
    scale: float = 1.0  # Diagram scale factor
    positive_color: str = "red"
    negative_color: str = "blue"
    line_width: float = 2.0
    fill_opacity: float = 0.3
    show_values: bool = True
    show_max_values: bool = True
    interpolation_points: int = 20

    # Diagram direction in local coordinates
    # M3 is typically shown perpendicular to local-2 axis
    DIAGRAM_DIRECTIONS: ClassVar[dict[ForceType, tuple[int, int]]] = {
        ForceType.P: (0, 1),  # Along local-1, show in local-2
        ForceType.V2: (0, 1),  # Along local-1, show in local-2
        ForceType.V3: (0, 2),  # Along local-1, show in local-3
        ForceType.T: (0, 1),  # Along local-1, show in local-2
        ForceType.M2: (0, 2),  # Along local-1, show in local-3
        ForceType.M3: (0, 1),  # Along local-1, show in local-2
    }


class ForceDiagramRenderer:
    """
    Renders force diagrams for frame elements.

    Creates visual representations of internal forces (P, V, M, T)
    along frame elements as filled diagrams perpendicular to the frame axis.
    """

    def __init__(self, settings: DiagramSettings | None = None) -> None:
        """
        Initialize renderer.

        Args:
            settings: Diagram visualization settings
        """
        self._settings = settings or DiagramSettings()

    @property
    def settings(self) -> DiagramSettings:
        """Get current settings."""
        return self._settings

    @settings.setter
    def settings(self, value: DiagramSettings) -> None:
        """Set settings."""
        self._settings = value

    def build_diagram_mesh(
        self,
        model: StructuralModel,
        results: AnalysisResults,
        force_type: ForceType | None = None,
        frame_ids: set[int] | None = None,
    ) -> tuple[pv.PolyData, np.ndarray]:
        """
        Build PyVista mesh for force diagrams.

        Args:
            model: Structural model
            results: Analysis results with frame forces
            force_type: Override force type from settings
            frame_ids: Optional set of frame IDs to include (None = all frames)

        Returns:
            Tuple of (mesh, scalar_values) for coloring
        """
        if force_type is None:
            force_type = self._settings.force_type

        all_points: list[list[float]] = []
        all_lines: list[list[int]] = []
        all_scalars: list[float] = []
        point_idx = 0

        for frame in model.frames:
            # Skip frames not in filter
            if frame_ids is not None and frame.id not in frame_ids:
                continue

            frame_result = results.get_frame_result(frame.id)
            if frame_result is None or not frame_result.forces:
                continue

            points, lines, scalars = self._build_frame_diagram(
                frame, model, frame_result, force_type
            )

            if points is None:
                continue

            # Offset line indices
            for line in lines:
                all_lines.append([line[0], line[1] + point_idx, line[2] + point_idx])

            all_points.extend(points)
            all_scalars.extend(scalars)
            point_idx += len(points)

        if not all_points:
            return pv.PolyData(), np.array([])

        points_array = np.array(all_points, dtype=np.float64)
        lines_array = np.hstack(all_lines) if all_lines else np.array([], dtype=np.int64)
        scalars_array = np.array(all_scalars, dtype=np.float64)

        mesh = pv.PolyData(points_array)
        if len(lines_array) > 0:
            mesh.lines = lines_array  # type: ignore[assignment]

        return mesh, scalars_array

    def build_filled_diagram_mesh(
        self,
        model: StructuralModel,
        results: AnalysisResults,
        force_type: ForceType | None = None,
        frame_ids: set[int] | None = None,
    ) -> tuple[pv.PolyData, np.ndarray]:
        """
        Build filled polygon mesh for force diagrams.

        Creates triangulated surfaces for filled diagram visualization.

        Args:
            model: Structural model
            results: Analysis results
            force_type: Override force type
            frame_ids: Optional set of frame IDs to include (None = all frames)

        Returns:
            Tuple of (mesh, scalar_values)
        """
        if force_type is None:
            force_type = self._settings.force_type

        all_points: list[list[float]] = []
        all_faces: list[list[int]] = []
        all_scalars: list[float] = []
        point_idx = 0

        for frame in model.frames:
            # Skip frames not in filter
            if frame_ids is not None and frame.id not in frame_ids:
                continue

            frame_result = results.get_frame_result(frame.id)
            if frame_result is None or not frame_result.forces:
                continue

            points, faces, scalars = self._build_frame_filled_diagram(
                frame, model, frame_result, force_type
            )

            if points is None:
                continue

            # Offset face indices
            for face in faces:
                all_faces.append([face[0]] + [f + point_idx for f in face[1:]])

            all_points.extend(points)
            all_scalars.extend(scalars)
            point_idx += len(points)

        if not all_points:
            return pv.PolyData(), np.array([])

        points_array = np.array(all_points, dtype=np.float64)
        faces_array = np.hstack(all_faces) if all_faces else np.array([], dtype=np.int64)
        scalars_array = np.array(all_scalars, dtype=np.float64)

        mesh = pv.PolyData(points_array, faces=faces_array)

        return mesh, scalars_array

    def get_value_labels(
        self,
        model: StructuralModel,
        results: AnalysisResults,
        force_type: ForceType | None = None,
        frame_ids: set[int] | None = None,
    ) -> tuple[np.ndarray, list[str]]:
        """
        Get positions and labels for force values.

        Returns labels at extremes and maximum points.

        Args:
            model: Structural model
            results: Analysis results
            force_type: Force type to label
            frame_ids: Optional set of frame IDs to include (None = all frames)

        Returns:
            Tuple of (positions array, labels list)
        """
        if force_type is None:
            force_type = self._settings.force_type

        positions: list[list[float]] = []
        labels: list[str] = []

        for frame in model.frames:
            # Skip frames not in filter
            if frame_ids is not None and frame.id not in frame_ids:
                continue

            frame_result = results.get_frame_result(frame.id)
            if frame_result is None or not frame_result.forces:
                continue

            node_i = model.get_node(frame.node_i_id)
            node_j = model.get_node(frame.node_j_id)

            # Get frame axis vector
            dx = node_j.x - node_i.x
            dy = node_j.y - node_i.y
            dz = node_j.z - node_i.z
            length = np.sqrt(dx**2 + dy**2 + dz**2)

            if length < 1e-6:
                continue

            # Calculate perpendicular direction for label offset
            perp = self._get_perpendicular_direction(dx, dy, dz)

            # Find max value location and extremes
            max_val = 0.0
            max_loc = 0.5
            start_val = 0.0
            end_val = 0.0

            for forces in frame_result.forces:
                val = self._get_force_value(forces, force_type)
                if abs(val) > abs(max_val):
                    max_val = val
                    max_loc = forces.location
                if forces.location == 0.0 or forces.location < 0.01:
                    start_val = val
                if forces.location == 1.0 or forces.location > 0.99:
                    end_val = val

            # Label offset based on diagram scale
            offset = self._settings.scale * max(abs(max_val), 0.1) * 1.2

            # Start label
            if self._settings.show_values and abs(start_val) > 1e-6:
                pos = [
                    node_i.x + perp[0] * offset * np.sign(start_val),
                    node_i.y + perp[1] * offset * np.sign(start_val),
                    node_i.z + perp[2] * offset * np.sign(start_val),
                ]
                positions.append(pos)
                labels.append(f"{start_val:.1f}")

            # End label
            if self._settings.show_values and abs(end_val) > 1e-6:
                pos = [
                    node_j.x + perp[0] * offset * np.sign(end_val),
                    node_j.y + perp[1] * offset * np.sign(end_val),
                    node_j.z + perp[2] * offset * np.sign(end_val),
                ]
                positions.append(pos)
                labels.append(f"{end_val:.1f}")

            # Max value label (if different from extremes)
            if self._settings.show_max_values and 0.1 < max_loc < 0.9:
                if abs(max_val) > max(abs(start_val), abs(end_val)) * 1.1:
                    t = max_loc
                    pos = [
                        node_i.x + t * dx + perp[0] * offset * np.sign(max_val),
                        node_i.y + t * dy + perp[1] * offset * np.sign(max_val),
                        node_i.z + t * dz + perp[2] * offset * np.sign(max_val),
                    ]
                    positions.append(pos)
                    labels.append(f"{max_val:.1f}")

        if not positions:
            return np.array([]).reshape(0, 3), []

        return np.array(positions, dtype=np.float64), labels

    def get_global_extremes(
        self,
        results: AnalysisResults,
        force_type: ForceType | None = None,
    ) -> dict[str, float]:
        """
        Get global maximum and minimum values for a force type.

        Args:
            results: Analysis results
            force_type: Force type to analyze

        Returns:
            Dictionary with 'max', 'min', 'abs_max' keys
        """
        if force_type is None:
            force_type = self._settings.force_type

        max_val = float("-inf")
        min_val = float("inf")

        for frame_result in results.frame_results.values():
            for forces in frame_result.forces:
                val = self._get_force_value(forces, force_type)
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

    def get_frame_with_max_value(
        self,
        results: AnalysisResults,
        force_type: ForceType | None = None,
    ) -> tuple[int | None, float]:
        """
        Find the frame with maximum absolute value.

        Args:
            results: Analysis results
            force_type: Force type to search

        Returns:
            Tuple of (frame_id, max_value) or (None, 0) if no results
        """
        if force_type is None:
            force_type = self._settings.force_type

        max_frame_id: int | None = None
        max_val = 0.0

        for frame_id, frame_result in results.frame_results.items():
            for forces in frame_result.forces:
                val = self._get_force_value(forces, force_type)
                if abs(val) > abs(max_val):
                    max_val = val
                    max_frame_id = frame_id

        return max_frame_id, max_val

    def _build_frame_diagram(
        self,
        frame: Frame,
        model: StructuralModel,
        frame_result: FrameResult,
        force_type: ForceType,
    ) -> tuple[list[list[float]] | None, list[list[int]], list[float]]:
        """Build diagram lines for a single frame."""
        node_i = model.get_node(frame.node_i_id)
        node_j = model.get_node(frame.node_j_id)

        dx = node_j.x - node_i.x
        dy = node_j.y - node_i.y
        dz = node_j.z - node_i.z
        length = np.sqrt(dx**2 + dy**2 + dz**2)

        if length < 1e-6:
            return None, [], []

        # Get perpendicular direction for diagram
        perp = self._get_perpendicular_direction(dx, dy, dz)

        # Interpolate forces along frame
        n_pts = self._settings.interpolation_points
        points: list[list[float]] = []
        scalars: list[float] = []
        lines: list[list[int]] = []

        # Sort forces by location
        sorted_forces = sorted(frame_result.forces, key=lambda f: f.location)

        for i in range(n_pts):
            t = i / (n_pts - 1)

            # Interpolate force value at this location
            val = self._interpolate_force(sorted_forces, t, force_type)

            # Calculate point on frame axis
            x_base = node_i.x + t * dx
            y_base = node_i.y + t * dy
            z_base = node_i.z + t * dz

            # Offset perpendicular to frame by scaled value
            offset = self._settings.scale * val
            x = x_base + perp[0] * offset
            y = y_base + perp[1] * offset
            z = z_base + perp[2] * offset

            points.append([x, y, z])
            scalars.append(val)

            # Connect to previous point
            if i > 0:
                lines.append([2, i - 1, i])

        return points, lines, scalars

    def _build_frame_filled_diagram(
        self,
        frame: Frame,
        model: StructuralModel,
        frame_result: FrameResult,
        force_type: ForceType,
    ) -> tuple[list[list[float]] | None, list[list[int]], list[float]]:
        """Build filled diagram triangles for a single frame."""
        node_i = model.get_node(frame.node_i_id)
        node_j = model.get_node(frame.node_j_id)

        dx = node_j.x - node_i.x
        dy = node_j.y - node_i.y
        dz = node_j.z - node_i.z
        length = np.sqrt(dx**2 + dy**2 + dz**2)

        if length < 1e-6:
            return None, [], []

        perp = self._get_perpendicular_direction(dx, dy, dz)

        n_pts = self._settings.interpolation_points
        sorted_forces = sorted(frame_result.forces, key=lambda f: f.location)

        # Create points along frame axis and diagram curve
        base_points: list[list[float]] = []
        diagram_points: list[list[float]] = []
        scalars: list[float] = []

        for i in range(n_pts):
            t = i / (n_pts - 1)
            val = self._interpolate_force(sorted_forces, t, force_type)

            x_base = node_i.x + t * dx
            y_base = node_i.y + t * dy
            z_base = node_i.z + t * dz

            base_points.append([x_base, y_base, z_base])

            offset = self._settings.scale * val
            diagram_points.append([
                x_base + perp[0] * offset,
                y_base + perp[1] * offset,
                z_base + perp[2] * offset,
            ])
            scalars.append(val)

        # Combine points: base points first, then diagram points
        all_points = base_points + diagram_points
        all_scalars = [0.0] * n_pts + scalars  # Base points have zero scalar

        # Create triangles between base and diagram
        faces: list[list[int]] = []
        for i in range(n_pts - 1):
            # Two triangles per segment
            base_i = i
            base_j = i + 1
            diag_i = n_pts + i
            diag_j = n_pts + i + 1

            faces.append([3, base_i, base_j, diag_i])
            faces.append([3, base_j, diag_j, diag_i])

        return all_points, faces, all_scalars

    def _get_perpendicular_direction(
        self, dx: float, dy: float, dz: float
    ) -> tuple[float, float, float]:
        """Calculate perpendicular direction for diagram display."""
        length = np.sqrt(dx**2 + dy**2 + dz**2)
        if length < 1e-6:
            return (0.0, 1.0, 0.0)

        # Normalize frame direction
        ux = dx / length
        uy = dy / length
        uz = dz / length

        # Choose reference vector for cross product
        # Use global Y if frame is not vertical, otherwise use global X
        if abs(uz) < 0.99:
            ref = (0.0, 0.0, 1.0)  # Global Z
        else:
            ref = (1.0, 0.0, 0.0)  # Global X

        # Cross product to get perpendicular
        px = uy * ref[2] - uz * ref[1]
        py = uz * ref[0] - ux * ref[2]
        pz = ux * ref[1] - uy * ref[0]

        # Normalize
        p_len = np.sqrt(px**2 + py**2 + pz**2)
        if p_len < 1e-6:
            return (0.0, 1.0, 0.0)

        return (px / p_len, py / p_len, pz / p_len)

    def _interpolate_force(
        self,
        sorted_forces: list,
        t: float,
        force_type: ForceType,
    ) -> float:
        """Interpolate force value at location t (0-1)."""
        if not sorted_forces:
            return 0.0

        # Find surrounding force values
        prev_force = sorted_forces[0]
        next_force = sorted_forces[-1]

        for i, forces in enumerate(sorted_forces):
            if forces.location <= t:
                prev_force = forces
            if forces.location >= t:
                next_force = forces
                break

        # Linear interpolation
        prev_loc = prev_force.location
        next_loc = next_force.location
        prev_val = self._get_force_value(prev_force, force_type)
        next_val = self._get_force_value(next_force, force_type)

        if abs(next_loc - prev_loc) < 1e-6:
            return prev_val

        factor = (t - prev_loc) / (next_loc - prev_loc)
        return prev_val + factor * (next_val - prev_val)

    def _get_force_value(self, forces: object, force_type: ForceType) -> float:
        """Extract specific force value from FrameForces."""
        if force_type == ForceType.P:
            return float(getattr(forces, "P", 0.0))
        if force_type == ForceType.V2:
            return float(getattr(forces, "V2", 0.0))
        if force_type == ForceType.V3:
            return float(getattr(forces, "V3", 0.0))
        if force_type == ForceType.T:
            return float(getattr(forces, "T", 0.0))
        if force_type == ForceType.M2:
            return float(getattr(forces, "M2", 0.0))
        if force_type == ForceType.M3:
            return float(getattr(forces, "M3", 0.0))
        return 0.0

"""
Build PyVista meshes from structural models.

Converts domain model objects into PyVista geometry for 3D rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyvista as pv


if TYPE_CHECKING:
    from paz.domain.model import StructuralModel


class MeshBuilder:
    """
    Builds PyVista meshes from structural models.

    Creates optimized mesh representations for rendering nodes, frames,
    and support symbols.
    """

    def build_frame_mesh(self, model: StructuralModel) -> pv.PolyData:
        """
        Build line mesh for all frames.

        Creates a single PyVista PolyData with all frame lines for efficient
        rendering.

        Args:
            model: Structural model containing nodes and frames

        Returns:
            PyVista PolyData with lines connecting frame endpoints
        """
        if not model.frames:
            return pv.PolyData()

        # Build node coordinate lookup
        node_positions = {node.id: (node.x, node.y, node.z) for node in model.nodes}

        # Pre-allocate arrays for performance
        n_frames = len(model.frames)
        points = np.zeros((n_frames * 2, 3), dtype=np.float64)
        lines = np.zeros(n_frames * 3, dtype=np.int64)

        valid_frames = 0

        for frame in model.frames:
            pos_i = node_positions.get(frame.node_i_id)
            pos_j = node_positions.get(frame.node_j_id)

            if pos_i is None or pos_j is None:
                continue

            points[valid_frames * 2] = pos_i
            points[valid_frames * 2 + 1] = pos_j

            lines[valid_frames * 3] = 2  # Number of points in line
            lines[valid_frames * 3 + 1] = valid_frames * 2
            lines[valid_frames * 3 + 2] = valid_frames * 2 + 1

            valid_frames += 1

        if valid_frames == 0:
            return pv.PolyData()

        # Trim arrays to actual size
        points = points[: valid_frames * 2]
        lines = lines[: valid_frames * 3]

        mesh = pv.PolyData(points)
        mesh.lines = lines  # type: ignore[assignment]

        return mesh

    def build_node_points(self, model: StructuralModel) -> pv.PolyData:
        """
        Build point cloud from nodes.

        Args:
            model: Structural model containing nodes

        Returns:
            PyVista PolyData with node positions as points
        """
        if not model.nodes:
            return pv.PolyData()

        points = np.array(
            [[node.x, node.y, node.z] for node in model.nodes],
            dtype=np.float64,
        )

        point_cloud = pv.PolyData(points)

        # Add node IDs as scalar data for picking
        node_ids = np.array([node.id for node in model.nodes], dtype=np.int64)
        point_cloud["node_id"] = node_ids  # type: ignore[assignment]

        return point_cloud

    def build_support_glyphs(
        self,
        model: StructuralModel,
        glyph_size: float = 0.2,
    ) -> pv.PolyData | None:
        """
        Build support symbol geometry.

        Creates visual markers for supported nodes:
        - Fully fixed: cube
        - Pinned (translations only): cone pointing up
        - Partial: pyramid

        Args:
            model: Structural model containing nodes
            glyph_size: Size of support glyphs in model units

        Returns:
            Combined PyVista mesh of all support glyphs, or None if no supports
        """
        supported_nodes = model.get_supported_nodes()

        if not supported_nodes:
            return None

        glyphs: list[pv.PolyData] = []

        for node in supported_nodes:
            restraint = node.restraint

            # Determine support type based on restraints
            is_fully_fixed = all([
                restraint.ux,
                restraint.uy,
                restraint.uz,
                restraint.rx,
                restraint.ry,
                restraint.rz,
            ])

            is_pinned = all([restraint.ux, restraint.uy, restraint.uz]) and not any([
                restraint.rx,
                restraint.ry,
                restraint.rz,
            ])

            # Position glyph below the node
            center = (node.x, node.y, node.z - glyph_size * 0.5)

            if is_fully_fixed:
                # Fixed support: cube
                glyph = pv.Cube(
                    center=center,
                    x_length=glyph_size,
                    y_length=glyph_size,
                    z_length=glyph_size,
                )
            elif is_pinned:
                # Pinned support: cone pointing up
                glyph = pv.Cone(
                    center=center,
                    direction=(0, 0, 1),
                    height=glyph_size,
                    radius=glyph_size * 0.5,
                    resolution=8,
                )
            else:
                # Partial restraint: small sphere
                glyph = pv.Sphere(
                    center=center,
                    radius=glyph_size * 0.4,
                )

            glyphs.append(glyph)

        if not glyphs:
            return None

        # Merge all glyphs into single mesh
        if len(glyphs) == 1:
            return glyphs[0]

        combined = glyphs[0]
        for glyph in glyphs[1:]:
            combined = combined.merge(glyph)

        return combined

    def build_node_labels(
        self,
        model: StructuralModel,
    ) -> tuple[np.ndarray, list[str]]:
        """
        Get node positions and labels for text rendering.

        Args:
            model: Structural model containing nodes

        Returns:
            Tuple of (positions array, labels list)
        """
        if not model.nodes:
            return np.array([]).reshape(0, 3), []

        positions = np.array(
            [[node.x, node.y, node.z] for node in model.nodes],
            dtype=np.float64,
        )
        labels = [str(node.id) for node in model.nodes]

        return positions, labels

    def build_frame_labels(
        self,
        model: StructuralModel,
    ) -> tuple[np.ndarray, list[str]]:
        """
        Get frame midpoint positions and labels for text rendering.

        Args:
            model: Structural model containing nodes and frames

        Returns:
            Tuple of (positions array, labels list)
        """
        if not model.frames:
            return np.array([]).reshape(0, 3), []

        node_positions = {node.id: (node.x, node.y, node.z) for node in model.nodes}

        positions = []
        labels = []

        for frame in model.frames:
            pos_i = node_positions.get(frame.node_i_id)
            pos_j = node_positions.get(frame.node_j_id)

            if pos_i is None or pos_j is None:
                continue

            # Midpoint of frame
            mid = (
                (pos_i[0] + pos_j[0]) / 2,
                (pos_i[1] + pos_j[1]) / 2,
                (pos_i[2] + pos_j[2]) / 2,
            )
            positions.append(mid)
            labels.append(str(frame.id))

        return np.array(positions, dtype=np.float64), labels

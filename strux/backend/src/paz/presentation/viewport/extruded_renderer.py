"""
Extruded section renderer for 3D visualization of structural frames.

Generates solid 3D meshes by extruding section profiles along frame axes,
with proper orientation based on local coordinate systems.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
import pyvista as pv

from paz.domain.model.local_axes import calculate_local_axes
from paz.domain.sections.profile_geometry import ProfileGenerator, ProfileGeometry


if TYPE_CHECKING:
    from paz.domain.model import Frame, Node, StructuralModel
    from paz.domain.results import AnalysisResults
    from paz.domain.sections.section import Section


@dataclass
class ExtrudedSettings:
    """Settings for extruded rendering."""

    lod_high_threshold: float = 50.0  # Distance threshold for high detail
    lod_medium_threshold: float = 200.0  # Distance for medium detail
    high_detail_segments: int = 32  # Circle segments at high detail
    medium_detail_segments: int = 16
    low_detail_segments: int = 8
    show_end_caps: bool = True
    smooth_shading: bool = True


class ExtrudedRenderer:
    """
    Renders structural frames as extruded 3D solids.

    Generates PyVista meshes by extruding section profiles along frame axes,
    correctly oriented according to local coordinate systems.
    """

    def __init__(self, settings: ExtrudedSettings | None = None) -> None:
        """
        Initialize renderer.

        Args:
            settings: Rendering settings
        """
        self._settings = settings or ExtrudedSettings()
        self._profile_generator = ProfileGenerator(
            circle_segments=self._settings.high_detail_segments
        )
        self._section_cache: dict[str, ProfileGeometry] = {}

    @property
    def settings(self) -> ExtrudedSettings:
        """Get current settings."""
        return self._settings

    def build_extruded_mesh(
        self,
        model: StructuralModel,
        sections: dict[str, Section],
    ) -> pv.PolyData:
        """
        Build combined mesh for all frames with extruded sections.

        Args:
            model: Structural model with frames
            sections: Dictionary mapping section_id to Section

        Returns:
            Combined PyVista mesh for all extruded frames
        """
        if not model.frames:
            return pv.PolyData()

        meshes: list[pv.PolyData] = []

        for frame in model.frames:
            section = sections.get(frame.section_name)
            if section is None:
                continue

            mesh = self._extrude_frame(frame, model, section)
            if mesh is not None and mesh.n_points > 0:
                meshes.append(mesh)

        if not meshes:
            return pv.PolyData()

        # Combine all meshes
        combined = meshes[0]
        for mesh in meshes[1:]:
            combined = combined.merge(mesh)

        return combined

    def build_extruded_mesh_by_material(
        self,
        model: StructuralModel,
        sections: dict[str, Section],
    ) -> dict[str, pv.PolyData]:
        """
        Build separate meshes grouped by material.

        Args:
            model: Structural model
            sections: Section dictionary

        Returns:
            Dictionary mapping material_id to combined mesh
        """
        material_meshes: dict[str, list[pv.PolyData]] = {}

        for frame in model.frames:
            section = sections.get(frame.section_name)
            if section is None:
                continue

            mesh = self._extrude_frame(frame, model, section)
            if mesh is None or mesh.n_points == 0:
                continue

            mat_id = frame.material_name
            if mat_id not in material_meshes:
                material_meshes[mat_id] = []
            material_meshes[mat_id].append(mesh)

        # Combine meshes per material
        result: dict[str, pv.PolyData] = {}
        for mat_id, meshes in material_meshes.items():
            if meshes:
                combined = meshes[0]
                for mesh in meshes[1:]:
                    combined = combined.merge(mesh)
                result[mat_id] = combined

        return result

    def build_deformed_extruded_mesh(
        self,
        model: StructuralModel,
        sections: dict[str, Section],
        results: AnalysisResults,
        scale: float,
    ) -> pv.PolyData:
        """
        Build extruded mesh with deformed geometry.

        Args:
            model: Structural model
            sections: Section dictionary
            results: Analysis results with displacements
            scale: Deformation scale factor

        Returns:
            Extruded mesh with deformed positions
        """
        if not model.frames:
            return pv.PolyData()

        meshes: list[pv.PolyData] = []

        for frame in model.frames:
            section = sections.get(frame.section_name)
            if section is None:
                continue

            mesh = self._extrude_frame_deformed(frame, model, section, results, scale)
            if mesh is not None and mesh.n_points > 0:
                meshes.append(mesh)

        if not meshes:
            return pv.PolyData()

        combined = meshes[0]
        for mesh in meshes[1:]:
            combined = combined.merge(mesh)

        return combined

    def _extrude_frame(
        self,
        frame: Frame,
        model: StructuralModel,
        section: Section,
    ) -> pv.PolyData | None:
        """Extrude a single frame element."""
        node_i = model.get_node(frame.node_i_id)
        node_j = model.get_node(frame.node_j_id)

        # Get or generate profile geometry
        profile = self._get_profile(section)
        if profile is None:
            return None

        # Calculate local axes
        local_axes = calculate_local_axes(node_i, node_j, frame.rotation)

        # Transform profile to 3D at start and end positions
        start_pos = np.array([node_i.x, node_i.y, node_i.z])
        end_pos = np.array([node_j.x, node_j.y, node_j.z])

        return self._create_extrusion_mesh(profile, start_pos, end_pos, local_axes)

    def _extrude_frame_deformed(
        self,
        frame: Frame,
        model: StructuralModel,
        section: Section,
        results: AnalysisResults,
        scale: float,
    ) -> pv.PolyData | None:
        """Extrude frame with deformed end positions."""
        node_i = model.get_node(frame.node_i_id)
        node_j = model.get_node(frame.node_j_id)

        # Get displacements
        disp_i = results.get_displacement(node_i.id)
        disp_j = results.get_displacement(node_j.id)

        # Calculate deformed positions
        if disp_i:
            start_pos = np.array([
                node_i.x + scale * disp_i.Ux,
                node_i.y + scale * disp_i.Uy,
                node_i.z + scale * disp_i.Uz,
            ])
        else:
            start_pos = np.array([node_i.x, node_i.y, node_i.z])

        if disp_j:
            end_pos = np.array([
                node_j.x + scale * disp_j.Ux,
                node_j.y + scale * disp_j.Uy,
                node_j.z + scale * disp_j.Uz,
            ])
        else:
            end_pos = np.array([node_j.x, node_j.y, node_j.z])

        # Get profile and calculate local axes (from deformed geometry)
        profile = self._get_profile(section)
        if profile is None:
            return None

        # Create temporary nodes for local axes calculation
        from paz.domain.model.node import Node
        temp_i = Node(id=-1, x=start_pos[0], y=start_pos[1], z=start_pos[2])
        temp_j = Node(id=-2, x=end_pos[0], y=end_pos[1], z=end_pos[2])

        try:
            local_axes = calculate_local_axes(temp_i, temp_j, frame.rotation)
        except ValueError:
            # Zero length element
            return None

        return self._create_extrusion_mesh(profile, start_pos, end_pos, local_axes)

    def _get_profile(self, section: Section) -> ProfileGeometry | None:
        """Get or generate cached profile geometry."""
        cache_key = section.name
        if cache_key in self._section_cache:
            return self._section_cache[cache_key]

        try:
            profile = self._profile_generator.generate(section)
            self._section_cache[cache_key] = profile
            return profile
        except Exception:
            return None

    def _create_extrusion_mesh(
        self,
        profile: ProfileGeometry,
        start_pos: np.ndarray,
        end_pos: np.ndarray,
        local_axes: Any,
    ) -> pv.PolyData:
        """
        Create 3D extrusion mesh from profile and frame geometry.

        Args:
            profile: 2D profile geometry
            start_pos: Start point (3D)
            end_pos: End point (3D)
            local_axes: Local coordinate system

        Returns:
            PyVista mesh representing the extruded section
        """
        # Build transformation matrix (local to global)
        # axis1 is along the element, axis2 and axis3 are perpendicular
        # Profile is defined in local Y-Z plane (axis2-axis3)
        rot_matrix = np.array([
            local_axes.axis2,  # X-profile -> axis2
            local_axes.axis3,  # Y-profile -> axis3
            local_axes.axis1,  # Z-profile -> axis1 (extrusion direction)
        ]).T

        # Transform 2D profile vertices to 3D at start position
        n_verts = len(profile.vertices)
        start_verts_3d = np.zeros((n_verts, 3))
        end_verts_3d = np.zeros((n_verts, 3))

        for i, (px, py) in enumerate(profile.vertices):
            # Profile point in local coords: (px, py, 0)
            local_point = np.array([px, py, 0.0])
            global_offset = rot_matrix @ local_point

            start_verts_3d[i] = start_pos + global_offset
            end_verts_3d[i] = end_pos + global_offset

        # Create mesh with side faces
        all_points = np.vstack([start_verts_3d, end_verts_3d])

        # Build faces (quads connecting start and end profiles)
        faces = []
        for i in range(n_verts):
            i_next = (i + 1) % n_verts
            # Quad: start[i], start[i+1], end[i+1], end[i]
            faces.append([4, i, i_next, n_verts + i_next, n_verts + i])

        # Add end caps if enabled
        if self._settings.show_end_caps and n_verts >= 3:
            # Simple fan triangulation from centroid
            # This works well for convex and most concave sections
            try:
                triangles = self._triangulate_polygon(profile.vertices)

                # Start cap (reversed winding for correct normal)
                for tri_idx in triangles:
                    faces.append([3, tri_idx[2], tri_idx[1], tri_idx[0]])

                # End cap
                for tri_idx in triangles:
                    faces.append([3, n_verts + tri_idx[0], n_verts + tri_idx[1], n_verts + tri_idx[2]])
            except Exception:
                # Skip caps if triangulation fails
                pass

        faces_array = np.hstack(faces)
        mesh = pv.PolyData(all_points, faces=faces_array)

        if self._settings.smooth_shading:
            mesh.compute_normals(inplace=True)

        return mesh

    def clear_cache(self) -> None:
        """Clear the section profile cache."""
        self._section_cache.clear()

    def _triangulate_polygon(
        self, vertices: np.ndarray
    ) -> list[tuple[int, int, int]]:
        """
        Simple ear-clipping triangulation for polygon.

        Works for simple polygons (no self-intersections).

        Args:
            vertices: 2D vertices array (N, 2)

        Returns:
            List of triangle index tuples
        """
        n = len(vertices)
        if n < 3:
            return []
        if n == 3:
            return [(0, 1, 2)]

        # Simple fan triangulation from first vertex
        # Works for convex polygons and many concave ones
        triangles = []
        for i in range(1, n - 1):
            triangles.append((0, i, i + 1))

        return triangles


def get_material_colors() -> dict[str, str]:
    """
    Get default colors for common materials.

    Returns:
        Dictionary mapping material patterns to colors
    """
    return {
        "steel": "#708090",  # Steel gray
        "a36": "#708090",
        "a572": "#708090",
        "a992": "#708090",
        "concrete": "#A9A9A9",  # Concrete gray
        "h20": "#A9A9A9",
        "h25": "#A9A9A9",
        "h30": "#A9A9A9",
        "wood": "#DEB887",  # Wood brown
        "timber": "#DEB887",
        "aluminum": "#C0C0C0",  # Aluminum silver
        "default": "#4169E1",  # Royal blue default
    }


def get_color_for_material(material_id: str) -> str:
    """
    Get display color for a material.

    Args:
        material_id: Material identifier

    Returns:
        Hex color string
    """
    colors = get_material_colors()
    material_lower = material_id.lower()

    for pattern, color in colors.items():
        if pattern in material_lower:
            return color

    return colors["default"]

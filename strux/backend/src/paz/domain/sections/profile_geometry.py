"""
Profile geometry generation for section cross-sections.

Generates 2D vertices for different section types that can be used
for 3D extrusion visualization.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from paz.domain.sections.section import Section


@dataclass
class ProfileGeometry:
    """
    2D profile geometry for a structural section.

    Attributes:
        vertices: List of (x, y) coordinates forming the outer boundary
        holes: List of vertex lists for interior holes (for hollow sections)
        centroid: (x, y) coordinates of the centroid
    """

    vertices: np.ndarray  # Shape (N, 2)
    holes: list[np.ndarray]  # List of shape (M, 2) arrays
    centroid: tuple[float, float]

    @property
    def n_vertices(self) -> int:
        """Number of outer boundary vertices."""
        return len(self.vertices)

    @property
    def has_holes(self) -> bool:
        """Whether the section has interior holes."""
        return len(self.holes) > 0


class ProfileGenerator:
    """
    Generates 2D profile geometries for different section types.

    Coordinates are in meters, centered at the centroid.
    """

    def __init__(self, circle_segments: int = 32) -> None:
        """
        Initialize generator.

        Args:
            circle_segments: Number of segments for circular sections
        """
        self._circle_segments = max(8, circle_segments)

    def generate(self, section: Section) -> ProfileGeometry:
        """
        Generate profile geometry for a section.

        Args:
            section: Section with geometric dimensions

        Returns:
            ProfileGeometry with vertices and holes
        """
        from paz.domain.sections.section import SectionShape

        shape = section.shape

        if shape == SectionShape.W:
            return self._generate_i_section(section)
        if shape in (SectionShape.HSS_RECT,):
            return self._generate_rectangular_hollow(section)
        if shape in (SectionShape.HSS_ROUND, SectionShape.PIPE):
            return self._generate_circular_hollow(section)
        if shape == SectionShape.L:
            return self._generate_angle(section)
        if shape == SectionShape.C:
            return self._generate_channel(section)
        if shape in (SectionShape.WT, SectionShape.MT, SectionShape.ST):
            return self._generate_t_section(section)
        if shape == SectionShape.CUSTOM:
            # Try to infer from dimensions
            return self._generate_from_dimensions(section)

        # Default: rectangular solid based on d and bf
        return self._generate_rectangular_solid(section)

    def _generate_i_section(self, section: Section) -> ProfileGeometry:
        """Generate I/W section profile (double-T)."""
        d = section.d or 0.3  # Total depth
        bf = section.bf or 0.15  # Flange width
        tf = section.tf or 0.01  # Flange thickness
        tw = section.tw or 0.006  # Web thickness

        # Half dimensions
        hd = d / 2
        hbf = bf / 2
        htw = tw / 2

        # I-section vertices (clockwise from top-left)
        # Centered at centroid (which is at geometric center for symmetric I)
        vertices = np.array([
            # Top flange (left to right)
            [-hbf, hd],
            [hbf, hd],
            # Top flange to web transition (right side)
            [hbf, hd - tf],
            [htw, hd - tf],
            # Web right side
            [htw, -hd + tf],
            # Bottom flange transition (right side)
            [hbf, -hd + tf],
            [hbf, -hd],
            # Bottom flange (right to left)
            [-hbf, -hd],
            # Bottom flange to web transition (left side)
            [-hbf, -hd + tf],
            [-htw, -hd + tf],
            # Web left side
            [-htw, hd - tf],
            # Top flange transition (left side)
            [-hbf, hd - tf],
        ], dtype=np.float64)

        return ProfileGeometry(
            vertices=vertices,
            holes=[],
            centroid=(0.0, 0.0),
        )

    def _generate_rectangular_hollow(self, section: Section) -> ProfileGeometry:
        """Generate rectangular hollow section (box/tube)."""
        # Use bf for width, d for height
        B = section.bf or section.d or 0.2
        H = section.d or 0.2
        t = section.t or section.tw or 0.01

        hB = B / 2
        hH = H / 2

        # Outer rectangle
        outer = np.array([
            [-hB, -hH],
            [hB, -hH],
            [hB, hH],
            [-hB, hH],
        ], dtype=np.float64)

        # Inner rectangle (hole)
        inner_hB = hB - t
        inner_hH = hH - t

        if inner_hB > 0 and inner_hH > 0:
            inner = np.array([
                [-inner_hB, -inner_hH],
                [inner_hB, -inner_hH],
                [inner_hB, inner_hH],
                [-inner_hB, inner_hH],
            ], dtype=np.float64)
            holes = [inner]
        else:
            holes = []

        return ProfileGeometry(
            vertices=outer,
            holes=holes,
            centroid=(0.0, 0.0),
        )

    def _generate_circular_hollow(self, section: Section) -> ProfileGeometry:
        """Generate circular hollow section (pipe/HSS round)."""
        D = section.OD or section.d or 0.2
        t = section.t or 0.01

        R_outer = D / 2
        R_inner = R_outer - t

        # Generate circle vertices
        angles = np.linspace(0, 2 * math.pi, self._circle_segments, endpoint=False)

        outer = np.column_stack([
            R_outer * np.cos(angles),
            R_outer * np.sin(angles),
        ])

        if R_inner > 0:
            inner = np.column_stack([
                R_inner * np.cos(angles),
                R_inner * np.sin(angles),
            ])
            holes = [inner]
        else:
            holes = []

        return ProfileGeometry(
            vertices=outer,
            holes=holes,
            centroid=(0.0, 0.0),
        )

    def _generate_angle(self, section: Section) -> ProfileGeometry:
        """Generate L-angle section."""
        # For angles, d is vertical leg, bf is horizontal leg
        L1 = section.d or 0.1  # Vertical leg
        L2 = section.bf or 0.1  # Horizontal leg
        t = section.t or section.tw or 0.01

        # Calculate centroid for L-shape
        A1 = L1 * t  # Vertical leg area
        A2 = (L2 - t) * t  # Horizontal leg area (minus overlap)
        A_total = A1 + A2

        # Centroid calculation
        y1 = L1 / 2  # Vertical leg centroid y
        y2 = t / 2  # Horizontal leg centroid y
        x1 = t / 2  # Vertical leg centroid x
        x2 = t + (L2 - t) / 2  # Horizontal leg centroid x

        cx = (A1 * x1 + A2 * x2) / A_total
        cy = (A1 * y1 + A2 * y2) / A_total

        # Vertices relative to corner (0,0), then shift by centroid
        vertices = np.array([
            [0, 0],
            [L2, 0],
            [L2, t],
            [t, t],
            [t, L1],
            [0, L1],
        ], dtype=np.float64)

        # Center at centroid
        vertices[:, 0] -= cx
        vertices[:, 1] -= cy

        return ProfileGeometry(
            vertices=vertices,
            holes=[],
            centroid=(0.0, 0.0),
        )

    def _generate_channel(self, section: Section) -> ProfileGeometry:
        """Generate C-channel section."""
        d = section.d or 0.2  # Depth
        bf = section.bf or 0.08  # Flange width
        tf = section.tf or 0.01  # Flange thickness
        tw = section.tw or 0.006  # Web thickness

        # C-channel is NOT symmetric about y-axis
        # Calculate centroid x position
        A_web = (d - 2 * tf) * tw
        A_flange = bf * tf
        A_total = A_web + 2 * A_flange

        x_web = tw / 2
        x_flange = bf / 2

        cx = (A_web * x_web + 2 * A_flange * x_flange) / A_total
        cy = 0.0  # Symmetric about x-axis

        hd = d / 2

        # Vertices (channel opening to the right)
        vertices = np.array([
            # Start at bottom-left
            [0, -hd],
            [bf, -hd],
            [bf, -hd + tf],
            [tw, -hd + tf],
            [tw, hd - tf],
            [bf, hd - tf],
            [bf, hd],
            [0, hd],
        ], dtype=np.float64)

        # Center at centroid
        vertices[:, 0] -= cx

        return ProfileGeometry(
            vertices=vertices,
            holes=[],
            centroid=(0.0, 0.0),
        )

    def _generate_t_section(self, section: Section) -> ProfileGeometry:
        """Generate T-section (WT, MT, ST)."""
        d = section.d or 0.15  # Total depth
        bf = section.bf or 0.15  # Flange width
        tf = section.tf or 0.01  # Flange thickness
        tw = section.tw or 0.008  # Stem thickness

        # T-section is NOT symmetric about x-axis
        # Flange at top, stem going down
        stem_height = d - tf

        # Calculate centroid y
        A_flange = bf * tf
        A_stem = stem_height * tw
        A_total = A_flange + A_stem

        y_flange = d - tf / 2
        y_stem = stem_height / 2

        cy = (A_flange * y_flange + A_stem * y_stem) / A_total
        cx = 0.0  # Symmetric about y-axis

        hbf = bf / 2
        htw = tw / 2

        # Vertices
        vertices = np.array([
            # Start at stem bottom-left
            [-htw, 0],
            [htw, 0],
            [htw, stem_height],
            [hbf, stem_height],
            [hbf, d],
            [-hbf, d],
            [-hbf, stem_height],
            [-htw, stem_height],
        ], dtype=np.float64)

        # Center at centroid
        vertices[:, 1] -= cy

        return ProfileGeometry(
            vertices=vertices,
            holes=[],
            centroid=(0.0, 0.0),
        )

    def _generate_rectangular_solid(self, section: Section) -> ProfileGeometry:
        """Generate solid rectangular section."""
        B = section.bf or section.d or 0.2
        H = section.d or 0.2

        hB = B / 2
        hH = H / 2

        vertices = np.array([
            [-hB, -hH],
            [hB, -hH],
            [hB, hH],
            [-hB, hH],
        ], dtype=np.float64)

        return ProfileGeometry(
            vertices=vertices,
            holes=[],
            centroid=(0.0, 0.0),
        )

    def _generate_circular_solid(self, D: float) -> ProfileGeometry:
        """Generate solid circular section."""
        R = D / 2
        angles = np.linspace(0, 2 * math.pi, self._circle_segments, endpoint=False)

        vertices = np.column_stack([
            R * np.cos(angles),
            R * np.sin(angles),
        ])

        return ProfileGeometry(
            vertices=vertices,
            holes=[],
            centroid=(0.0, 0.0),
        )

    def _generate_from_dimensions(self, section: Section) -> ProfileGeometry:
        """Infer section type from available dimensions."""
        # If we have OD, it's circular
        if section.OD and section.OD > 0:
            if section.t and section.t > 0:
                return self._generate_circular_hollow(section)
            return self._generate_circular_solid(section.OD)

        # If we have d, bf, tf, tw - it's likely I-section
        if all([section.d, section.bf, section.tf, section.tw]):
            return self._generate_i_section(section)

        # If we have d, bf, t - rectangular hollow
        if section.d and section.bf and section.t:
            return self._generate_rectangular_hollow(section)

        # Default to rectangular solid
        return self._generate_rectangular_solid(section)

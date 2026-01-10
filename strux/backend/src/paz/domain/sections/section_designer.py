"""
Section Designer for custom and composite sections.

Provides tools to create custom cross-sections by:
- Defining arbitrary shapes with polygons
- Combining standard sections (back-to-back, built-up)
- Calculating geometric properties automatically
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import pi, sqrt
from typing import TYPE_CHECKING
from uuid import uuid4

from paz.core.exceptions import ValidationError
from paz.domain.sections.section import Section, SectionShape, SectionStandard


if TYPE_CHECKING:
    pass


class RegionShape(str, Enum):
    """Basic shapes for section regions."""

    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    POLYGON = "polygon"
    I_SHAPE = "i_shape"
    CHANNEL = "channel"
    ANGLE = "angle"


@dataclass
class SectionRegion:
    """
    A region within a composite section.

    Each region represents a solid area with material properties.
    Regions can be combined to form complex sections.

    Attributes:
        shape: Basic shape type
        cx: Centroid x-coordinate relative to section origin (m)
        cy: Centroid y-coordinate relative to section origin (m)
        rotation: Rotation angle in radians
        vertices: For polygon shapes, list of (x, y) vertices (m)

        For RECTANGLE:
            width: Width in x-direction (m)
            height: Height in y-direction (m)

        For CIRCLE:
            radius: Outer radius (m)
            inner_radius: Inner radius for hollow (m), 0 for solid

        For I_SHAPE:
            d: Total depth (m)
            bf: Flange width (m)
            tf: Flange thickness (m)
            tw: Web thickness (m)
    """

    shape: RegionShape
    cx: float = 0.0
    cy: float = 0.0
    rotation: float = 0.0

    # Rectangle parameters
    width: float | None = None
    height: float | None = None

    # Circle parameters
    radius: float | None = None
    inner_radius: float = 0.0

    # I-shape parameters
    d: float | None = None
    bf: float | None = None
    tf: float | None = None
    tw: float | None = None

    # Polygon vertices (for arbitrary shapes)
    vertices: list[tuple[float, float]] = field(default_factory=list)

    # Material factor (for composite sections with different materials)
    # E_material / E_reference
    modular_ratio: float = 1.0

    def calculate_properties(self) -> dict[str, float]:
        """
        Calculate geometric properties for this region.

        Returns:
            Dictionary with A, Ix, Iy, J (all in SI units)
        """
        if self.shape == RegionShape.RECTANGLE:
            return self._calc_rectangle()
        elif self.shape == RegionShape.CIRCLE:
            return self._calc_circle()
        elif self.shape == RegionShape.I_SHAPE:
            return self._calc_i_shape()
        elif self.shape == RegionShape.POLYGON:
            return self._calc_polygon()
        else:
            raise ValidationError(f"Unsupported shape: {self.shape}", field="shape")

    def _calc_rectangle(self) -> dict[str, float]:
        """Calculate properties for rectangle."""
        if self.width is None or self.height is None:
            raise ValidationError("Rectangle requires width and height", field="width")

        b, h = self.width, self.height
        A = b * h
        Ix_local = (b * h**3) / 12
        Iy_local = (h * b**3) / 12
        J = (b * h * (b**2 + h**2)) / 12  # Approximate for thin sections

        return {
            "A": A * self.modular_ratio,
            "Ix_local": Ix_local * self.modular_ratio,
            "Iy_local": Iy_local * self.modular_ratio,
            "J": J * self.modular_ratio,
        }

    def _calc_circle(self) -> dict[str, float]:
        """Calculate properties for circle (solid or hollow)."""
        if self.radius is None:
            raise ValidationError("Circle requires radius", field="radius")

        r_o = self.radius
        r_i = self.inner_radius

        A = pi * (r_o**2 - r_i**2)
        I = (pi / 4) * (r_o**4 - r_i**4)
        J = (pi / 2) * (r_o**4 - r_i**4)  # Polar moment

        return {
            "A": A * self.modular_ratio,
            "Ix_local": I * self.modular_ratio,
            "Iy_local": I * self.modular_ratio,
            "J": J * self.modular_ratio,
        }

    def _calc_i_shape(self) -> dict[str, float]:
        """Calculate properties for I-shape."""
        if any(v is None for v in [self.d, self.bf, self.tf, self.tw]):
            raise ValidationError("I-shape requires d, bf, tf, tw", field="d")

        d, bf, tf, tw = self.d, self.bf, self.tf, self.tw  # type: ignore

        # Area: two flanges + web
        A_flange = bf * tf
        h_web = d - 2 * tf
        A_web = h_web * tw
        A = 2 * A_flange + A_web

        # Ix: sum of flanges (parallel axis) + web
        Ix_flange = (bf * tf**3) / 12 + A_flange * ((d - tf) / 2) ** 2
        Ix_web = (tw * h_web**3) / 12
        Ix = 2 * Ix_flange + Ix_web

        # Iy: flanges + web about y-axis
        Iy_flange = (tf * bf**3) / 12
        Iy_web = (h_web * tw**3) / 12
        Iy = 2 * Iy_flange + Iy_web

        # J: approximate for open section
        J = (2 * bf * tf**3 + h_web * tw**3) / 3

        return {
            "A": A * self.modular_ratio,
            "Ix_local": Ix * self.modular_ratio,
            "Iy_local": Iy * self.modular_ratio,
            "J": J * self.modular_ratio,
        }

    def _calc_polygon(self) -> dict[str, float]:
        """Calculate properties for arbitrary polygon using Green's theorem."""
        if len(self.vertices) < 3:
            raise ValidationError("Polygon requires at least 3 vertices", field="vertices")

        n = len(self.vertices)
        A = 0.0
        Cx = 0.0
        Cy = 0.0

        # Calculate area and centroid
        for i in range(n):
            x0, y0 = self.vertices[i]
            x1, y1 = self.vertices[(i + 1) % n]
            cross = x0 * y1 - x1 * y0
            A += cross
            Cx += (x0 + x1) * cross
            Cy += (y0 + y1) * cross

        A = abs(A) / 2
        if A < 1e-12:
            raise ValidationError("Polygon has zero area", field="vertices")

        Cx = Cx / (6 * A) if A > 0 else 0
        Cy = Cy / (6 * A) if A > 0 else 0

        # Calculate moments of inertia about centroid
        Ix = 0.0
        Iy = 0.0

        for i in range(n):
            x0, y0 = self.vertices[i]
            x1, y1 = self.vertices[(i + 1) % n]
            cross = x0 * y1 - x1 * y0
            Ix += cross * (y0**2 + y0 * y1 + y1**2)
            Iy += cross * (x0**2 + x0 * x1 + x1**2)

        Ix = abs(Ix) / 12
        Iy = abs(Iy) / 12

        # Shift to centroid
        Ix -= A * Cy**2
        Iy -= A * Cx**2

        # J approximation (use bounding box)
        xs = [v[0] for v in self.vertices]
        ys = [v[1] for v in self.vertices]
        b = max(xs) - min(xs)
        h = max(ys) - min(ys)
        J = (b * h * (b**2 + h**2)) / 12

        return {
            "A": abs(A) * self.modular_ratio,
            "Ix_local": abs(Ix) * self.modular_ratio,
            "Iy_local": abs(Iy) * self.modular_ratio,
            "J": abs(J) * self.modular_ratio,
        }


class SectionDesigner:
    """
    Designer for creating custom and composite sections.

    Features:
    - Create sections from basic shapes (rectangle, circle, I-shape)
    - Combine multiple regions into composite sections
    - Create back-to-back and built-up configurations
    - Calculate combined geometric properties

    Example:
        designer = SectionDesigner("CustomBeam")
        designer.add_rectangle(width=0.3, height=0.5)  # Main section
        designer.add_rectangle(width=0.3, height=0.1, cy=0.3)  # Top plate
        section = designer.build()
    """

    def __init__(self, name: str) -> None:
        """
        Initialize the section designer.

        Args:
            name: Name for the resulting section
        """
        self._name = name
        self._regions: list[SectionRegion] = []
        self._description = ""

    @property
    def name(self) -> str:
        """Get section name."""
        return self._name

    @property
    def regions(self) -> list[SectionRegion]:
        """Get list of regions."""
        return self._regions.copy()

    def set_description(self, description: str) -> "SectionDesigner":
        """Set section description."""
        self._description = description
        return self

    def add_region(self, region: SectionRegion) -> "SectionDesigner":
        """
        Add a region to the section.

        Args:
            region: SectionRegion to add

        Returns:
            Self for chaining
        """
        self._regions.append(region)
        return self

    def add_rectangle(
        self,
        width: float,
        height: float,
        cx: float = 0.0,
        cy: float = 0.0,
        rotation: float = 0.0,
        modular_ratio: float = 1.0,
    ) -> "SectionDesigner":
        """
        Add a rectangular region.

        Args:
            width: Width in x-direction (m)
            height: Height in y-direction (m)
            cx: Centroid x-coordinate (m)
            cy: Centroid y-coordinate (m)
            rotation: Rotation angle (radians)
            modular_ratio: E_material / E_reference

        Returns:
            Self for chaining
        """
        region = SectionRegion(
            shape=RegionShape.RECTANGLE,
            width=width,
            height=height,
            cx=cx,
            cy=cy,
            rotation=rotation,
            modular_ratio=modular_ratio,
        )
        return self.add_region(region)

    def add_circle(
        self,
        radius: float,
        cx: float = 0.0,
        cy: float = 0.0,
        inner_radius: float = 0.0,
        modular_ratio: float = 1.0,
    ) -> "SectionDesigner":
        """
        Add a circular region (solid or hollow).

        Args:
            radius: Outer radius (m)
            cx: Centroid x-coordinate (m)
            cy: Centroid y-coordinate (m)
            inner_radius: Inner radius for hollow section (m)
            modular_ratio: E_material / E_reference

        Returns:
            Self for chaining
        """
        region = SectionRegion(
            shape=RegionShape.CIRCLE,
            radius=radius,
            inner_radius=inner_radius,
            cx=cx,
            cy=cy,
            modular_ratio=modular_ratio,
        )
        return self.add_region(region)

    def add_i_shape(
        self,
        d: float,
        bf: float,
        tf: float,
        tw: float,
        cx: float = 0.0,
        cy: float = 0.0,
        modular_ratio: float = 1.0,
    ) -> "SectionDesigner":
        """
        Add an I-shaped region.

        Args:
            d: Total depth (m)
            bf: Flange width (m)
            tf: Flange thickness (m)
            tw: Web thickness (m)
            cx: Centroid x-coordinate (m)
            cy: Centroid y-coordinate (m)
            modular_ratio: E_material / E_reference

        Returns:
            Self for chaining
        """
        region = SectionRegion(
            shape=RegionShape.I_SHAPE,
            d=d,
            bf=bf,
            tf=tf,
            tw=tw,
            cx=cx,
            cy=cy,
            modular_ratio=modular_ratio,
        )
        return self.add_region(region)

    def add_polygon(
        self,
        vertices: list[tuple[float, float]],
        cx: float = 0.0,
        cy: float = 0.0,
        modular_ratio: float = 1.0,
    ) -> "SectionDesigner":
        """
        Add a polygonal region.

        Args:
            vertices: List of (x, y) coordinates (m)
            cx: Offset in x-direction (m)
            cy: Offset in y-direction (m)
            modular_ratio: E_material / E_reference

        Returns:
            Self for chaining
        """
        # Offset vertices
        offset_vertices = [(x + cx, y + cy) for x, y in vertices]

        region = SectionRegion(
            shape=RegionShape.POLYGON,
            vertices=offset_vertices,
            cx=cx,
            cy=cy,
            modular_ratio=modular_ratio,
        )
        return self.add_region(region)

    def build(self) -> Section:
        """
        Build the final Section from all regions.

        Calculates combined geometric properties using:
        - Summation for area and J
        - Parallel axis theorem for Ix and Iy

        Returns:
            Section object with calculated properties
        """
        if not self._regions:
            raise ValidationError("No regions defined", field="regions")

        # Calculate properties for each region
        region_props = [r.calculate_properties() for r in self._regions]

        # Combined area
        total_A = sum(p["A"] for p in region_props)

        # Combined centroid
        sum_Ax = sum(p["A"] * r.cx for p, r in zip(region_props, self._regions))
        sum_Ay = sum(p["A"] * r.cy for p, r in zip(region_props, self._regions))
        Cx = sum_Ax / total_A if total_A > 0 else 0
        Cy = sum_Ay / total_A if total_A > 0 else 0

        # Combined moments of inertia (parallel axis theorem)
        total_Ix = 0.0
        total_Iy = 0.0
        total_J = 0.0

        for props, region in zip(region_props, self._regions):
            A = props["A"]
            Ix_local = props["Ix_local"]
            Iy_local = props["Iy_local"]
            J = props["J"]

            # Distance from region centroid to combined centroid
            dx = region.cx - Cx
            dy = region.cy - Cy

            # Parallel axis theorem: I_total = I_local + A * d^2
            total_Ix += Ix_local + A * dy**2
            total_Iy += Iy_local + A * dx**2
            total_J += J

        # Calculate derived properties
        rx = sqrt(total_Ix / total_A) if total_A > 0 else 0
        ry = sqrt(total_Iy / total_A) if total_A > 0 else 0

        # Approximate section moduli (assumes symmetric section)
        # Find bounding box
        d_max = self._estimate_depth()
        b_max = self._estimate_width()

        Sx = total_Ix / (d_max / 2) if d_max > 0 else None
        Sy = total_Iy / (b_max / 2) if b_max > 0 else None

        return Section(
            id=uuid4(),
            name=self._name,
            shape=SectionShape.CUSTOM,
            standard=SectionStandard.CUSTOM,
            A=total_A,
            Ix=total_Ix,
            Iy=total_Iy,
            Sx=Sx,
            Sy=Sy,
            rx=rx,
            ry=ry,
            J=total_J,
            d=d_max if d_max > 0 else None,
            bf=b_max if b_max > 0 else None,
            description=self._description,
            is_custom=True,
        )

    def _estimate_depth(self) -> float:
        """Estimate total depth from regions."""
        y_coords: list[float] = []

        for region in self._regions:
            if region.shape == RegionShape.RECTANGLE and region.height:
                y_coords.append(region.cy - region.height / 2)
                y_coords.append(region.cy + region.height / 2)
            elif region.shape == RegionShape.CIRCLE and region.radius:
                y_coords.append(region.cy - region.radius)
                y_coords.append(region.cy + region.radius)
            elif region.shape == RegionShape.I_SHAPE and region.d:
                y_coords.append(region.cy - region.d / 2)
                y_coords.append(region.cy + region.d / 2)
            elif region.shape == RegionShape.POLYGON and region.vertices:
                for _, y in region.vertices:
                    y_coords.append(y)

        if y_coords:
            return max(y_coords) - min(y_coords)
        return 0.0

    def _estimate_width(self) -> float:
        """Estimate total width from regions."""
        x_coords: list[float] = []

        for region in self._regions:
            if region.shape == RegionShape.RECTANGLE and region.width:
                x_coords.append(region.cx - region.width / 2)
                x_coords.append(region.cx + region.width / 2)
            elif region.shape == RegionShape.CIRCLE and region.radius:
                x_coords.append(region.cx - region.radius)
                x_coords.append(region.cx + region.radius)
            elif region.shape == RegionShape.I_SHAPE and region.bf:
                x_coords.append(region.cx - region.bf / 2)
                x_coords.append(region.cx + region.bf / 2)
            elif region.shape == RegionShape.POLYGON and region.vertices:
                for x, _ in region.vertices:
                    x_coords.append(x)

        if x_coords:
            return max(x_coords) - min(x_coords)
        return 0.0

    def clear(self) -> "SectionDesigner":
        """Clear all regions."""
        self._regions.clear()
        return self


# Convenience functions for common composite configurations

def create_double_angle(
    angle_section: Section,
    gap: float = 0.01,
    name: str | None = None,
) -> Section:
    """
    Create a double angle (back-to-back) section.

    Args:
        angle_section: Base angle section
        gap: Gap between angles (m)
        name: Name for resulting section (default: "2L-{base_name}")

    Returns:
        New Section with combined properties
    """
    if name is None:
        name = f"2L-{angle_section.name}"

    # Double the area
    A = 2 * angle_section.A

    # Ix doubles (parallel to each other)
    Ix = 2 * angle_section.Ix

    # Iy uses parallel axis theorem
    # Assume angle centroid offset from back is roughly bf/3
    if angle_section.bf:
        d_y = angle_section.bf / 3 + gap / 2
        Iy = 2 * (angle_section.Iy + angle_section.A * d_y**2)
    else:
        Iy = 2 * angle_section.Iy

    J = 2 * (angle_section.J or 0) if angle_section.J else None

    return Section(
        name=name,
        shape=SectionShape.DOUBLE_L,
        standard=SectionStandard.CUSTOM,
        A=A,
        Ix=Ix,
        Iy=Iy,
        J=J,
        rx=sqrt(Ix / A) if A > 0 else None,
        ry=sqrt(Iy / A) if A > 0 else None,
        description=f"Double angle from {angle_section.name}",
        is_custom=True,
    )


def create_built_up_section(
    base_section: Section,
    plate_width: float,
    plate_thickness: float,
    position: str = "top",
    name: str | None = None,
) -> Section:
    """
    Create a built-up section with cover plate.

    Args:
        base_section: Base section (typically W or I)
        plate_width: Width of cover plate (m)
        plate_thickness: Thickness of cover plate (m)
        position: "top", "bottom", or "both"
        name: Name for resulting section

    Returns:
        New Section with combined properties
    """
    if name is None:
        name = f"{base_section.name}-PL{plate_width*1000:.0f}x{plate_thickness*1000:.0f}"

    designer = SectionDesigner(name)

    # Add base section as I-shape
    if base_section.d and base_section.bf and base_section.tf and base_section.tw:
        designer.add_i_shape(
            d=base_section.d,
            bf=base_section.bf,
            tf=base_section.tf,
            tw=base_section.tw,
        )
    else:
        # Fallback: use a rectangle approximation
        raise ValidationError(
            "Base section must have d, bf, tf, tw defined",
            field="base_section",
        )

    # Add plates
    base_d = base_section.d

    if position in ("top", "both"):
        designer.add_rectangle(
            width=plate_width,
            height=plate_thickness,
            cy=base_d / 2 + plate_thickness / 2,
        )

    if position in ("bottom", "both"):
        designer.add_rectangle(
            width=plate_width,
            height=plate_thickness,
            cy=-(base_d / 2 + plate_thickness / 2),
        )

    section = designer.build()
    section.description = f"Built-up section: {base_section.name} + plates"

    return section

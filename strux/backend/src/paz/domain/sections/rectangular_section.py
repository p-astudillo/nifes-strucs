"""
Rectangular section parametric definitions.

Includes solid rectangles and hollow rectangular tubes (box sections).
"""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from paz.domain.sections.parametric import (
    ParametricSection,
    _validate_positive,
    _validate_thickness_ratio,
)
from paz.domain.sections.section import SectionShape


@dataclass
class RectangularSolid(ParametricSection):
    """
    Solid rectangular section.

    Dimensions:
        B: Width (m) - along y-axis
        H: Height (m) - along x-axis (strong axis)

    ```
         B
    |----------|
    |          |
    |          |  H
    |          |
    |----------|
    ```
    """

    B: float = 0.0  # Width (m)
    H: float = 0.0  # Height (m)
    name: str = "Rectangular Solid"
    id: UUID = field(default_factory=uuid4)
    description: str = ""

    def _validate_dimensions(self) -> None:
        """Validate rectangular solid dimensions."""
        _validate_positive(self.B, "B (width)")
        _validate_positive(self.H, "H (height)")

    def _get_shape(self) -> SectionShape:
        return SectionShape.CUSTOM

    def _get_dimensions_dict(self) -> dict[str, float]:
        return {
            "B": self.B,
            "H": self.H,
            "d": self.H,
            "bf": self.B,
        }

    def _calculate_A(self) -> float:
        """A = B * H"""
        return self.B * self.H

    def _calculate_Ix(self) -> float:
        """Ix = B * H³ / 12"""
        return self.B * self.H**3 / 12

    def _calculate_Iy(self) -> float:
        """Iy = H * B³ / 12"""
        return self.H * self.B**3 / 12

    def _calculate_J(self) -> float:
        """
        Torsional constant for solid rectangle (approximate).

        J ≈ k * a * b³ where a >= b
        k depends on aspect ratio, approximately 0.141 for square, up to 1/3 for thin strips
        """
        a = max(self.B, self.H)
        b = min(self.B, self.H)
        # Approximation: J = b³*a/3 * (1 - 0.63*b/a)
        if a == 0:
            return 0.0
        return b**3 * a / 3 * (1 - 0.63 * b / a)

    def _get_extreme_fiber_x(self) -> float:
        return self.H / 2

    def _get_extreme_fiber_y(self) -> float:
        return self.B / 2

    def _calculate_Zx(self) -> float:
        """Zx = B * H² / 4"""
        return self.B * self.H**2 / 4

    def _calculate_Zy(self) -> float:
        """Zy = H * B² / 4"""
        return self.H * self.B**2 / 4


@dataclass
class RectangularHollow(ParametricSection):
    """
    Hollow rectangular section (box/tube).

    Dimensions:
        B: Outer width (m) - along y-axis
        H: Outer height (m) - along x-axis (strong axis)
        t: Wall thickness (m) - uniform on all sides

    ```
         B
    |----------|
    |  |----| |
    |  |    | |  H
    |  |----| |
    |----------|
         t
    ```
    """

    B: float = 0.0  # Outer width (m)
    H: float = 0.0  # Outer height (m)
    t: float = 0.0  # Wall thickness (m)
    name: str = "Rectangular Hollow"
    id: UUID = field(default_factory=uuid4)
    description: str = ""

    def _validate_dimensions(self) -> None:
        """Validate hollow rectangular dimensions."""
        _validate_positive(self.B, "B (width)")
        _validate_positive(self.H, "H (height)")
        _validate_positive(self.t, "t (thickness)")
        _validate_thickness_ratio(self.t, min(self.B, self.H), "t")

    def _get_shape(self) -> SectionShape:
        return SectionShape.HSS_RECT

    def _get_dimensions_dict(self) -> dict[str, float]:
        return {
            "B": self.B,
            "H": self.H,
            "t": self.t,
            "d": self.H,
            "bf": self.B,
        }

    @property
    def Bi(self) -> float:
        """Inner width."""
        return self.B - 2 * self.t

    @property
    def Hi(self) -> float:
        """Inner height."""
        return self.H - 2 * self.t

    def _calculate_A(self) -> float:
        """A = B*H - Bi*Hi"""
        return self.B * self.H - self.Bi * self.Hi

    def _calculate_Ix(self) -> float:
        """Ix = (B*H³ - Bi*Hi³) / 12"""
        return (self.B * self.H**3 - self.Bi * self.Hi**3) / 12

    def _calculate_Iy(self) -> float:
        """Iy = (H*B³ - Hi*Bi³) / 12"""
        return (self.H * self.B**3 - self.Hi * self.Bi**3) / 12

    def _calculate_J(self) -> float:
        """
        Torsional constant for hollow rectangle.

        J = 2 * t * (B-t)² * (H-t)² / (B + H - 2t)
        """
        Bm = self.B - self.t  # Mean width
        Hm = self.H - self.t  # Mean height
        perimeter = 2 * (Bm + Hm)
        if perimeter == 0:
            return 0.0
        Am = Bm * Hm  # Mean enclosed area
        return 4 * Am**2 * self.t / perimeter

    def _get_extreme_fiber_x(self) -> float:
        return self.H / 2

    def _get_extreme_fiber_y(self) -> float:
        return self.B / 2

    def _calculate_Zx(self) -> float:
        """Zx = (B*H² - Bi*Hi²) / 4"""
        return (self.B * self.H**2 - self.Bi * self.Hi**2) / 4

    def _calculate_Zy(self) -> float:
        """Zy = (H*B² - Hi*Bi²) / 4"""
        return (self.H * self.B**2 - self.Hi * self.Bi**2) / 4

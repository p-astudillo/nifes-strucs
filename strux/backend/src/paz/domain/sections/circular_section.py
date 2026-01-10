"""
Circular section parametric definitions.

Includes solid circles and hollow circular tubes (pipes).
"""

from dataclasses import dataclass, field
from math import pi
from uuid import UUID, uuid4

from paz.domain.sections.parametric import (
    ParametricSection,
    _validate_positive,
    _validate_thickness_ratio,
)
from paz.domain.sections.section import SectionShape


@dataclass
class CircularSolid(ParametricSection):
    """
    Solid circular section.

    Dimensions:
        D: Diameter (m)

    ```
        ____
      /      \\
     |   D    |
      \\____/
    ```
    """

    D: float = 0.0  # Diameter (m)
    name: str = "Circular Solid"
    id: UUID = field(default_factory=uuid4)
    description: str = ""

    def _validate_dimensions(self) -> None:
        """Validate circular solid dimensions."""
        _validate_positive(self.D, "D (diameter)")

    def _get_shape(self) -> SectionShape:
        return SectionShape.CUSTOM

    def _get_dimensions_dict(self) -> dict[str, float]:
        return {
            "D": self.D,
            "OD": self.D,
            "d": self.D,
        }

    @property
    def r(self) -> float:
        """Radius."""
        return self.D / 2

    def _calculate_A(self) -> float:
        """A = π * D² / 4"""
        return pi * self.D**2 / 4

    def _calculate_Ix(self) -> float:
        """Ix = π * D⁴ / 64"""
        return pi * self.D**4 / 64

    def _calculate_Iy(self) -> float:
        """Iy = Ix for circular section."""
        return self._calculate_Ix()

    def _calculate_J(self) -> float:
        """J = π * D⁴ / 32 (polar moment of inertia)."""
        return pi * self.D**4 / 32

    def _get_extreme_fiber_x(self) -> float:
        return self.D / 2

    def _get_extreme_fiber_y(self) -> float:
        return self.D / 2

    def _calculate_Zx(self) -> float:
        """Zx = D³ / 6"""
        return self.D**3 / 6

    def _calculate_Zy(self) -> float:
        """Zy = Zx for circular section."""
        return self._calculate_Zx()


@dataclass
class CircularHollow(ParametricSection):
    """
    Hollow circular section (pipe/tube).

    Dimensions:
        D: Outer diameter (m)
        t: Wall thickness (m)

    ```
        ____
      / __ \\
     | |  | |  D
      \\--/
        t
    ```
    """

    D: float = 0.0  # Outer diameter (m)
    t: float = 0.0  # Wall thickness (m)
    name: str = "Circular Hollow"
    id: UUID = field(default_factory=uuid4)
    description: str = ""

    def _validate_dimensions(self) -> None:
        """Validate hollow circular dimensions."""
        _validate_positive(self.D, "D (diameter)")
        _validate_positive(self.t, "t (thickness)")
        _validate_thickness_ratio(self.t, self.D, "t")

    def _get_shape(self) -> SectionShape:
        return SectionShape.PIPE

    def _get_dimensions_dict(self) -> dict[str, float]:
        return {
            "D": self.D,
            "OD": self.D,
            "t": self.t,
            "d": self.D,
        }

    @property
    def Di(self) -> float:
        """Inner diameter."""
        return self.D - 2 * self.t

    @property
    def ro(self) -> float:
        """Outer radius."""
        return self.D / 2

    @property
    def ri(self) -> float:
        """Inner radius."""
        return self.Di / 2

    def _calculate_A(self) -> float:
        """A = π * (D² - Di²) / 4"""
        return pi * (self.D**2 - self.Di**2) / 4

    def _calculate_Ix(self) -> float:
        """Ix = π * (D⁴ - Di⁴) / 64"""
        return pi * (self.D**4 - self.Di**4) / 64

    def _calculate_Iy(self) -> float:
        """Iy = Ix for circular section."""
        return self._calculate_Ix()

    def _calculate_J(self) -> float:
        """J = π * (D⁴ - Di⁴) / 32"""
        return pi * (self.D**4 - self.Di**4) / 32

    def _get_extreme_fiber_x(self) -> float:
        return self.D / 2

    def _get_extreme_fiber_y(self) -> float:
        return self.D / 2

    def _calculate_Zx(self) -> float:
        """Zx = (D³ - Di³) / 6"""
        return (self.D**3 - self.Di**3) / 6

    def _calculate_Zy(self) -> float:
        """Zy = Zx for circular section."""
        return self._calculate_Zx()


# Alias for common naming convention
Pipe = CircularHollow

"""
Angle section (L-shape) parametric definition.

Creates single angle sections with automatic property calculation.
"""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from paz.domain.sections.parametric import (
    ParametricSection,
    _validate_positive,
)
from paz.domain.sections.section import SectionShape


@dataclass
class Angle(ParametricSection):
    """
    Single angle (L-shape) section.

    Dimensions:
        L1: Length of vertical leg (m) - along y direction
        L2: Length of horizontal leg (m) - along x direction
        t: Thickness (m) - uniform for both legs

    For equal angles, L1 = L2.

    ```
    |
    |  L1
    |
    |______
       L2
    (thickness t)
    ```

    Note: Properties are calculated about the centroidal axes,
    which are NOT at the corner for angles.
    """

    L1: float = 0.0  # Vertical leg length (m)
    L2: float = 0.0  # Horizontal leg length (m)
    t: float = 0.0  # Thickness (m)
    name: str = "Angle"
    id: UUID = field(default_factory=uuid4)
    description: str = ""

    def _validate_dimensions(self) -> None:
        """Validate angle dimensions."""
        _validate_positive(self.L1, "L1 (vertical leg)")
        _validate_positive(self.L2, "L2 (horizontal leg)")
        _validate_positive(self.t, "t (thickness)")

        # Thickness should be less than leg lengths
        if self.t >= self.L1:
            raise ValueError(
                f"Thickness ({self.t}) must be less than L1 ({self.L1})"
            )
        if self.t >= self.L2:
            raise ValueError(
                f"Thickness ({self.t}) must be less than L2 ({self.L2})"
            )

    def _get_shape(self) -> SectionShape:
        return SectionShape.L

    def _get_dimensions_dict(self) -> dict[str, float]:
        return {
            "L1": self.L1,
            "L2": self.L2,
            "t": self.t,
            "d": self.L1,
            "bf": self.L2,
        }

    @property
    def is_equal(self) -> bool:
        """Check if this is an equal-leg angle."""
        return abs(self.L1 - self.L2) < 1e-9

    def _calculate_A(self) -> float:
        """
        Calculate area.

        A = t * (L1 + L2 - t)
        """
        return self.t * (self.L1 + self.L2 - self.t)

    @property
    def _centroid_x(self) -> float:
        """X-coordinate of centroid from bottom-left corner."""
        # Area of horizontal leg
        A1 = self.L2 * self.t
        x1 = self.L2 / 2

        # Area of vertical leg (excluding overlap)
        A2 = (self.L1 - self.t) * self.t
        x2 = self.t / 2

        return (A1 * x1 + A2 * x2) / (A1 + A2)

    @property
    def _centroid_y(self) -> float:
        """Y-coordinate of centroid from bottom-left corner."""
        # Area of horizontal leg
        A1 = self.L2 * self.t
        y1 = self.t / 2

        # Area of vertical leg (excluding overlap)
        A2 = (self.L1 - self.t) * self.t
        y2 = self.t + (self.L1 - self.t) / 2

        return (A1 * y1 + A2 * y2) / (A1 + A2)

    def _calculate_Ix(self) -> float:
        """
        Calculate moment of inertia about x-axis (through centroid).

        Uses parallel axis theorem for composite section.
        """
        yc = self._centroid_y

        # Horizontal leg
        A1 = self.L2 * self.t
        y1 = self.t / 2
        Ix1 = self.L2 * self.t**3 / 12 + A1 * (yc - y1) ** 2

        # Vertical leg (excluding overlap)
        h2 = self.L1 - self.t
        A2 = h2 * self.t
        y2 = self.t + h2 / 2
        Ix2 = self.t * h2**3 / 12 + A2 * (yc - y2) ** 2

        return Ix1 + Ix2

    def _calculate_Iy(self) -> float:
        """
        Calculate moment of inertia about y-axis (through centroid).

        Uses parallel axis theorem for composite section.
        """
        xc = self._centroid_x

        # Horizontal leg
        A1 = self.L2 * self.t
        x1 = self.L2 / 2
        Iy1 = self.t * self.L2**3 / 12 + A1 * (xc - x1) ** 2

        # Vertical leg (excluding overlap)
        h2 = self.L1 - self.t
        A2 = h2 * self.t
        x2 = self.t / 2
        Iy2 = h2 * self.t**3 / 12 + A2 * (xc - x2) ** 2

        return Iy1 + Iy2

    def _calculate_J(self) -> float:
        """
        Calculate torsional constant (approximate for thin-walled open section).

        J ≈ (1/3) * (L1 + L2 - t) * t³
        """
        return (self.L1 + self.L2 - self.t) * self.t**3 / 3

    def _get_extreme_fiber_x(self) -> float:
        """Distance from centroid to extreme fiber (x-axis)."""
        yc = self._centroid_y
        return max(yc, self.L1 - yc)

    def _get_extreme_fiber_y(self) -> float:
        """Distance from centroid to extreme fiber (y-axis)."""
        xc = self._centroid_x
        return max(xc, self.L2 - xc)

    def _calculate_Zx(self) -> float:
        """Approximate plastic section modulus about x-axis."""
        # Simplified approximation
        return 1.5 * self.Sx

    def _calculate_Zy(self) -> float:
        """Approximate plastic section modulus about y-axis."""
        # Simplified approximation
        return 1.5 * self.Sy

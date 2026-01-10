"""
Channel section (C-shape) parametric definition.

Creates channel sections with automatic property calculation.
"""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from paz.domain.sections.parametric import (
    ParametricSection,
    _validate_positive,
)
from paz.domain.sections.section import SectionShape


@dataclass
class Channel(ParametricSection):
    """
    Channel (C-shape) section.

    Dimensions:
        d: Total depth (m) - height of the web
        bf: Flange width (m)
        tf: Flange thickness (m)
        tw: Web thickness (m)

    ```
    |-------|  bf
    |=======|  tf
    |
    |         d
    |
    |=======|  tf
    |-------|
       tw
    ```

    Note: The y-axis (weak axis) does NOT pass through the center
    of the channel - it passes through the centroid.
    """

    d: float = 0.0  # Total depth (m)
    bf: float = 0.0  # Flange width (m)
    tf: float = 0.0  # Flange thickness (m)
    tw: float = 0.0  # Web thickness (m)
    name: str = "Channel"
    id: UUID = field(default_factory=uuid4)
    description: str = ""

    def _validate_dimensions(self) -> None:
        """Validate channel dimensions."""
        _validate_positive(self.d, "d (depth)")
        _validate_positive(self.bf, "bf (flange width)")
        _validate_positive(self.tf, "tf (flange thickness)")
        _validate_positive(self.tw, "tw (web thickness)")

        # Web height must be positive
        hw = self.d - 2 * self.tf
        if hw <= 0:
            raise ValueError(
                f"Web height (d - 2*tf = {hw}) must be positive. "
                f"Reduce flange thickness or increase depth."
            )

        # Web should be thinner than flange width
        if self.tw >= self.bf:
            raise ValueError(
                f"Web thickness ({self.tw}) should be less than flange width ({self.bf})"
            )

    def _get_shape(self) -> SectionShape:
        return SectionShape.C

    def _get_dimensions_dict(self) -> dict[str, float]:
        return {
            "d": self.d,
            "bf": self.bf,
            "tf": self.tf,
            "tw": self.tw,
        }

    @property
    def hw(self) -> float:
        """Web height (clear distance between flanges)."""
        return self.d - 2 * self.tf

    @property
    def _centroid_x(self) -> float:
        """X-coordinate of centroid from back of web."""
        # Web area
        Aw = self.hw * self.tw
        xw = self.tw / 2

        # Flange areas (2 flanges)
        Af = 2 * self.bf * self.tf
        xf = self.bf / 2

        return (Aw * xw + Af * xf) / (Aw + Af)

    def _calculate_A(self) -> float:
        """
        Calculate area.

        A = hw * tw + 2 * bf * tf
        """
        return self.hw * self.tw + 2 * self.bf * self.tf

    def _calculate_Ix(self) -> float:
        """
        Calculate moment of inertia about x-axis (strong axis, symmetric).

        Ix = (tw * hw³)/12 + 2*[bf*tf³/12 + bf*tf*(d/2 - tf/2)²]
        """
        # Web contribution
        Ix_web = self.tw * self.hw**3 / 12

        # Flange contribution (using parallel axis theorem)
        Af = self.bf * self.tf
        d_flange = (self.d - self.tf) / 2  # Distance from centroid to flange centroid
        Ix_flange = 2 * (self.bf * self.tf**3 / 12 + Af * d_flange**2)

        return Ix_web + Ix_flange

    def _calculate_Iy(self) -> float:
        """
        Calculate moment of inertia about y-axis (weak axis, through centroid).

        Uses parallel axis theorem since channel is not symmetric about y.
        """
        xc = self._centroid_x

        # Web contribution
        Aw = self.hw * self.tw
        xw = self.tw / 2
        Iy_web = self.hw * self.tw**3 / 12 + Aw * (xc - xw) ** 2

        # Flange contribution (2 flanges)
        Af = self.bf * self.tf
        xf = self.bf / 2
        Iy_flange = 2 * (self.tf * self.bf**3 / 12 + Af * (xc - xf) ** 2)

        return Iy_web + Iy_flange

    def _calculate_J(self) -> float:
        """
        Calculate torsional constant (approximate for thin-walled open section).

        J ≈ (1/3) * (2*bf*tf³ + hw*tw³)
        """
        return (2 * self.bf * self.tf**3 + self.hw * self.tw**3) / 3

    def _get_extreme_fiber_x(self) -> float:
        """Distance from centroid to extreme fiber (x-axis)."""
        return self.d / 2

    def _get_extreme_fiber_y(self) -> float:
        """Distance from centroid to extreme fiber (y-axis)."""
        xc = self._centroid_x
        return max(xc, self.bf - xc)

    def _calculate_Zx(self) -> float:
        """
        Plastic section modulus about x-axis.

        For symmetric section about x: Zx = bf*tf*(d-tf) + tw*hw²/4
        """
        return self.bf * self.tf * (self.d - self.tf) + self.tw * self.hw**2 / 4

    def _calculate_Zy(self) -> float:
        """Approximate plastic section modulus about y-axis."""
        # Simplified approximation for non-symmetric section
        return 1.5 * self.Sy

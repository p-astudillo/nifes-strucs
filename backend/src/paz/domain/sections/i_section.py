"""
I-Section (Wide Flange) parametric definition.

Creates I/H shaped sections with automatic property calculation.
"""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from paz.domain.sections.parametric import (
    ParametricSection,
    _validate_positive,
)
from paz.domain.sections.section import SectionShape


@dataclass
class ISection(ParametricSection):
    """
    Parametric I-Section (Wide Flange / H-shape).

    Dimensions:
        d: Total depth (m)
        bf: Flange width (m)
        tf: Flange thickness (m)
        tw: Web thickness (m)

    Properties are calculated assuming the section is symmetric
    about both axes, with the x-axis being the strong axis (horizontal)
    and y-axis being the weak axis (vertical through the web).

    ```
         bf
    |----------|
    |==========|  tf
    |    ||    |
    |    ||    |  d
    |    ||    |
    |==========|  tf
         tw
    ```
    """

    d: float = 0.0  # Total depth (m)
    bf: float = 0.0  # Flange width (m)
    tf: float = 0.0  # Flange thickness (m)
    tw: float = 0.0  # Web thickness (m)
    name: str = "Custom I-Section"
    id: UUID = field(default_factory=uuid4)
    description: str = ""

    def _validate_dimensions(self) -> None:
        """Validate I-section dimensions."""
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
        return SectionShape.W

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

    def _calculate_A(self) -> float:
        """
        Calculate area.

        A = 2 * bf * tf + hw * tw
        """
        return 2 * self.bf * self.tf + self.hw * self.tw

    def _calculate_Ix(self) -> float:
        """
        Calculate moment of inertia about x-axis (strong axis).

        Ix = (bf * d³)/12 - ((bf - tw) * hw³)/12
        """
        outer = (self.bf * self.d**3) / 12
        inner = ((self.bf - self.tw) * self.hw**3) / 12
        return outer - inner

    def _calculate_Iy(self) -> float:
        """
        Calculate moment of inertia about y-axis (weak axis).

        Iy = (2 * tf * bf³)/12 + (hw * tw³)/12
        """
        flanges = (2 * self.tf * self.bf**3) / 12
        web = (self.hw * self.tw**3) / 12
        return flanges + web

    def _calculate_J(self) -> float:
        """
        Calculate torsional constant (approximate for thin-walled open section).

        J ≈ (1/3) * (2*bf*tf³ + hw*tw³)
        """
        return (2 * self.bf * self.tf**3 + self.hw * self.tw**3) / 3

    def _get_extreme_fiber_x(self) -> float:
        """Distance from neutral axis to extreme fiber (x-axis)."""
        return self.d / 2

    def _get_extreme_fiber_y(self) -> float:
        """Distance from neutral axis to extreme fiber (y-axis)."""
        return self.bf / 2

    def _calculate_Zx(self) -> float:
        """
        Calculate plastic section modulus about x-axis.

        For I-section: Zx = bf*tf*(d-tf) + tw*hw²/4
        """
        return self.bf * self.tf * (self.d - self.tf) + self.tw * self.hw**2 / 4

    def _calculate_Zy(self) -> float:
        """
        Calculate plastic section modulus about y-axis.

        For I-section: Zy = tf*bf²/2 + hw*tw²/4
        """
        return self.tf * self.bf**2 / 2 + self.hw * self.tw**2 / 4

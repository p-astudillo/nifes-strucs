"""
T-Section parametric definition.

Creates T-shaped sections with automatic property calculation.
"""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from paz.domain.sections.parametric import (
    ParametricSection,
    _validate_positive,
)
from paz.domain.sections.section import SectionShape


@dataclass
class TSection(ParametricSection):
    """
    T-Section (Tee shape).

    Dimensions:
        d: Total depth (m) - from top of flange to bottom of stem
        bf: Flange width (m)
        tf: Flange thickness (m)
        tw: Stem (web) thickness (m)

    ```
    |=========|  tf
        ||
        ||       d - tf (stem height)
        ||
        tw
    |----bf----|
    ```

    Note: The x-axis (strong axis) does NOT pass through the center
    of the T - it passes through the centroid.
    """

    d: float = 0.0  # Total depth (m)
    bf: float = 0.0  # Flange width (m)
    tf: float = 0.0  # Flange thickness (m)
    tw: float = 0.0  # Stem thickness (m)
    name: str = "T-Section"
    id: UUID = field(default_factory=uuid4)
    description: str = ""

    def _validate_dimensions(self) -> None:
        """Validate T-section dimensions."""
        _validate_positive(self.d, "d (depth)")
        _validate_positive(self.bf, "bf (flange width)")
        _validate_positive(self.tf, "tf (flange thickness)")
        _validate_positive(self.tw, "tw (stem thickness)")

        # Stem height must be positive
        hs = self.d - self.tf
        if hs <= 0:
            raise ValueError(
                f"Stem height (d - tf = {hs}) must be positive. "
                f"Reduce flange thickness or increase depth."
            )

        # Stem should be thinner than flange width
        if self.tw >= self.bf:
            raise ValueError(
                f"Stem thickness ({self.tw}) should be less than flange width ({self.bf})"
            )

    def _get_shape(self) -> SectionShape:
        return SectionShape.WT

    def _get_dimensions_dict(self) -> dict[str, float]:
        return {
            "d": self.d,
            "bf": self.bf,
            "tf": self.tf,
            "tw": self.tw,
        }

    @property
    def hs(self) -> float:
        """Stem height."""
        return self.d - self.tf

    @property
    def _centroid_y(self) -> float:
        """Y-coordinate of centroid from bottom of stem."""
        # Flange area
        Af = self.bf * self.tf
        yf = self.d - self.tf / 2  # Distance to flange centroid from bottom

        # Stem area
        As = self.hs * self.tw
        ys = self.hs / 2  # Distance to stem centroid from bottom

        return (Af * yf + As * ys) / (Af + As)

    def _calculate_A(self) -> float:
        """
        Calculate area.

        A = bf * tf + hs * tw
        """
        return self.bf * self.tf + self.hs * self.tw

    def _calculate_Ix(self) -> float:
        """
        Calculate moment of inertia about x-axis (through centroid).

        Uses parallel axis theorem for composite section.
        """
        yc = self._centroid_y

        # Flange contribution
        Af = self.bf * self.tf
        yf = self.d - self.tf / 2
        Ix_flange = self.bf * self.tf**3 / 12 + Af * (yc - yf) ** 2

        # Stem contribution
        As = self.hs * self.tw
        ys = self.hs / 2
        Ix_stem = self.tw * self.hs**3 / 12 + As * (yc - ys) ** 2

        return Ix_flange + Ix_stem

    def _calculate_Iy(self) -> float:
        """
        Calculate moment of inertia about y-axis (symmetric).

        Iy = tf * bf³ / 12 + hs * tw³ / 12
        """
        return self.tf * self.bf**3 / 12 + self.hs * self.tw**3 / 12

    def _calculate_J(self) -> float:
        """
        Calculate torsional constant (approximate for thin-walled open section).

        J ≈ (1/3) * (bf*tf³ + hs*tw³)
        """
        return (self.bf * self.tf**3 + self.hs * self.tw**3) / 3

    def _get_extreme_fiber_x(self) -> float:
        """Distance from centroid to extreme fiber (x-axis)."""
        yc = self._centroid_y
        return max(yc, self.d - yc)

    def _get_extreme_fiber_y(self) -> float:
        """Distance from centroid to extreme fiber (y-axis)."""
        return self.bf / 2

    def _calculate_Zx(self) -> float:
        """Approximate plastic section modulus about x-axis."""
        # Simplified approximation for non-symmetric section
        return 1.3 * self.Sx

    def _calculate_Zy(self) -> float:
        """
        Plastic section modulus about y-axis.

        For symmetric section about y: Zy = tf*bf²/4 + hs*tw²/4
        """
        return self.tf * self.bf**2 / 4 + self.hs * self.tw**2 / 4

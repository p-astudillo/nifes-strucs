"""
Parametric section definitions for custom cross-sections.

Allows creating sections by specifying dimensions, with automatic
calculation of geometric properties (A, I, S, Z, r, J).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from math import sqrt
from typing import Any
from uuid import UUID, uuid4

from paz.core.exceptions import ValidationError
from paz.domain.sections.section import Section, SectionShape, SectionStandard


@dataclass
class ParametricSection(ABC):
    """
    Abstract base class for parametric sections.

    Subclasses must implement _calculate_properties() to compute
    geometric properties from dimensions.

    All dimensions are in meters (SI units).
    """

    name: str
    id: UUID = field(default_factory=uuid4)
    description: str = ""

    def __post_init__(self) -> None:
        """Validate dimensions after initialization."""
        self._validate_dimensions()

    @abstractmethod
    def _validate_dimensions(self) -> None:
        """Validate that dimensions are physically reasonable."""
        pass

    @abstractmethod
    def _calculate_A(self) -> float:
        """Calculate cross-sectional area (m²)."""
        pass

    @abstractmethod
    def _calculate_Ix(self) -> float:
        """Calculate moment of inertia about x-axis (m⁴)."""
        pass

    @abstractmethod
    def _calculate_Iy(self) -> float:
        """Calculate moment of inertia about y-axis (m⁴)."""
        pass

    @abstractmethod
    def _calculate_J(self) -> float:
        """Calculate torsional constant (m⁴)."""
        pass

    @abstractmethod
    def _get_shape(self) -> SectionShape:
        """Get the section shape type."""
        pass

    @abstractmethod
    def _get_dimensions_dict(self) -> dict[str, float]:
        """Get dimension properties as a dictionary."""
        pass

    @property
    def A(self) -> float:
        """Cross-sectional area (m²)."""
        return self._calculate_A()

    @property
    def Ix(self) -> float:
        """Moment of inertia about x-axis (m⁴)."""
        return self._calculate_Ix()

    @property
    def Iy(self) -> float:
        """Moment of inertia about y-axis (m⁴)."""
        return self._calculate_Iy()

    @property
    def J(self) -> float:
        """Torsional constant (m⁴)."""
        return self._calculate_J()

    @property
    def Sx(self) -> float:
        """Elastic section modulus about x-axis (m³)."""
        d = self._get_extreme_fiber_x()
        if d == 0:
            return 0.0
        return self.Ix / d

    @property
    def Sy(self) -> float:
        """Elastic section modulus about y-axis (m³)."""
        d = self._get_extreme_fiber_y()
        if d == 0:
            return 0.0
        return self.Iy / d

    @property
    def rx(self) -> float:
        """Radius of gyration about x-axis (m)."""
        if self.A == 0:
            return 0.0
        return sqrt(self.Ix / self.A)

    @property
    def ry(self) -> float:
        """Radius of gyration about y-axis (m)."""
        if self.A == 0:
            return 0.0
        return sqrt(self.Iy / self.A)

    def _get_extreme_fiber_x(self) -> float:
        """Get distance to extreme fiber from x-axis (for Sx calculation)."""
        # Default implementation - subclasses should override if needed
        dims = self._get_dimensions_dict()
        return dims.get("d", 0) / 2

    def _get_extreme_fiber_y(self) -> float:
        """Get distance to extreme fiber from y-axis (for Sy calculation)."""
        # Default implementation - subclasses should override if needed
        dims = self._get_dimensions_dict()
        return dims.get("bf", dims.get("B", dims.get("D", 0))) / 2

    def to_section(self) -> Section:
        """Convert parametric section to a standard Section object."""
        dims = self._get_dimensions_dict()
        return Section(
            id=self.id,
            name=self.name,
            shape=self._get_shape(),
            standard=SectionStandard.CUSTOM,
            A=self.A,
            Ix=self.Ix,
            Iy=self.Iy,
            Sx=self.Sx,
            Sy=self.Sy,
            Zx=self._calculate_Zx(),
            Zy=self._calculate_Zy(),
            rx=self.rx,
            ry=self.ry,
            J=self.J,
            d=dims.get("d"),
            bf=dims.get("bf"),
            tw=dims.get("tw"),
            tf=dims.get("tf"),
            t=dims.get("t"),
            OD=dims.get("OD"),
            description=self.description,
            is_custom=True,
        )

    def _calculate_Zx(self) -> float:
        """Calculate plastic section modulus about x-axis (m³)."""
        # Default: approximate as 1.1 * Sx for I-shapes
        # Subclasses should override with exact formula
        return 1.1 * self.Sx

    def _calculate_Zy(self) -> float:
        """Calculate plastic section modulus about y-axis (m³)."""
        # Default: approximate as 1.5 * Sy for I-shapes
        # Subclasses should override with exact formula
        return 1.5 * self.Sy

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return self.to_section().to_dict()


def _validate_positive(value: float, name: str) -> None:
    """Validate that a dimension is positive."""
    if value <= 0:
        raise ValidationError(
            f"{name} must be positive, got {value}",
            field=name,
        )


def _validate_thickness_ratio(t: float, outer: float, name: str) -> None:
    """Validate that thickness is reasonable relative to outer dimension."""
    if t >= outer / 2:
        raise ValidationError(
            f"Thickness {name} ({t}) must be less than half of outer dimension ({outer/2})",
            field=name,
        )

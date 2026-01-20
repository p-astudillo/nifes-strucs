"""
Mass source configuration for dynamic analysis.

Defines how mass is calculated for modal and dynamic analysis:
- From self-weight (automatic from materials and sections)
- From specified loads (with factors)
- Combined sources
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MassSourceType(str, Enum):
    """Types of mass sources for dynamic analysis."""

    SELF_WEIGHT = "self_weight"
    """Mass from element self-weight only (rho * A * L for frames)."""

    LOADS = "loads"
    """Mass from specified load cases with factors."""

    SELF_WEIGHT_PLUS_LOADS = "self_weight_plus_loads"
    """Combined: self-weight + specified loads with factors."""

    CUSTOM = "custom"
    """Custom mass definition per element."""


@dataclass
class LoadMassFactor:
    """
    Factor to convert a load case to mass contribution.

    For dynamic analysis, loads can contribute to mass.
    Example: Dead load contributes 100% (factor=1.0),
             Live load contributes 25% (factor=0.25).

    Attributes:
        load_case_name: Name of the load case
        factor: Factor to apply (0.0 to 1.0 typically)
    """

    load_case_name: str
    factor: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "load_case_name": self.load_case_name,
            "factor": self.factor,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoadMassFactor":
        """Create from dictionary."""
        return cls(
            load_case_name=data["load_case_name"],
            factor=data.get("factor", 1.0),
        )


@dataclass
class MassSource:
    """
    Configuration for how mass is calculated in dynamic analysis.

    In structural analysis, mass can come from:
    1. Self-weight of elements (automatic from geometry and materials)
    2. Applied loads (with reduction factors, e.g., 25% of live load)
    3. Custom mass assignments

    Attributes:
        source_type: Type of mass source
        include_self_weight: Whether to include element self-weight
        self_weight_factor: Factor for self-weight (default 1.0)
        load_factors: List of load cases with their mass factors
        lumped_mass: Whether to use lumped mass (True) or consistent mass (False)
    """

    source_type: MassSourceType = MassSourceType.SELF_WEIGHT
    include_self_weight: bool = True
    self_weight_factor: float = 1.0
    load_factors: list[LoadMassFactor] = field(default_factory=list)
    lumped_mass: bool = True  # Lumped mass is default for efficiency

    def __post_init__(self) -> None:
        """Validate mass source configuration."""
        if self.self_weight_factor < 0:
            raise ValueError("self_weight_factor cannot be negative")

        for lf in self.load_factors:
            if lf.factor < 0:
                raise ValueError(f"Load factor for {lf.load_case_name} cannot be negative")

    def add_load_factor(self, load_case_name: str, factor: float = 1.0) -> None:
        """
        Add a load case contribution to mass.

        Args:
            load_case_name: Name of the load case
            factor: Factor to apply (e.g., 1.0 for dead, 0.25 for live)
        """
        # Remove existing entry for same load case if exists
        self.load_factors = [lf for lf in self.load_factors if lf.load_case_name != load_case_name]
        self.load_factors.append(LoadMassFactor(load_case_name, factor))

    def remove_load_factor(self, load_case_name: str) -> None:
        """Remove a load case from mass calculation."""
        self.load_factors = [lf for lf in self.load_factors if lf.load_case_name != load_case_name]

    def get_load_factor(self, load_case_name: str) -> float | None:
        """Get factor for a specific load case, or None if not included."""
        for lf in self.load_factors:
            if lf.load_case_name == load_case_name:
                return lf.factor
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source_type": self.source_type.value,
            "include_self_weight": self.include_self_weight,
            "self_weight_factor": self.self_weight_factor,
            "load_factors": [lf.to_dict() for lf in self.load_factors],
            "lumped_mass": self.lumped_mass,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MassSource":
        """Create from dictionary."""
        load_factors = [
            LoadMassFactor.from_dict(lf) for lf in data.get("load_factors", [])
        ]
        return cls(
            source_type=MassSourceType(data.get("source_type", "self_weight")),
            include_self_weight=data.get("include_self_weight", True),
            self_weight_factor=data.get("self_weight_factor", 1.0),
            load_factors=load_factors,
            lumped_mass=data.get("lumped_mass", True),
        )

    @classmethod
    def self_weight_only(cls) -> "MassSource":
        """Create a mass source from self-weight only."""
        return cls(
            source_type=MassSourceType.SELF_WEIGHT,
            include_self_weight=True,
            self_weight_factor=1.0,
        )

    @classmethod
    def dead_plus_live(cls, live_factor: float = 0.25) -> "MassSource":
        """
        Create a typical mass source: self-weight + dead load + fraction of live.

        Args:
            live_factor: Factor for live load (default 0.25 = 25%)

        Returns:
            MassSource configured for dead + live combination
        """
        return cls(
            source_type=MassSourceType.SELF_WEIGHT_PLUS_LOADS,
            include_self_weight=True,
            self_weight_factor=1.0,
            load_factors=[
                LoadMassFactor("Dead", 1.0),
                LoadMassFactor("Live", live_factor),
            ],
        )

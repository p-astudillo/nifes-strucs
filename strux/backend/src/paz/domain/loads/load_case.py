"""
Load case definitions for structural analysis.

A load case groups loads that act together (e.g., all dead loads, all live loads).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class LoadCaseType(str, Enum):
    """Standard load case types."""

    DEAD = "Dead"  # Self-weight and permanent loads
    LIVE = "Live"  # Occupancy loads
    ROOF_LIVE = "Roof Live"  # Roof live loads
    SNOW = "Snow"  # Snow loads
    WIND = "Wind"  # Wind loads
    SEISMIC = "Seismic"  # Earthquake loads
    TEMPERATURE = "Temperature"  # Thermal effects
    OTHER = "Other"  # User-defined


@dataclass
class LoadCase:
    """
    A load case containing related loads.

    Attributes:
        id: Unique identifier
        name: Load case name (e.g., "DL", "LL", "Wind X")
        load_type: Type of load case
        description: Optional description
        self_weight_multiplier: Multiplier for automatic self-weight (0 = no self-weight)
    """

    name: str
    load_type: LoadCaseType = LoadCaseType.OTHER
    id: UUID = field(default_factory=uuid4)
    description: str = ""
    self_weight_multiplier: float = 0.0

    def __post_init__(self) -> None:
        """Validate load case."""
        if not self.name:
            raise ValueError("Load case name cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "load_type": self.load_type.value,
            "description": self.description,
            "self_weight_multiplier": self.self_weight_multiplier,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoadCase":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            name=data["name"],
            load_type=LoadCaseType(data.get("load_type", "Other")),
            description=data.get("description", ""),
            self_weight_multiplier=data.get("self_weight_multiplier", 0.0),
        )


# Common predefined load cases
DEAD_LOAD = LoadCase(name="Dead", load_type=LoadCaseType.DEAD, self_weight_multiplier=1.0)
LIVE_LOAD = LoadCase(name="Live", load_type=LoadCaseType.LIVE)
WIND_X = LoadCase(name="Wind X", load_type=LoadCaseType.WIND)
WIND_Y = LoadCase(name="Wind Y", load_type=LoadCaseType.WIND)
SEISMIC_X = LoadCase(name="Seismic X", load_type=LoadCaseType.SEISMIC)
SEISMIC_Y = LoadCase(name="Seismic Y", load_type=LoadCaseType.SEISMIC)

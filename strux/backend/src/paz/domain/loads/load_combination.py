"""
Load combination definitions for structural analysis.

Load combinations define how individual load cases are factored and combined
for design checks (e.g., 1.2D + 1.6L for LRFD).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class CombinationType(str, Enum):
    """Type of load combination."""

    LINEAR = "Linear"  # Simple linear combination with factors
    ENVELOPE = "Envelope"  # Max/min envelope of results
    ABS_ADD = "Absolute Add"  # Sum of absolute values


@dataclass
class LoadCombinationItem:
    """
    A load case with its factor in a combination.

    Attributes:
        load_case_id: ID of the load case
        factor: Multiplication factor for this load case
    """

    load_case_id: UUID
    factor: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "load_case_id": str(self.load_case_id),
            "factor": self.factor,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoadCombinationItem":
        """Create from dictionary."""
        return cls(
            load_case_id=UUID(data["load_case_id"]),
            factor=data.get("factor", 1.0),
        )


@dataclass
class LoadCombination:
    """
    A combination of load cases with factors.

    Attributes:
        id: Unique identifier
        name: Combination name (e.g., "1.2D+1.6L", "Envelope")
        combination_type: Type of combination
        items: List of load cases with their factors
        description: Optional description
    """

    name: str
    items: list[LoadCombinationItem] = field(default_factory=list)
    combination_type: CombinationType = CombinationType.LINEAR
    id: UUID = field(default_factory=uuid4)
    description: str = ""

    def __post_init__(self) -> None:
        """Validate combination."""
        if not self.name:
            raise ValueError("Load combination name cannot be empty")

    def add_case(self, load_case_id: UUID, factor: float = 1.0) -> None:
        """Add a load case to the combination."""
        self.items.append(LoadCombinationItem(load_case_id=load_case_id, factor=factor))

    def get_factor(self, load_case_id: UUID) -> float | None:
        """Get the factor for a specific load case, or None if not in combination."""
        for item in self.items:
            if item.load_case_id == load_case_id:
                return item.factor
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "combination_type": self.combination_type.value,
            "items": [item.to_dict() for item in self.items],
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoadCombination":
        """Create from dictionary."""
        items = [
            LoadCombinationItem.from_dict(item_data)
            for item_data in data.get("items", [])
        ]
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            name=data["name"],
            combination_type=CombinationType(data.get("combination_type", "Linear")),
            items=items,
            description=data.get("description", ""),
        )


def create_lrfd_combinations(
    dead_case_id: UUID,
    live_case_id: UUID,
) -> list[LoadCombination]:
    """
    Create standard LRFD load combinations.

    Returns combinations per ASCE 7:
    - 1.4D
    - 1.2D + 1.6L
    """
    combinations = [
        LoadCombination(
            name="1.4D",
            items=[LoadCombinationItem(dead_case_id, 1.4)],
            description="LRFD: Dead only",
        ),
        LoadCombination(
            name="1.2D+1.6L",
            items=[
                LoadCombinationItem(dead_case_id, 1.2),
                LoadCombinationItem(live_case_id, 1.6),
            ],
            description="LRFD: Dead + Live",
        ),
    ]
    return combinations


def create_asd_combinations(
    dead_case_id: UUID,
    live_case_id: UUID,
) -> list[LoadCombination]:
    """
    Create standard ASD load combinations.

    Returns combinations per ASCE 7:
    - D
    - D + L
    """
    combinations = [
        LoadCombination(
            name="D",
            items=[LoadCombinationItem(dead_case_id, 1.0)],
            description="ASD: Dead only",
        ),
        LoadCombination(
            name="D+L",
            items=[
                LoadCombinationItem(dead_case_id, 1.0),
                LoadCombinationItem(live_case_id, 1.0),
            ],
            description="ASD: Dead + Live",
        ),
    ]
    return combinations

"""
Point load on frame element.

Represents concentrated forces and moments applied at a specific
location along a frame element.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class PointLoadDirection(str, Enum):
    """Direction of point load on frame."""

    LOCAL_X = "Local X"  # Axial (along element)
    LOCAL_Y = "Local Y"  # Perpendicular in local Y
    LOCAL_Z = "Local Z"  # Perpendicular in local Z
    GLOBAL_X = "Global X"
    GLOBAL_Y = "Global Y"
    GLOBAL_Z = "Global Z"
    GRAVITY = "Gravity"  # Always in -Z global


@dataclass
class PointLoadOnFrame:
    """
    A concentrated load applied at a point along a frame element.

    Attributes:
        id: Unique identifier
        frame_id: ID of the frame element
        load_case_id: ID of the load case this load belongs to
        location: Location along frame as fraction of length (0-1)
        P: Force magnitude (kN)
        direction: Direction of the force
        M: Optional moment magnitude (kN-m), applied about axis perpendicular to direction
    """

    frame_id: int
    load_case_id: UUID
    location: float  # 0-1 fraction of frame length
    P: float  # Force in kN
    direction: PointLoadDirection = PointLoadDirection.GRAVITY
    M: float = 0.0  # Optional moment
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        """Validate point load."""
        if not 0.0 <= self.location <= 1.0:
            raise ValueError(
                f"location must be between 0 and 1, got {self.location}"
            )

    @property
    def is_at_start(self) -> bool:
        """Check if load is at start of element."""
        return self.location == 0.0

    @property
    def is_at_end(self) -> bool:
        """Check if load is at end of element."""
        return self.location == 1.0

    @property
    def is_at_midpoint(self) -> bool:
        """Check if load is at midpoint of element."""
        return abs(self.location - 0.5) < 1e-6

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "frame_id": self.frame_id,
            "load_case_id": str(self.load_case_id),
            "location": self.location,
            "P": self.P,
            "direction": self.direction.value,
            "M": self.M,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PointLoadOnFrame":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            frame_id=data["frame_id"],
            load_case_id=UUID(data["load_case_id"]),
            location=data.get("location", 0.5),
            P=data.get("P", 0.0),
            direction=PointLoadDirection(data.get("direction", "Gravity")),
            M=data.get("M", 0.0),
        )


def midpoint_load(
    frame_id: int,
    load_case_id: UUID,
    P: float,
    direction: PointLoadDirection = PointLoadDirection.GRAVITY,
) -> PointLoadOnFrame:
    """Create a point load at midpoint of frame."""
    return PointLoadOnFrame(
        frame_id=frame_id,
        load_case_id=load_case_id,
        location=0.5,
        P=P,
        direction=direction,
    )

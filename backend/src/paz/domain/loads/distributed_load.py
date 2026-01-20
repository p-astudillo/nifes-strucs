"""
Distributed load definitions for frame elements.

Represents loads distributed along the length of a frame element.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class LoadDirection(str, Enum):
    """Direction of distributed load."""

    GRAVITY = "Gravity"  # Always in -Z global direction
    LOCAL_X = "Local X"  # Along element axis
    LOCAL_Y = "Local Y"  # Perpendicular in local Y
    LOCAL_Z = "Local Z"  # Perpendicular in local Z
    GLOBAL_X = "Global X"
    GLOBAL_Y = "Global Y"
    GLOBAL_Z = "Global Z"


@dataclass
class DistributedLoad:
    """
    A distributed load along a frame element.

    Can be uniform or trapezoidal (varying linearly from start to end).
    Load intensity is in kN/m.

    Attributes:
        id: Unique identifier
        frame_id: ID of the frame element
        load_case_id: ID of the load case this load belongs to
        direction: Direction of the load
        w_start: Load intensity at start of element (kN/m)
        w_end: Load intensity at end of element (kN/m)
        start_loc: Start location as fraction of length (0-1)
        end_loc: End location as fraction of length (0-1)
    """

    frame_id: int
    load_case_id: UUID
    direction: LoadDirection = LoadDirection.GRAVITY
    w_start: float = 0.0
    w_end: float | None = None  # None means uniform (w_end = w_start)
    start_loc: float = 0.0
    end_loc: float = 1.0
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        """Validate and normalize load."""
        if self.w_end is None:
            self.w_end = self.w_start

        if not 0.0 <= self.start_loc <= 1.0:
            raise ValueError(f"start_loc must be between 0 and 1, got {self.start_loc}")
        if not 0.0 <= self.end_loc <= 1.0:
            raise ValueError(f"end_loc must be between 0 and 1, got {self.end_loc}")
        if self.start_loc >= self.end_loc:
            raise ValueError(
                f"start_loc ({self.start_loc}) must be less than end_loc ({self.end_loc})"
            )

    @property
    def is_uniform(self) -> bool:
        """Check if load is uniform (constant intensity)."""
        return self.w_start == self.w_end

    @property
    def is_full_length(self) -> bool:
        """Check if load covers full element length."""
        return self.start_loc == 0.0 and self.end_loc == 1.0

    @property
    def average_intensity(self) -> float:
        """Get average load intensity."""
        if self.w_end is None:
            return self.w_start
        return (self.w_start + self.w_end) / 2

    def intensity_at(self, location: float) -> float:
        """
        Get load intensity at a specific location.

        Args:
            location: Location as fraction of length (0-1)

        Returns:
            Load intensity at location (kN/m), or 0 if outside load range
        """
        if location < self.start_loc or location > self.end_loc:
            return 0.0

        if self.w_end is None or self.is_uniform:
            return self.w_start

        # Linear interpolation
        t = (location - self.start_loc) / (self.end_loc - self.start_loc)
        return self.w_start + t * (self.w_end - self.w_start)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "frame_id": self.frame_id,
            "load_case_id": str(self.load_case_id),
            "direction": self.direction.value,
            "w_start": self.w_start,
            "w_end": self.w_end,
            "start_loc": self.start_loc,
            "end_loc": self.end_loc,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DistributedLoad":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            frame_id=data["frame_id"],
            load_case_id=UUID(data["load_case_id"]),
            direction=LoadDirection(data.get("direction", "Gravity")),
            w_start=data.get("w_start", 0.0),
            w_end=data.get("w_end"),
            start_loc=data.get("start_loc", 0.0),
            end_loc=data.get("end_loc", 1.0),
        )


def uniform_load(
    frame_id: int,
    load_case_id: UUID,
    w: float,
    direction: LoadDirection = LoadDirection.GRAVITY,
) -> DistributedLoad:
    """Create a uniform distributed load over full element length."""
    return DistributedLoad(
        frame_id=frame_id,
        load_case_id=load_case_id,
        direction=direction,
        w_start=w,
        w_end=w,
        start_loc=0.0,
        end_loc=1.0,
    )


def triangular_load(
    frame_id: int,
    load_case_id: UUID,
    w_max: float,
    ascending: bool = True,
    direction: LoadDirection = LoadDirection.GRAVITY,
) -> DistributedLoad:
    """
    Create a triangular distributed load over full element length.

    Args:
        frame_id: ID of the frame element
        load_case_id: ID of the load case
        w_max: Maximum load intensity at one end (kN/m)
        ascending: If True, load increases from 0 at start to w_max at end
                   If False, load decreases from w_max at start to 0 at end
        direction: Direction of the load

    Returns:
        DistributedLoad with triangular variation
    """
    if ascending:
        return DistributedLoad(
            frame_id=frame_id,
            load_case_id=load_case_id,
            direction=direction,
            w_start=0.0,
            w_end=w_max,
            start_loc=0.0,
            end_loc=1.0,
        )
    else:
        return DistributedLoad(
            frame_id=frame_id,
            load_case_id=load_case_id,
            direction=direction,
            w_start=w_max,
            w_end=0.0,
            start_loc=0.0,
            end_loc=1.0,
        )


def trapezoidal_load(
    frame_id: int,
    load_case_id: UUID,
    w_start: float,
    w_end: float,
    direction: LoadDirection = LoadDirection.GRAVITY,
    start_loc: float = 0.0,
    end_loc: float = 1.0,
) -> DistributedLoad:
    """
    Create a trapezoidal distributed load.

    Args:
        frame_id: ID of the frame element
        load_case_id: ID of the load case
        w_start: Load intensity at start (kN/m)
        w_end: Load intensity at end (kN/m)
        direction: Direction of the load
        start_loc: Start location as fraction of length (0-1)
        end_loc: End location as fraction of length (0-1)

    Returns:
        DistributedLoad with trapezoidal/linear variation
    """
    return DistributedLoad(
        frame_id=frame_id,
        load_case_id=load_case_id,
        direction=direction,
        w_start=w_start,
        w_end=w_end,
        start_loc=start_loc,
        end_loc=end_loc,
    )


def partial_uniform_load(
    frame_id: int,
    load_case_id: UUID,
    w: float,
    start_loc: float,
    end_loc: float,
    direction: LoadDirection = LoadDirection.GRAVITY,
) -> DistributedLoad:
    """
    Create a uniform distributed load over partial element length.

    Args:
        frame_id: ID of the frame element
        load_case_id: ID of the load case
        w: Load intensity (kN/m)
        start_loc: Start location as fraction of length (0-1)
        end_loc: End location as fraction of length (0-1)
        direction: Direction of the load

    Returns:
        DistributedLoad with uniform intensity over partial length
    """
    return DistributedLoad(
        frame_id=frame_id,
        load_case_id=load_case_id,
        direction=direction,
        w_start=w,
        w_end=w,
        start_loc=start_loc,
        end_loc=end_loc,
    )

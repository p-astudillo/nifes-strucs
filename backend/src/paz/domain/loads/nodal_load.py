"""
Nodal (point) load definitions.

Represents concentrated forces and moments applied at nodes.
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4


@dataclass
class NodalLoad:
    """
    A concentrated load applied at a node.

    Forces are in global coordinates (kN).
    Moments are in global coordinates (kN-m).

    Attributes:
        id: Unique identifier
        node_id: ID of the node where load is applied
        load_case_id: ID of the load case this load belongs to
        Fx: Force in global X direction (kN)
        Fy: Force in global Y direction (kN)
        Fz: Force in global Z direction (kN)
        Mx: Moment about global X axis (kN-m)
        My: Moment about global Y axis (kN-m)
        Mz: Moment about global Z axis (kN-m)
    """

    node_id: int
    load_case_id: UUID
    Fx: float = 0.0
    Fy: float = 0.0
    Fz: float = 0.0
    Mx: float = 0.0
    My: float = 0.0
    Mz: float = 0.0
    id: UUID = field(default_factory=uuid4)

    @property
    def force_vector(self) -> tuple[float, float, float]:
        """Get force components as a tuple."""
        return (self.Fx, self.Fy, self.Fz)

    @property
    def moment_vector(self) -> tuple[float, float, float]:
        """Get moment components as a tuple."""
        return (self.Mx, self.My, self.Mz)

    @property
    def is_zero(self) -> bool:
        """Check if all load components are zero."""
        return (
            self.Fx == 0.0
            and self.Fy == 0.0
            and self.Fz == 0.0
            and self.Mx == 0.0
            and self.My == 0.0
            and self.Mz == 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "node_id": self.node_id,
            "load_case_id": str(self.load_case_id),
            "Fx": self.Fx,
            "Fy": self.Fy,
            "Fz": self.Fz,
            "Mx": self.Mx,
            "My": self.My,
            "Mz": self.Mz,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NodalLoad":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            node_id=data["node_id"],
            load_case_id=UUID(data["load_case_id"]),
            Fx=data.get("Fx", 0.0),
            Fy=data.get("Fy", 0.0),
            Fz=data.get("Fz", 0.0),
            Mx=data.get("Mx", 0.0),
            My=data.get("My", 0.0),
            Mz=data.get("Mz", 0.0),
        )

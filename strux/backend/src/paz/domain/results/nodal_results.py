"""
Nodal results from structural analysis.

Contains displacements and reactions at nodes.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class NodalDisplacement:
    """
    Displacement results at a node.

    All values are in global coordinates.
    Translations in meters (m), rotations in radians (rad).
    """

    node_id: int
    Ux: float = 0.0  # Translation in X (m)
    Uy: float = 0.0  # Translation in Y (m)
    Uz: float = 0.0  # Translation in Z (m)
    Rx: float = 0.0  # Rotation about X (rad)
    Ry: float = 0.0  # Rotation about Y (rad)
    Rz: float = 0.0  # Rotation about Z (rad)

    @property
    def translation_magnitude(self) -> float:
        """Total translational displacement magnitude."""
        return float((self.Ux**2 + self.Uy**2 + self.Uz**2) ** 0.5)

    @property
    def rotation_magnitude(self) -> float:
        """Total rotational displacement magnitude."""
        return float((self.Rx**2 + self.Ry**2 + self.Rz**2) ** 0.5)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "node_id": self.node_id,
            "Ux": self.Ux,
            "Uy": self.Uy,
            "Uz": self.Uz,
            "Rx": self.Rx,
            "Ry": self.Ry,
            "Rz": self.Rz,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NodalDisplacement":
        """Create from dictionary."""
        return cls(
            node_id=data["node_id"],
            Ux=data.get("Ux", 0.0),
            Uy=data.get("Uy", 0.0),
            Uz=data.get("Uz", 0.0),
            Rx=data.get("Rx", 0.0),
            Ry=data.get("Ry", 0.0),
            Rz=data.get("Rz", 0.0),
        )


@dataclass
class NodalReaction:
    """
    Reaction forces at a support node.

    All values are in global coordinates.
    Forces in kN, moments in kN-m.
    """

    node_id: int
    Fx: float = 0.0  # Reaction force in X (kN)
    Fy: float = 0.0  # Reaction force in Y (kN)
    Fz: float = 0.0  # Reaction force in Z (kN)
    Mx: float = 0.0  # Reaction moment about X (kN-m)
    My: float = 0.0  # Reaction moment about Y (kN-m)
    Mz: float = 0.0  # Reaction moment about Z (kN-m)

    @property
    def force_magnitude(self) -> float:
        """Total reaction force magnitude."""
        return float((self.Fx**2 + self.Fy**2 + self.Fz**2) ** 0.5)

    @property
    def moment_magnitude(self) -> float:
        """Total reaction moment magnitude."""
        return float((self.Mx**2 + self.My**2 + self.Mz**2) ** 0.5)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "node_id": self.node_id,
            "Fx": self.Fx,
            "Fy": self.Fy,
            "Fz": self.Fz,
            "Mx": self.Mx,
            "My": self.My,
            "Mz": self.Mz,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NodalReaction":
        """Create from dictionary."""
        return cls(
            node_id=data["node_id"],
            Fx=data.get("Fx", 0.0),
            Fy=data.get("Fy", 0.0),
            Fz=data.get("Fz", 0.0),
            Mx=data.get("Mx", 0.0),
            My=data.get("My", 0.0),
            Mz=data.get("Mz", 0.0),
        )

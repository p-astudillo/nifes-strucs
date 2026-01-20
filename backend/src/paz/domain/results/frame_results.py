"""
Frame element results from structural analysis.

Contains internal forces (P, V, M, T) along frame elements.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FrameForces:
    """
    Internal forces at a point along a frame element.

    Forces are in local coordinates:
    - P: Axial force (+ = tension)
    - V2: Shear in local 2 direction
    - V3: Shear in local 3 direction
    - T: Torsion (moment about local 1 axis)
    - M2: Moment about local 2 axis (bending in 1-3 plane)
    - M3: Moment about local 3 axis (bending in 1-2 plane)

    Units: Forces in kN, Moments in kN-m
    """

    location: float  # Location as fraction of length (0-1)
    P: float = 0.0  # Axial force (kN)
    V2: float = 0.0  # Shear force in local 2 (kN)
    V3: float = 0.0  # Shear force in local 3 (kN)
    T: float = 0.0  # Torsion (kN-m)
    M2: float = 0.0  # Moment about local 2 (kN-m)
    M3: float = 0.0  # Moment about local 3 (kN-m)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "location": self.location,
            "P": self.P,
            "V2": self.V2,
            "V3": self.V3,
            "T": self.T,
            "M2": self.M2,
            "M3": self.M3,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FrameForces":
        """Create from dictionary."""
        return cls(
            location=data["location"],
            P=data.get("P", 0.0),
            V2=data.get("V2", 0.0),
            V3=data.get("V3", 0.0),
            T=data.get("T", 0.0),
            M2=data.get("M2", 0.0),
            M3=data.get("M3", 0.0),
        )


@dataclass
class FrameResult:
    """
    Complete results for a single frame element.

    Contains forces at multiple points along the element
    (typically start, middle, and end, or more for accuracy).
    """

    frame_id: int
    forces: list[FrameForces] = field(default_factory=list)

    @property
    def P_max(self) -> float:
        """Maximum axial force (tension positive)."""
        if not self.forces:
            return 0.0
        return max(f.P for f in self.forces)

    @property
    def P_min(self) -> float:
        """Minimum axial force (compression negative)."""
        if not self.forces:
            return 0.0
        return min(f.P for f in self.forces)

    @property
    def V2_max(self) -> float:
        """Maximum shear in local 2 (with sign, max by absolute value)."""
        if not self.forces:
            return 0.0
        return max((f.V2 for f in self.forces), key=abs)

    @property
    def V3_max(self) -> float:
        """Maximum shear in local 3 (with sign, max by absolute value)."""
        if not self.forces:
            return 0.0
        return max((f.V3 for f in self.forces), key=abs)

    @property
    def M2_max(self) -> float:
        """Maximum moment about local 2 (with sign, max by absolute value)."""
        if not self.forces:
            return 0.0
        return max((f.M2 for f in self.forces), key=abs)

    @property
    def M3_max(self) -> float:
        """Maximum moment about local 3 (with sign, max by absolute value)."""
        if not self.forces:
            return 0.0
        return max((f.M3 for f in self.forces), key=abs)

    @property
    def T_max(self) -> float:
        """Maximum torsion (with sign, max by absolute value)."""
        if not self.forces:
            return 0.0
        return max((f.T for f in self.forces), key=abs)

    @property
    def V_max(self) -> float:
        """Maximum shear (either direction, with sign)."""
        v2 = self.V2_max
        v3 = self.V3_max
        return v2 if abs(v2) >= abs(v3) else v3

    @property
    def M_max(self) -> float:
        """Maximum moment (either axis, with sign)."""
        m2 = self.M2_max
        m3 = self.M3_max
        return m2 if abs(m2) >= abs(m3) else m3

    def force_at_start(self) -> FrameForces | None:
        """Get forces at start of element (location = 0)."""
        for f in self.forces:
            if f.location == 0.0:
                return f
        return self.forces[0] if self.forces else None

    def force_at_end(self) -> FrameForces | None:
        """Get forces at end of element (location = 1)."""
        for f in self.forces:
            if f.location == 1.0:
                return f
        return self.forces[-1] if self.forces else None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "frame_id": self.frame_id,
            "forces": [f.to_dict() for f in self.forces],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FrameResult":
        """Create from dictionary."""
        forces = [FrameForces.from_dict(f) for f in data.get("forces", [])]
        return cls(frame_id=data["frame_id"], forces=forces)

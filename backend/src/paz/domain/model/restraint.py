"""
Restraint (boundary condition) model for structural nodes.

Defines which degrees of freedom are fixed at a node.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RestraintType(str, Enum):
    """
    Predefined restraint types for common support conditions.
    """

    FREE = "free"
    FIXED = "fixed"
    PINNED = "pinned"
    ROLLER_X = "roller_x"
    ROLLER_Y = "roller_y"
    ROLLER_Z = "roller_z"
    VERTICAL_ONLY = "vertical_only"
    CUSTOM = "custom"


@dataclass(frozen=True)
class Restraint:
    """
    Represents boundary conditions at a node.

    Each boolean indicates whether that degree of freedom is restrained (fixed).
    True = fixed, False = free.

    Attributes:
        ux: Translation in X direction
        uy: Translation in Y direction
        uz: Translation in Z direction
        rx: Rotation about X axis
        ry: Rotation about Y axis
        rz: Rotation about Z axis
    """

    ux: bool = False
    uy: bool = False
    uz: bool = False
    rx: bool = False
    ry: bool = False
    rz: bool = False

    @property
    def is_free(self) -> bool:
        """Check if all degrees of freedom are free."""
        return not any([self.ux, self.uy, self.uz, self.rx, self.ry, self.rz])

    @property
    def is_fixed(self) -> bool:
        """Check if all degrees of freedom are fixed."""
        return all([self.ux, self.uy, self.uz, self.rx, self.ry, self.rz])

    @property
    def is_pinned(self) -> bool:
        """Check if translations are fixed but rotations are free."""
        return (
            self.ux
            and self.uy
            and self.uz
            and not self.rx
            and not self.ry
            and not self.rz
        )

    def to_list(self) -> list[bool]:
        """Convert to list [ux, uy, uz, rx, ry, rz]."""
        return [self.ux, self.uy, self.uz, self.rx, self.ry, self.rz]

    def to_int_list(self) -> list[int]:
        """Convert to integer list (1=fixed, 0=free) for OpenSees."""
        return [int(v) for v in self.to_list()]

    def to_dict(self) -> dict[str, bool]:
        """Convert to dictionary for serialization."""
        return {
            "ux": self.ux,
            "uy": self.uy,
            "uz": self.uz,
            "rx": self.rx,
            "ry": self.ry,
            "rz": self.rz,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Restraint":
        """Create from dictionary."""
        return cls(
            ux=bool(data.get("ux", False)),
            uy=bool(data.get("uy", False)),
            uz=bool(data.get("uz", False)),
            rx=bool(data.get("rx", False)),
            ry=bool(data.get("ry", False)),
            rz=bool(data.get("rz", False)),
        )

    @classmethod
    def from_list(cls, values: list[bool | int]) -> "Restraint":
        """Create from list [ux, uy, uz, rx, ry, rz]."""
        if len(values) != 6:
            msg = f"Expected 6 values, got {len(values)}"
            raise ValueError(msg)
        return cls(
            ux=bool(values[0]),
            uy=bool(values[1]),
            uz=bool(values[2]),
            rx=bool(values[3]),
            ry=bool(values[4]),
            rz=bool(values[5]),
        )

    @classmethod
    def from_type(cls, restraint_type: RestraintType | str) -> "Restraint":
        """
        Create restraint from a predefined type.

        Args:
            restraint_type: RestraintType enum or string value

        Returns:
            Restraint with appropriate DOF configuration
        """
        if isinstance(restraint_type, str):
            restraint_type = RestraintType(restraint_type)

        mapping = {
            RestraintType.FREE: FREE,
            RestraintType.FIXED: FIXED,
            RestraintType.PINNED: PINNED,
            RestraintType.ROLLER_X: ROLLER_X,
            RestraintType.ROLLER_Y: ROLLER_Y,
            RestraintType.ROLLER_Z: ROLLER_Z,
            RestraintType.VERTICAL_ONLY: VERTICAL_ONLY,
        }

        if restraint_type == RestraintType.CUSTOM:
            return FREE  # Custom starts as free, user sets DOFs manually

        return mapping.get(restraint_type, FREE)

    def get_type(self) -> RestraintType:
        """
        Determine the restraint type based on current DOF configuration.

        Returns:
            RestraintType that matches the current configuration
        """
        if self.is_free:
            return RestraintType.FREE
        if self.is_fixed:
            return RestraintType.FIXED
        if self.is_pinned:
            return RestraintType.PINNED

        # Check roller types
        if (
            not self.ux
            and self.uy
            and self.uz
            and not self.rx
            and not self.ry
            and not self.rz
        ):
            return RestraintType.ROLLER_X
        if (
            self.ux
            and not self.uy
            and self.uz
            and not self.rx
            and not self.ry
            and not self.rz
        ):
            return RestraintType.ROLLER_Y
        if (
            self.ux
            and self.uy
            and not self.uz
            and not self.rx
            and not self.ry
            and not self.rz
        ):
            return RestraintType.ROLLER_Z

        # Check vertical only
        if (
            not self.ux
            and not self.uy
            and self.uz
            and not self.rx
            and not self.ry
            and not self.rz
        ):
            return RestraintType.VERTICAL_ONLY

        return RestraintType.CUSTOM


# Common restraint presets
FREE = Restraint()
FIXED = Restraint(ux=True, uy=True, uz=True, rx=True, ry=True, rz=True)
PINNED = Restraint(ux=True, uy=True, uz=True, rx=False, ry=False, rz=False)
ROLLER_X = Restraint(ux=False, uy=True, uz=True, rx=False, ry=False, rz=False)
ROLLER_Y = Restraint(ux=True, uy=False, uz=True, rx=False, ry=False, rz=False)
ROLLER_Z = Restraint(ux=True, uy=True, uz=False, rx=False, ry=False, rz=False)
VERTICAL_ONLY = Restraint(ux=False, uy=False, uz=True, rx=False, ry=False, rz=False)


# Type descriptions for UI
RESTRAINT_TYPE_LABELS = {
    RestraintType.FREE: "Libre",
    RestraintType.FIXED: "Empotrado",
    RestraintType.PINNED: "Articulado",
    RestraintType.ROLLER_X: "Rodillo X",
    RestraintType.ROLLER_Y: "Rodillo Y",
    RestraintType.ROLLER_Z: "Rodillo Z",
    RestraintType.VERTICAL_ONLY: "Fijo Vertical",
    RestraintType.CUSTOM: "Personalizado",
}


RESTRAINT_TYPE_DESCRIPTIONS = {
    RestraintType.FREE: "Todos los DOF libres",
    RestraintType.FIXED: "Todos los DOF restringidos (empotrado)",
    RestraintType.PINNED: "Traslaciones restringidas, rotaciones libres",
    RestraintType.ROLLER_X: "Libre en X, fijo en Y/Z",
    RestraintType.ROLLER_Y: "Libre en Y, fijo en X/Z",
    RestraintType.ROLLER_Z: "Libre en Z, fijo en X/Y",
    RestraintType.VERTICAL_ONLY: "Solo Uz restringido",
    RestraintType.CUSTOM: "Configuración manual por DOF",
}

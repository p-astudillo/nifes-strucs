"""
Frame element model for structural analysis.

Represents a 1D element (beam, column, brace) connecting two nodes
with assigned material and section properties.
"""

from dataclasses import dataclass, field
from math import sqrt
from typing import Any

from paz.core.exceptions import FrameError, ValidationError
from paz.domain.model.local_axes import LocalAxes, calculate_local_axes
from paz.domain.model.node import Node


@dataclass(frozen=True)
class FrameReleases:
    """
    End releases for a frame element.

    Each boolean indicates if the corresponding DOF is released (True)
    or fixed (False) at that end of the frame.

    Attributes (for each end i and j):
        P: Axial force release (translation along axis 1)
        V2: Shear force release in axis 2 direction
        V3: Shear force release in axis 3 direction
        T: Torsion release (rotation about axis 1)
        M2: Moment release about axis 2 (bending in 1-3 plane)
        M3: Moment release about axis 3 (bending in 1-2 plane)

    Common configurations:
        - Pinned end: M2=True, M3=True (releases both bending moments)
        - Roller: P=True, M2=True, M3=True
        - Fixed: all False (default)
    """

    # End i releases
    P_i: bool = False
    V2_i: bool = False
    V3_i: bool = False
    T_i: bool = False
    M2_i: bool = False
    M3_i: bool = False

    # End j releases
    P_j: bool = False
    V2_j: bool = False
    V3_j: bool = False
    T_j: bool = False
    M2_j: bool = False
    M3_j: bool = False

    @classmethod
    def fixed_fixed(cls) -> "FrameReleases":
        """Create fixed-fixed releases (default, no releases)."""
        return cls()

    @classmethod
    def pinned_pinned(cls) -> "FrameReleases":
        """Create pinned-pinned releases (moment releases at both ends)."""
        return cls(M2_i=True, M3_i=True, M2_j=True, M3_j=True)

    @classmethod
    def fixed_pinned(cls) -> "FrameReleases":
        """Create fixed-pinned releases (moment release at end j only)."""
        return cls(M2_j=True, M3_j=True)

    @classmethod
    def pinned_fixed(cls) -> "FrameReleases":
        """Create pinned-fixed releases (moment release at end i only)."""
        return cls(M2_i=True, M3_i=True)

    def is_fully_fixed(self) -> bool:
        """Check if all DOFs are fixed (no releases)."""
        return not any([
            self.P_i, self.V2_i, self.V3_i, self.T_i, self.M2_i, self.M3_i,
            self.P_j, self.V2_j, self.V3_j, self.T_j, self.M2_j, self.M3_j,
        ])

    def to_dict(self) -> dict[str, bool]:
        """Serialize to dictionary."""
        return {
            "P_i": self.P_i, "V2_i": self.V2_i, "V3_i": self.V3_i,
            "T_i": self.T_i, "M2_i": self.M2_i, "M3_i": self.M3_i,
            "P_j": self.P_j, "V2_j": self.V2_j, "V3_j": self.V3_j,
            "T_j": self.T_j, "M2_j": self.M2_j, "M3_j": self.M3_j,
        }

    @classmethod
    def from_dict(cls, data: dict[str, bool]) -> "FrameReleases":
        """Create from dictionary."""
        return cls(
            P_i=data.get("P_i", False),
            V2_i=data.get("V2_i", False),
            V3_i=data.get("V3_i", False),
            T_i=data.get("T_i", False),
            M2_i=data.get("M2_i", False),
            M3_i=data.get("M3_i", False),
            P_j=data.get("P_j", False),
            V2_j=data.get("V2_j", False),
            V3_j=data.get("V3_j", False),
            T_j=data.get("T_j", False),
            M2_j=data.get("M2_j", False),
            M3_j=data.get("M3_j", False),
        )


@dataclass
class Frame:
    """
    A frame element connecting two nodes.

    Represents beams, columns, braces, and other 1D elements in the
    structural model. Each frame has:
    - Start node (i) and end node (j)
    - Material properties (referenced by name)
    - Section properties (referenced by name)
    - Local axis rotation
    - End releases

    Attributes:
        id: Unique identifier for this frame
        node_i_id: ID of start node
        node_j_id: ID of end node
        material_name: Name of assigned material
        section_name: Name of assigned section
        rotation: Rotation angle in radians about the element axis
        releases: End releases configuration
        label: Optional user-defined label
    """

    node_i_id: int
    node_j_id: int
    material_name: str
    section_name: str
    id: int = field(default=-1)
    rotation: float = 0.0
    releases: FrameReleases = field(default_factory=FrameReleases)
    label: str = ""

    # Cached node references (not serialized)
    _node_i: Node | None = field(default=None, repr=False, compare=False)
    _node_j: Node | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Validate frame properties."""
        self._validate()

    def _validate(self) -> None:
        """Validate frame properties."""
        if self.node_i_id == self.node_j_id:
            raise ValidationError(
                f"Frame cannot connect a node to itself (node_id={self.node_i_id})",
                field="node_j_id",
            )

        if not self.material_name:
            raise ValidationError(
                "Frame must have a material assigned",
                field="material_name",
            )

        if not self.section_name:
            raise ValidationError(
                "Frame must have a section assigned",
                field="section_name",
            )

    def set_nodes(self, node_i: Node, node_j: Node) -> None:
        """
        Set node references for length and local axes calculations.

        Args:
            node_i: Start node
            node_j: End node

        Raises:
            FrameError: If node IDs don't match
        """
        if node_i.id != self.node_i_id:
            raise FrameError(
                f"Node i ID mismatch: expected {self.node_i_id}, got {node_i.id}",
                frame_id=self.id,
            )
        if node_j.id != self.node_j_id:
            raise FrameError(
                f"Node j ID mismatch: expected {self.node_j_id}, got {node_j.id}",
                frame_id=self.id,
            )

        object.__setattr__(self, "_node_i", node_i)
        object.__setattr__(self, "_node_j", node_j)

    def _ensure_nodes(self) -> tuple[Node, Node]:
        """Ensure nodes are set and return them."""
        if self._node_i is None or self._node_j is None:
            raise FrameError(
                "Node references not set. Call set_nodes() first.",
                frame_id=self.id,
            )
        return self._node_i, self._node_j

    def length(self) -> float:
        """
        Calculate element length.

        Returns:
            Length in meters

        Raises:
            FrameError: If nodes not set
        """
        node_i, node_j = self._ensure_nodes()
        dx = node_j.x - node_i.x
        dy = node_j.y - node_i.y
        dz = node_j.z - node_i.z
        return sqrt(dx * dx + dy * dy + dz * dz)

    def local_axes(self) -> LocalAxes:
        """
        Calculate local coordinate system for this frame.

        Returns:
            LocalAxes object with axis1, axis2, axis3 unit vectors

        Raises:
            FrameError: If nodes not set
        """
        node_i, node_j = self._ensure_nodes()
        return calculate_local_axes(node_i, node_j, self.rotation)

    def midpoint(self) -> tuple[float, float, float]:
        """
        Calculate midpoint of the frame.

        Returns:
            (x, y, z) coordinates of midpoint

        Raises:
            FrameError: If nodes not set
        """
        node_i, node_j = self._ensure_nodes()
        return (
            (node_i.x + node_j.x) / 2,
            (node_i.y + node_j.y) / 2,
            (node_i.z + node_j.z) / 2,
        )

    def direction_vector(self) -> tuple[float, float, float]:
        """
        Get unit direction vector from node i to node j.

        Returns:
            (dx, dy, dz) unit vector

        Raises:
            FrameError: If nodes not set
        """
        node_i, node_j = self._ensure_nodes()
        dx = node_j.x - node_i.x
        dy = node_j.y - node_i.y
        dz = node_j.z - node_i.z
        length = sqrt(dx * dx + dy * dy + dz * dz)
        if length < 1e-9:
            return (0.0, 0.0, 0.0)
        return (dx / length, dy / length, dz / length)

    def point_at(self, t: float) -> tuple[float, float, float]:
        """
        Get point along frame at parameter t.

        Args:
            t: Parameter from 0 (node i) to 1 (node j)

        Returns:
            (x, y, z) coordinates

        Raises:
            FrameError: If nodes not set
        """
        node_i, node_j = self._ensure_nodes()
        return (
            node_i.x + t * (node_j.x - node_i.x),
            node_i.y + t * (node_j.y - node_i.y),
            node_i.z + t * (node_j.z - node_i.z),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "node_i_id": self.node_i_id,
            "node_j_id": self.node_j_id,
            "material_name": self.material_name,
            "section_name": self.section_name,
            "rotation": self.rotation,
            "releases": self.releases.to_dict(),
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Frame":
        """Create from dictionary."""
        releases_data = data.get("releases", {})
        releases = FrameReleases.from_dict(releases_data) if releases_data else FrameReleases()

        return cls(
            id=data.get("id", -1),
            node_i_id=data["node_i_id"],
            node_j_id=data["node_j_id"],
            material_name=data["material_name"],
            section_name=data["section_name"],
            rotation=data.get("rotation", 0.0),
            releases=releases,
            label=data.get("label", ""),
        )


# Minimum frame length in meters
MIN_FRAME_LENGTH = 0.01


def validate_frame_length(node_i: Node, node_j: Node) -> float:
    """
    Validate that frame length is above minimum.

    Args:
        node_i: Start node
        node_j: End node

    Returns:
        Frame length

    Raises:
        ValidationError: If length is below minimum
    """
    dx = node_j.x - node_i.x
    dy = node_j.y - node_i.y
    dz = node_j.z - node_i.z
    length = sqrt(dx * dx + dy * dy + dz * dz)

    if length < MIN_FRAME_LENGTH:
        raise ValidationError(
            f"Frame length ({length:.6f}m) is below minimum ({MIN_FRAME_LENGTH}m)",
            field="length",
            node_i_id=node_i.id,
            node_j_id=node_j.id,
        )

    return length

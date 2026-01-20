"""
Element group model for structural analysis.

Represents a logical grouping of nodes, frames, and shells
for bulk operations like assigning materials, sections, or loads.
"""

from dataclasses import dataclass, field
from typing import Any

from paz.core.exceptions import ValidationError


@dataclass
class ElementGroup:
    """
    A logical grouping of structural elements.

    Groups allow users to:
    - Select multiple elements at once
    - Apply properties to all elements in the group
    - Organize the model hierarchically

    Attributes:
        id: Unique identifier for this group
        name: User-defined name for the group
        node_ids: Set of node IDs in this group
        frame_ids: Set of frame IDs in this group
        shell_ids: Set of shell IDs in this group
        color: Optional color for visualization (hex string)
        parent_id: ID of parent group (for hierarchy), None if top-level
        description: Optional description
    """

    name: str
    node_ids: set[int] = field(default_factory=set)
    frame_ids: set[int] = field(default_factory=set)
    shell_ids: set[int] = field(default_factory=set)
    id: int = field(default=-1)
    color: str = "#808080"  # Default gray
    parent_id: int | None = None
    description: str = ""

    def __post_init__(self) -> None:
        """Validate group properties."""
        self._validate()
        # Convert lists to sets if needed
        if isinstance(self.node_ids, list):
            object.__setattr__(self, "node_ids", set(self.node_ids))
        if isinstance(self.frame_ids, list):
            object.__setattr__(self, "frame_ids", set(self.frame_ids))
        if isinstance(self.shell_ids, list):
            object.__setattr__(self, "shell_ids", set(self.shell_ids))

    def _validate(self) -> None:
        """Validate group properties."""
        if not self.name or not self.name.strip():
            raise ValidationError(
                "Group must have a non-empty name",
                field="name",
            )

        if self.color and not self.color.startswith("#"):
            raise ValidationError(
                f"Color must be a hex string starting with #, got '{self.color}'",
                field="color",
            )

    @property
    def is_empty(self) -> bool:
        """Check if group contains no elements."""
        return not self.node_ids and not self.frame_ids and not self.shell_ids

    @property
    def element_count(self) -> int:
        """Total number of elements in the group."""
        return len(self.node_ids) + len(self.frame_ids) + len(self.shell_ids)

    @property
    def has_nodes(self) -> bool:
        """Check if group contains nodes."""
        return len(self.node_ids) > 0

    @property
    def has_frames(self) -> bool:
        """Check if group contains frames."""
        return len(self.frame_ids) > 0

    @property
    def has_shells(self) -> bool:
        """Check if group contains shells."""
        return len(self.shell_ids) > 0

    def add_node(self, node_id: int) -> None:
        """Add a node to the group."""
        self.node_ids.add(node_id)

    def add_nodes(self, node_ids: list[int]) -> None:
        """Add multiple nodes to the group."""
        self.node_ids.update(node_ids)

    def remove_node(self, node_id: int) -> None:
        """Remove a node from the group."""
        self.node_ids.discard(node_id)

    def add_frame(self, frame_id: int) -> None:
        """Add a frame to the group."""
        self.frame_ids.add(frame_id)

    def add_frames(self, frame_ids: list[int]) -> None:
        """Add multiple frames to the group."""
        self.frame_ids.update(frame_ids)

    def remove_frame(self, frame_id: int) -> None:
        """Remove a frame from the group."""
        self.frame_ids.discard(frame_id)

    def add_shell(self, shell_id: int) -> None:
        """Add a shell to the group."""
        self.shell_ids.add(shell_id)

    def add_shells(self, shell_ids: list[int]) -> None:
        """Add multiple shells to the group."""
        self.shell_ids.update(shell_ids)

    def remove_shell(self, shell_id: int) -> None:
        """Remove a shell from the group."""
        self.shell_ids.discard(shell_id)

    def clear(self) -> None:
        """Remove all elements from the group."""
        self.node_ids.clear()
        self.frame_ids.clear()
        self.shell_ids.clear()

    def contains_node(self, node_id: int) -> bool:
        """Check if a node is in this group."""
        return node_id in self.node_ids

    def contains_frame(self, frame_id: int) -> bool:
        """Check if a frame is in this group."""
        return frame_id in self.frame_ids

    def contains_shell(self, shell_id: int) -> bool:
        """Check if a shell is in this group."""
        return shell_id in self.shell_ids

    def merge_with(self, other: "ElementGroup") -> None:
        """
        Merge another group's elements into this group.

        Args:
            other: Group to merge from
        """
        self.node_ids.update(other.node_ids)
        self.frame_ids.update(other.frame_ids)
        self.shell_ids.update(other.shell_ids)

    def intersection_with(self, other: "ElementGroup") -> "ElementGroup":
        """
        Create a new group with elements common to both groups.

        Args:
            other: Group to intersect with

        Returns:
            New group with common elements
        """
        return ElementGroup(
            name=f"{self.name} & {other.name}",
            node_ids=self.node_ids & other.node_ids,
            frame_ids=self.frame_ids & other.frame_ids,
            shell_ids=self.shell_ids & other.shell_ids,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "node_ids": sorted(self.node_ids),
            "frame_ids": sorted(self.frame_ids),
            "shell_ids": sorted(self.shell_ids),
            "color": self.color,
            "parent_id": self.parent_id,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ElementGroup":
        """Create from dictionary."""
        return cls(
            id=data.get("id", -1),
            name=data["name"],
            node_ids=set(data.get("node_ids", [])),
            frame_ids=set(data.get("frame_ids", [])),
            shell_ids=set(data.get("shell_ids", [])),
            color=data.get("color", "#808080"),
            parent_id=data.get("parent_id"),
            description=data.get("description", ""),
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ElementGroup(id={self.id}, name='{self.name}', "
            f"nodes={len(self.node_ids)}, frames={len(self.frame_ids)}, "
            f"shells={len(self.shell_ids)})"
        )

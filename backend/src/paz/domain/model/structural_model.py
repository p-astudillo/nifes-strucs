"""
Structural model containing all elements of a structure.

The StructuralModel is the central container for nodes, frames, materials,
sections, and other structural components.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from paz.core.constants import MAX_NODES, NODE_DUPLICATE_TOLERANCE
from paz.core.exceptions import (
    DuplicateNodeError,
    FrameError,
    NodeError,
    ValidationError,
)
from paz.domain.model.frame import Frame, FrameReleases, validate_frame_length
from paz.domain.model.node import Node
from paz.domain.model.restraint import Restraint


# Maximum number of frames in a model
MAX_FRAMES = 100000


@dataclass
class StructuralModel:
    """
    Container for all structural model data.

    Manages nodes, frames, and provides validation and queries.
    """

    _nodes: dict[int, Node] = field(default_factory=dict)
    _next_node_id: int = 1
    _frames: dict[int, Frame] = field(default_factory=dict)
    _next_frame_id: int = 1

    # Node operations

    @property
    def nodes(self) -> list[Node]:
        """Get all nodes as a list."""
        return list(self._nodes.values())

    @property
    def node_count(self) -> int:
        """Get the number of nodes."""
        return len(self._nodes)

    def get_node(self, node_id: int) -> Node:
        """
        Get a node by ID.

        Args:
            node_id: The node ID

        Returns:
            The node

        Raises:
            NodeError: If node doesn't exist
        """
        if node_id not in self._nodes:
            raise NodeError(f"Node {node_id} not found", node_id=node_id)
        return self._nodes[node_id]

    def has_node(self, node_id: int) -> bool:
        """Check if a node exists."""
        return node_id in self._nodes

    def add_node(
        self,
        x: float,
        y: float,
        z: float,
        restraint: Restraint | None = None,
        node_id: int | None = None,
        check_duplicate: bool = True,
    ) -> Node:
        """
        Add a new node to the model.

        Args:
            x: X coordinate
            y: Y coordinate
            z: Z coordinate
            restraint: Optional boundary conditions
            node_id: Optional specific ID (auto-generated if None)
            check_duplicate: Whether to check for duplicate nodes

        Returns:
            The created node

        Raises:
            ValidationError: If max nodes exceeded
            DuplicateNodeError: If a node exists at the same location
        """
        # Check limit
        if self.node_count >= MAX_NODES:
            raise ValidationError(
                f"Maximum number of nodes ({MAX_NODES}) exceeded",
                field="nodes",
            )

        # Check for duplicate
        if check_duplicate:
            existing = self.find_node_at(x, y, z)
            if existing is not None:
                raise DuplicateNodeError(x, y, z, existing.id)

        # Determine ID
        if node_id is None:
            node_id = self._next_node_id
            self._next_node_id += 1
        else:
            if node_id in self._nodes:
                raise NodeError(f"Node ID {node_id} already exists", node_id=node_id)
            if node_id >= self._next_node_id:
                self._next_node_id = node_id + 1

        # Create and add node
        from paz.domain.model.restraint import FREE

        node = Node(
            id=node_id,
            x=x,
            y=y,
            z=z,
            restraint=restraint if restraint is not None else FREE,
        )
        self._nodes[node_id] = node

        return node

    def remove_node(self, node_id: int) -> Node:
        """
        Remove a node from the model.

        Args:
            node_id: ID of node to remove

        Returns:
            The removed node

        Raises:
            NodeError: If node doesn't exist
        """
        if node_id not in self._nodes:
            raise NodeError(f"Node {node_id} not found", node_id=node_id)

        # Check if node is used by any frames
        frames_using_node = self.get_frames_using_node(node_id)
        if frames_using_node:
            frame_ids = [f.id for f in frames_using_node]
            raise NodeError(
                f"Cannot remove node {node_id}: used by frames {frame_ids}",
                node_id=node_id,
            )

        return self._nodes.pop(node_id)

    def update_node(
        self,
        node_id: int,
        x: float | None = None,
        y: float | None = None,
        z: float | None = None,
        restraint: Restraint | None = None,
    ) -> Node:
        """
        Update node properties.

        Args:
            node_id: ID of node to update
            x: New X coordinate (None to keep current)
            y: New Y coordinate (None to keep current)
            z: New Z coordinate (None to keep current)
            restraint: New restraint (None to keep current)

        Returns:
            The updated node

        Raises:
            NodeError: If node doesn't exist
        """
        node = self.get_node(node_id)

        if x is not None:
            node.x = x
        if y is not None:
            node.y = y
        if z is not None:
            node.z = z
        if restraint is not None:
            node.restraint = restraint

        return node

    def find_node_at(
        self,
        x: float,
        y: float,
        z: float,
        tolerance: float = NODE_DUPLICATE_TOLERANCE,
    ) -> Node | None:
        """
        Find a node at the given coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            z: Z coordinate
            tolerance: Distance tolerance for matching

        Returns:
            Node at location, or None if not found
        """
        for node in self._nodes.values():
            if node.distance_to_point(x, y, z) <= tolerance:
                return node
        return None

    def find_nodes_in_box(
        self,
        x_min: float,
        y_min: float,
        z_min: float,
        x_max: float,
        y_max: float,
        z_max: float,
    ) -> list[Node]:
        """
        Find all nodes within a bounding box.

        Args:
            x_min, y_min, z_min: Minimum coordinates
            x_max, y_max, z_max: Maximum coordinates

        Returns:
            List of nodes within the box
        """
        return [
            node
            for node in self._nodes.values()
            if x_min <= node.x <= x_max
            and y_min <= node.y <= y_max
            and z_min <= node.z <= z_max
        ]

    def get_supported_nodes(self) -> list[Node]:
        """Get all nodes with restraints."""
        return [node for node in self._nodes.values() if node.is_supported]

    def iter_nodes(self) -> Iterator[Node]:
        """Iterate over all nodes."""
        return iter(self._nodes.values())

    # Frame operations

    @property
    def frames(self) -> list[Frame]:
        """Get all frames as a list."""
        return list(self._frames.values())

    @property
    def frame_count(self) -> int:
        """Get the number of frames."""
        return len(self._frames)

    def get_frame(self, frame_id: int) -> Frame:
        """
        Get a frame by ID.

        Args:
            frame_id: The frame ID

        Returns:
            The frame

        Raises:
            FrameError: If frame doesn't exist
        """
        if frame_id not in self._frames:
            raise FrameError(f"Frame {frame_id} not found", frame_id=frame_id)
        return self._frames[frame_id]

    def has_frame(self, frame_id: int) -> bool:
        """Check if a frame exists."""
        return frame_id in self._frames

    def add_frame(
        self,
        node_i_id: int,
        node_j_id: int,
        material_name: str,
        section_name: str,
        rotation: float = 0.0,
        releases: FrameReleases | None = None,
        frame_id: int | None = None,
        label: str = "",
    ) -> Frame:
        """
        Add a new frame to the model.

        Args:
            node_i_id: ID of start node
            node_j_id: ID of end node
            material_name: Name of material
            section_name: Name of section
            rotation: Rotation angle in radians
            releases: End releases (default: fixed-fixed)
            frame_id: Optional specific ID (auto-generated if None)
            label: Optional user label

        Returns:
            The created frame

        Raises:
            ValidationError: If max frames exceeded or invalid parameters
            NodeError: If nodes don't exist
            FrameError: If frame is too short or already exists
        """
        # Check limit
        if self.frame_count >= MAX_FRAMES:
            raise ValidationError(
                f"Maximum number of frames ({MAX_FRAMES}) exceeded",
                field="frames",
            )

        # Validate nodes exist
        node_i = self.get_node(node_i_id)
        node_j = self.get_node(node_j_id)

        # Validate length
        validate_frame_length(node_i, node_j)

        # Check for duplicate frame
        existing = self.find_frame_between(node_i_id, node_j_id)
        if existing is not None:
            raise FrameError(
                f"Frame already exists between nodes {node_i_id} and {node_j_id}",
                frame_id=existing.id,
            )

        # Determine ID
        if frame_id is None:
            frame_id = self._next_frame_id
            self._next_frame_id += 1
        else:
            if frame_id in self._frames:
                raise FrameError(f"Frame ID {frame_id} already exists", frame_id=frame_id)
            if frame_id >= self._next_frame_id:
                self._next_frame_id = frame_id + 1

        # Create frame
        frame = Frame(
            id=frame_id,
            node_i_id=node_i_id,
            node_j_id=node_j_id,
            material_name=material_name,
            section_name=section_name,
            rotation=rotation,
            releases=releases if releases is not None else FrameReleases(),
            label=label,
        )

        # Set node references for length/axes calculations
        frame.set_nodes(node_i, node_j)

        self._frames[frame_id] = frame
        return frame

    def remove_frame(self, frame_id: int) -> Frame:
        """
        Remove a frame from the model.

        Args:
            frame_id: ID of frame to remove

        Returns:
            The removed frame

        Raises:
            FrameError: If frame doesn't exist
        """
        if frame_id not in self._frames:
            raise FrameError(f"Frame {frame_id} not found", frame_id=frame_id)
        return self._frames.pop(frame_id)

    def update_frame(
        self,
        frame_id: int,
        material_name: str | None = None,
        section_name: str | None = None,
        rotation: float | None = None,
        releases: FrameReleases | None = None,
        label: str | None = None,
    ) -> Frame:
        """
        Update frame properties.

        Note: Node assignments cannot be changed. Delete and recreate if needed.

        Args:
            frame_id: ID of frame to update
            material_name: New material (None to keep current)
            section_name: New section (None to keep current)
            rotation: New rotation (None to keep current)
            releases: New releases (None to keep current)
            label: New label (None to keep current)

        Returns:
            The updated frame

        Raises:
            FrameError: If frame doesn't exist
        """
        frame = self.get_frame(frame_id)

        if material_name is not None:
            frame.material_name = material_name
        if section_name is not None:
            frame.section_name = section_name
        if rotation is not None:
            frame.rotation = rotation
        if releases is not None:
            frame.releases = releases
        if label is not None:
            frame.label = label

        return frame

    def find_frame_between(self, node_i_id: int, node_j_id: int) -> Frame | None:
        """
        Find a frame connecting two nodes (in either direction).

        Args:
            node_i_id: First node ID
            node_j_id: Second node ID

        Returns:
            Frame if found, None otherwise
        """
        for frame in self._frames.values():
            if (frame.node_i_id == node_i_id and frame.node_j_id == node_j_id) or \
               (frame.node_i_id == node_j_id and frame.node_j_id == node_i_id):
                return frame
        return None

    def get_frames_using_node(self, node_id: int) -> list[Frame]:
        """
        Get all frames connected to a node.

        Args:
            node_id: Node ID

        Returns:
            List of frames using this node
        """
        return [
            frame for frame in self._frames.values()
            if frame.node_i_id == node_id or frame.node_j_id == node_id
        ]

    def get_frames_with_material(self, material_name: str) -> list[Frame]:
        """Get all frames using a specific material."""
        return [f for f in self._frames.values() if f.material_name == material_name]

    def get_frames_with_section(self, section_name: str) -> list[Frame]:
        """Get all frames using a specific section."""
        return [f for f in self._frames.values() if f.section_name == section_name]

    def iter_frames(self) -> Iterator[Frame]:
        """Iterate over all frames."""
        return iter(self._frames.values())

    def _refresh_frame_nodes(self) -> None:
        """Refresh node references for all frames after deserialization."""
        for frame in self._frames.values():
            node_i = self._nodes.get(frame.node_i_id)
            node_j = self._nodes.get(frame.node_j_id)
            if node_i is not None and node_j is not None:
                frame.set_nodes(node_i, node_j)

    # Serialization

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "nodes": [node.to_dict() for node in self._nodes.values()],
            "next_node_id": self._next_node_id,
            "frames": [frame.to_dict() for frame in self._frames.values()],
            "next_frame_id": self._next_frame_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StructuralModel":
        """Create from dictionary."""
        model = cls()

        # Load nodes first
        for node_data in data.get("nodes", []):
            node = Node.from_dict(node_data)
            model._nodes[node.id] = node

        model._next_node_id = data.get("next_node_id", 1)
        if model._nodes:
            max_id = max(model._nodes.keys())
            if model._next_node_id <= max_id:
                model._next_node_id = max_id + 1

        # Load frames
        for frame_data in data.get("frames", []):
            frame = Frame.from_dict(frame_data)
            model._frames[frame.id] = frame

        model._next_frame_id = data.get("next_frame_id", 1)
        if model._frames:
            max_id = max(model._frames.keys())
            if model._next_frame_id <= max_id:
                model._next_frame_id = max_id + 1

        # Refresh node references for frames
        model._refresh_frame_nodes()

        return model

    def clear(self) -> None:
        """Remove all nodes, frames and reset."""
        self._frames.clear()
        self._next_frame_id = 1
        self._nodes.clear()
        self._next_node_id = 1

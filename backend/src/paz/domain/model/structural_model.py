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
    GroupError,
    NodeError,
    ShellError,
    ValidationError,
)
from paz.domain.model.element_group import ElementGroup
from paz.domain.model.frame import Frame, FrameReleases, validate_frame_length
from paz.domain.model.node import Node
from paz.domain.model.restraint import Restraint
from paz.domain.model.shell import Shell, ShellType, validate_shell_area


# Maximum number of elements in a model
MAX_FRAMES = 100000
MAX_SHELLS = 100000
MAX_GROUPS = 10000


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
    _shells: dict[int, Shell] = field(default_factory=dict)
    _next_shell_id: int = 1
    _groups: dict[int, ElementGroup] = field(default_factory=dict)
    _next_group_id: int = 1

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

        # Check if node is used by any shells
        shells_using_node = self.get_shells_using_node(node_id)
        if shells_using_node:
            shell_ids = [s.id for s in shells_using_node]
            raise NodeError(
                f"Cannot remove node {node_id}: used by shells {shell_ids}",
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

    # Shell operations

    @property
    def shells(self) -> list[Shell]:
        """Get all shells as a list."""
        return list(self._shells.values())

    @property
    def shell_count(self) -> int:
        """Get the number of shells."""
        return len(self._shells)

    def get_shell(self, shell_id: int) -> Shell:
        """
        Get a shell by ID.

        Args:
            shell_id: The shell ID

        Returns:
            The shell

        Raises:
            ShellError: If shell doesn't exist
        """
        if shell_id not in self._shells:
            raise ShellError(f"Shell {shell_id} not found", shell_id=shell_id)
        return self._shells[shell_id]

    def has_shell(self, shell_id: int) -> bool:
        """Check if a shell exists."""
        return shell_id in self._shells

    def add_shell(
        self,
        node_ids: list[int],
        material_name: str,
        thickness: float,
        shell_type: ShellType = ShellType.SHELL,
        shell_id: int | None = None,
        label: str = "",
    ) -> Shell:
        """
        Add a new shell to the model.

        Args:
            node_ids: List of 3 or 4 node IDs
            material_name: Name of material
            thickness: Shell thickness in meters
            shell_type: Type of shell formulation
            shell_id: Optional specific ID (auto-generated if None)
            label: Optional user label

        Returns:
            The created shell

        Raises:
            ValidationError: If max shells exceeded or invalid parameters
            NodeError: If nodes don't exist
            ShellError: If shell already exists or area too small
        """
        # Check limit
        if self.shell_count >= MAX_SHELLS:
            raise ValidationError(
                f"Maximum number of shells ({MAX_SHELLS}) exceeded",
                field="shells",
            )

        # Validate nodes exist
        shell_nodes = []
        for nid in node_ids:
            node = self.get_node(nid)
            shell_nodes.append(node)

        # Validate area
        validate_shell_area(shell_nodes)

        # Determine ID
        if shell_id is None:
            shell_id = self._next_shell_id
            self._next_shell_id += 1
        else:
            if shell_id in self._shells:
                raise ShellError(f"Shell ID {shell_id} already exists", shell_id=shell_id)
            if shell_id >= self._next_shell_id:
                self._next_shell_id = shell_id + 1

        # Create shell
        shell = Shell(
            id=shell_id,
            node_ids=node_ids,
            material_name=material_name,
            thickness=thickness,
            shell_type=shell_type,
            label=label,
        )

        # Set node references for area/centroid calculations
        shell.set_nodes(shell_nodes)

        self._shells[shell_id] = shell
        return shell

    def remove_shell(self, shell_id: int) -> Shell:
        """
        Remove a shell from the model.

        Args:
            shell_id: ID of shell to remove

        Returns:
            The removed shell

        Raises:
            ShellError: If shell doesn't exist
        """
        if shell_id not in self._shells:
            raise ShellError(f"Shell {shell_id} not found", shell_id=shell_id)
        return self._shells.pop(shell_id)

    def update_shell(
        self,
        shell_id: int,
        material_name: str | None = None,
        thickness: float | None = None,
        shell_type: ShellType | None = None,
        label: str | None = None,
    ) -> Shell:
        """
        Update shell properties.

        Note: Node assignments cannot be changed. Delete and recreate if needed.

        Args:
            shell_id: ID of shell to update
            material_name: New material (None to keep current)
            thickness: New thickness (None to keep current)
            shell_type: New shell type (None to keep current)
            label: New label (None to keep current)

        Returns:
            The updated shell

        Raises:
            ShellError: If shell doesn't exist
        """
        shell = self.get_shell(shell_id)

        if material_name is not None:
            shell.material_name = material_name
        if thickness is not None:
            if thickness <= 0:
                raise ValidationError(
                    f"Shell thickness must be positive, got {thickness}",
                    field="thickness",
                )
            shell.thickness = thickness
        if shell_type is not None:
            shell.shell_type = shell_type
        if label is not None:
            shell.label = label

        return shell

    def get_shells_using_node(self, node_id: int) -> list[Shell]:
        """
        Get all shells connected to a node.

        Args:
            node_id: Node ID

        Returns:
            List of shells using this node
        """
        return [
            shell for shell in self._shells.values()
            if node_id in shell.node_ids
        ]

    def get_shells_with_material(self, material_name: str) -> list[Shell]:
        """Get all shells using a specific material."""
        return [s for s in self._shells.values() if s.material_name == material_name]

    def iter_shells(self) -> Iterator[Shell]:
        """Iterate over all shells."""
        return iter(self._shells.values())

    def _refresh_shell_nodes(self) -> None:
        """Refresh node references for all shells after deserialization."""
        for shell in self._shells.values():
            shell_nodes = []
            for nid in shell.node_ids:
                node = self._nodes.get(nid)
                if node is not None:
                    shell_nodes.append(node)
            if len(shell_nodes) == len(shell.node_ids):
                shell.set_nodes(shell_nodes)

    # Group operations

    @property
    def groups(self) -> list[ElementGroup]:
        """Get all groups as a list."""
        return list(self._groups.values())

    @property
    def group_count(self) -> int:
        """Get the number of groups."""
        return len(self._groups)

    def get_group(self, group_id: int) -> ElementGroup:
        """
        Get a group by ID.

        Args:
            group_id: The group ID

        Returns:
            The group

        Raises:
            GroupError: If group doesn't exist
        """
        if group_id not in self._groups:
            raise GroupError(f"Group {group_id} not found", group_id=group_id)
        return self._groups[group_id]

    def has_group(self, group_id: int) -> bool:
        """Check if a group exists."""
        return group_id in self._groups

    def add_group(
        self,
        name: str,
        node_ids: list[int] | None = None,
        frame_ids: list[int] | None = None,
        shell_ids: list[int] | None = None,
        color: str = "#808080",
        parent_id: int | None = None,
        description: str = "",
        group_id: int | None = None,
    ) -> ElementGroup:
        """
        Add a new group to the model.

        Args:
            name: Group name
            node_ids: Optional list of node IDs to include
            frame_ids: Optional list of frame IDs to include
            shell_ids: Optional list of shell IDs to include
            color: Optional color for visualization
            parent_id: Optional parent group ID
            description: Optional description
            group_id: Optional specific ID (auto-generated if None)

        Returns:
            The created group

        Raises:
            ValidationError: If max groups exceeded or invalid parameters
            GroupError: If group ID already exists or parent doesn't exist
        """
        # Check limit
        if self.group_count >= MAX_GROUPS:
            raise ValidationError(
                f"Maximum number of groups ({MAX_GROUPS}) exceeded",
                field="groups",
            )

        # Validate parent exists if specified
        if parent_id is not None and parent_id not in self._groups:
            raise GroupError(
                f"Parent group {parent_id} not found",
                group_id=parent_id,
            )

        # Validate referenced elements exist
        if node_ids:
            for nid in node_ids:
                if nid not in self._nodes:
                    raise NodeError(f"Node {nid} not found", node_id=nid)

        if frame_ids:
            for fid in frame_ids:
                if fid not in self._frames:
                    raise FrameError(f"Frame {fid} not found", frame_id=fid)

        if shell_ids:
            for sid in shell_ids:
                if sid not in self._shells:
                    raise ShellError(f"Shell {sid} not found", shell_id=sid)

        # Determine ID
        if group_id is None:
            group_id = self._next_group_id
            self._next_group_id += 1
        else:
            if group_id in self._groups:
                raise GroupError(f"Group ID {group_id} already exists", group_id=group_id)
            if group_id >= self._next_group_id:
                self._next_group_id = group_id + 1

        # Create group
        group = ElementGroup(
            id=group_id,
            name=name,
            node_ids=set(node_ids or []),
            frame_ids=set(frame_ids or []),
            shell_ids=set(shell_ids or []),
            color=color,
            parent_id=parent_id,
            description=description,
        )

        self._groups[group_id] = group
        return group

    def remove_group(self, group_id: int) -> ElementGroup:
        """
        Remove a group from the model.

        Note: This does NOT delete the elements in the group, only the group itself.

        Args:
            group_id: ID of group to remove

        Returns:
            The removed group

        Raises:
            GroupError: If group doesn't exist
        """
        if group_id not in self._groups:
            raise GroupError(f"Group {group_id} not found", group_id=group_id)

        # Update any child groups to have no parent
        for group in self._groups.values():
            if group.parent_id == group_id:
                group.parent_id = None

        return self._groups.pop(group_id)

    def update_group(
        self,
        group_id: int,
        name: str | None = None,
        node_ids: list[int] | None = None,
        frame_ids: list[int] | None = None,
        shell_ids: list[int] | None = None,
        color: str | None = None,
        parent_id: int | None = ...,  # Use ... to distinguish from None
        description: str | None = None,
    ) -> ElementGroup:
        """
        Update group properties.

        Args:
            group_id: ID of group to update
            name: New name (None to keep current)
            node_ids: New node IDs (None to keep current, use [] to clear)
            frame_ids: New frame IDs (None to keep current, use [] to clear)
            shell_ids: New shell IDs (None to keep current, use [] to clear)
            color: New color (None to keep current)
            parent_id: New parent (... to keep current, None to remove parent)
            description: New description (None to keep current)

        Returns:
            The updated group

        Raises:
            GroupError: If group doesn't exist or circular parent reference
        """
        group = self.get_group(group_id)

        if name is not None:
            group.name = name

        if node_ids is not None:
            # Validate nodes exist
            for nid in node_ids:
                if nid not in self._nodes:
                    raise NodeError(f"Node {nid} not found", node_id=nid)
            group.node_ids = set(node_ids)

        if frame_ids is not None:
            for fid in frame_ids:
                if fid not in self._frames:
                    raise FrameError(f"Frame {fid} not found", frame_id=fid)
            group.frame_ids = set(frame_ids)

        if shell_ids is not None:
            for sid in shell_ids:
                if sid not in self._shells:
                    raise ShellError(f"Shell {sid} not found", shell_id=sid)
            group.shell_ids = set(shell_ids)

        if color is not None:
            group.color = color

        if parent_id is not ...:
            # Check for circular reference
            if parent_id is not None:
                if parent_id not in self._groups:
                    raise GroupError(f"Parent group {parent_id} not found", group_id=parent_id)
                if parent_id == group_id:
                    raise GroupError("Group cannot be its own parent", group_id=group_id)
                # Check for circular reference in ancestry
                current = parent_id
                while current is not None:
                    parent_group = self._groups.get(current)
                    if parent_group is None:
                        break
                    if parent_group.parent_id == group_id:
                        raise GroupError("Circular group reference detected", group_id=group_id)
                    current = parent_group.parent_id
            group.parent_id = parent_id

        if description is not None:
            group.description = description

        return group

    def get_groups_containing_node(self, node_id: int) -> list[ElementGroup]:
        """Get all groups that contain a specific node."""
        return [g for g in self._groups.values() if node_id in g.node_ids]

    def get_groups_containing_frame(self, frame_id: int) -> list[ElementGroup]:
        """Get all groups that contain a specific frame."""
        return [g for g in self._groups.values() if frame_id in g.frame_ids]

    def get_groups_containing_shell(self, shell_id: int) -> list[ElementGroup]:
        """Get all groups that contain a specific shell."""
        return [g for g in self._groups.values() if shell_id in g.shell_ids]

    def get_child_groups(self, group_id: int) -> list[ElementGroup]:
        """Get all groups that have the specified group as their parent."""
        return [g for g in self._groups.values() if g.parent_id == group_id]

    def get_top_level_groups(self) -> list[ElementGroup]:
        """Get all groups that have no parent."""
        return [g for g in self._groups.values() if g.parent_id is None]

    def iter_groups(self) -> Iterator[ElementGroup]:
        """Iterate over all groups."""
        return iter(self._groups.values())

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
            "shells": [shell.to_dict() for shell in self._shells.values()],
            "next_shell_id": self._next_shell_id,
            "groups": [group.to_dict() for group in self._groups.values()],
            "next_group_id": self._next_group_id,
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

        # Load shells
        for shell_data in data.get("shells", []):
            shell = Shell.from_dict(shell_data)
            model._shells[shell.id] = shell

        model._next_shell_id = data.get("next_shell_id", 1)
        if model._shells:
            max_id = max(model._shells.keys())
            if model._next_shell_id <= max_id:
                model._next_shell_id = max_id + 1

        # Load groups
        for group_data in data.get("groups", []):
            group = ElementGroup.from_dict(group_data)
            model._groups[group.id] = group

        model._next_group_id = data.get("next_group_id", 1)
        if model._groups:
            max_id = max(model._groups.keys())
            if model._next_group_id <= max_id:
                model._next_group_id = max_id + 1

        # Refresh node references for frames and shells
        model._refresh_frame_nodes()
        model._refresh_shell_nodes()

        return model

    def clear(self) -> None:
        """Remove all nodes, frames, shells, groups and reset."""
        self._groups.clear()
        self._next_group_id = 1
        self._shells.clear()
        self._next_shell_id = 1
        self._frames.clear()
        self._next_frame_id = 1
        self._nodes.clear()
        self._next_node_id = 1

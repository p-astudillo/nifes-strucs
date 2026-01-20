"""
Shell element model for structural analysis.

Represents a 2D element (slab, wall, plate) connecting 3 or 4 nodes
with assigned material and thickness properties.
"""

from dataclasses import dataclass, field
from enum import Enum
from math import sqrt
from typing import Any, TYPE_CHECKING

from paz.core.exceptions import ValidationError
from paz.domain.model.node import Node

if TYPE_CHECKING:
    from paz.domain.materials import Material


class ShellType(str, Enum):
    """
    Shell element formulation type.

    PLATE: Bending only (out-of-plane) - for slabs
    MEMBRANE: In-plane only - for walls under in-plane loads
    SHELL: Combined bending and membrane - general purpose
    """
    PLATE = "plate"
    MEMBRANE = "membrane"
    SHELL = "shell"


@dataclass
class Shell:
    """
    A shell element connecting 3 or 4 nodes.

    Represents slabs, walls, and other 2D elements in the structural model.
    Each shell has:
    - 3 or 4 corner nodes (triangular or quadrilateral)
    - Material properties (referenced by name)
    - Thickness
    - Shell type (plate, membrane, or shell)

    Attributes:
        id: Unique identifier for this shell
        node_ids: List of 3 or 4 node IDs defining the shell corners
        material_name: Name of assigned material
        thickness: Shell thickness in meters
        shell_type: Type of shell formulation
        label: Optional user-defined label
    """

    node_ids: list[int]
    material_name: str
    thickness: float
    shell_type: ShellType = ShellType.SHELL
    id: int = field(default=-1)
    label: str = ""

    # Cached node references (not serialized)
    _nodes: list[Node] | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Validate shell properties."""
        self._validate()

    def _validate(self) -> None:
        """Validate shell properties."""
        # Validate number of nodes
        if len(self.node_ids) not in (3, 4):
            raise ValidationError(
                f"Shell must have 3 or 4 nodes, got {len(self.node_ids)}",
                field="node_ids",
            )

        # Validate unique nodes
        if len(set(self.node_ids)) != len(self.node_ids):
            raise ValidationError(
                "Shell cannot have duplicate nodes",
                field="node_ids",
            )

        # Validate material
        if not self.material_name:
            raise ValidationError(
                "Shell must have a material assigned",
                field="material_name",
            )

        # Validate thickness
        if self.thickness <= 0:
            raise ValidationError(
                f"Shell thickness must be positive, got {self.thickness}",
                field="thickness",
            )

    @property
    def num_nodes(self) -> int:
        """Number of nodes (3 or 4)."""
        return len(self.node_ids)

    @property
    def is_triangular(self) -> bool:
        """Check if shell is triangular (3 nodes)."""
        return len(self.node_ids) == 3

    @property
    def is_quadrilateral(self) -> bool:
        """Check if shell is quadrilateral (4 nodes)."""
        return len(self.node_ids) == 4

    def set_nodes(self, nodes: list[Node]) -> None:
        """
        Set node references for area and centroid calculations.

        Args:
            nodes: List of nodes matching node_ids

        Raises:
            ValidationError: If nodes don't match node_ids
        """
        if len(nodes) != len(self.node_ids):
            raise ValidationError(
                f"Expected {len(self.node_ids)} nodes, got {len(nodes)}",
                field="nodes",
            )

        node_dict = {n.id: n for n in nodes}
        ordered_nodes = []
        for nid in self.node_ids:
            if nid not in node_dict:
                raise ValidationError(
                    f"Node {nid} not found in provided nodes",
                    field="nodes",
                )
            ordered_nodes.append(node_dict[nid])

        object.__setattr__(self, "_nodes", ordered_nodes)

    def _ensure_nodes(self) -> list[Node]:
        """Ensure nodes are set and return them."""
        if self._nodes is None:
            raise ValidationError(
                "Node references not set. Call set_nodes() first.",
                field="nodes",
            )
        return self._nodes

    def area(self) -> float:
        """
        Calculate shell area.

        Uses the cross product method for both triangles and quads.
        For quads, splits into two triangles.

        Returns:
            Area in square meters

        Raises:
            ValidationError: If nodes not set
        """
        nodes = self._ensure_nodes()

        if self.is_triangular:
            return self._triangle_area(nodes[0], nodes[1], nodes[2])
        else:
            # Split quad into two triangles
            area1 = self._triangle_area(nodes[0], nodes[1], nodes[2])
            area2 = self._triangle_area(nodes[0], nodes[2], nodes[3])
            return area1 + area2

    def _triangle_area(self, n1: Node, n2: Node, n3: Node) -> float:
        """Calculate area of triangle using cross product."""
        # Vector from n1 to n2
        v1 = (n2.x - n1.x, n2.y - n1.y, n2.z - n1.z)
        # Vector from n1 to n3
        v2 = (n3.x - n1.x, n3.y - n1.y, n3.z - n1.z)

        # Cross product
        cx = v1[1] * v2[2] - v1[2] * v2[1]
        cy = v1[2] * v2[0] - v1[0] * v2[2]
        cz = v1[0] * v2[1] - v1[1] * v2[0]

        # Area = 0.5 * |cross product|
        return 0.5 * sqrt(cx * cx + cy * cy + cz * cz)

    def centroid(self) -> tuple[float, float, float]:
        """
        Calculate centroid of the shell.

        Returns:
            (x, y, z) coordinates of centroid

        Raises:
            ValidationError: If nodes not set
        """
        nodes = self._ensure_nodes()
        n = len(nodes)
        cx = sum(node.x for node in nodes) / n
        cy = sum(node.y for node in nodes) / n
        cz = sum(node.z for node in nodes) / n
        return (cx, cy, cz)

    def normal(self) -> tuple[float, float, float]:
        """
        Calculate unit normal vector to the shell surface.

        Uses first three nodes to compute normal.

        Returns:
            (nx, ny, nz) unit normal vector

        Raises:
            ValidationError: If nodes not set
        """
        nodes = self._ensure_nodes()
        n1, n2, n3 = nodes[0], nodes[1], nodes[2]

        # Vectors
        v1 = (n2.x - n1.x, n2.y - n1.y, n2.z - n1.z)
        v2 = (n3.x - n1.x, n3.y - n1.y, n3.z - n1.z)

        # Cross product
        nx = v1[1] * v2[2] - v1[2] * v2[1]
        ny = v1[2] * v2[0] - v1[0] * v2[2]
        nz = v1[0] * v2[1] - v1[1] * v2[0]

        # Normalize
        length = sqrt(nx * nx + ny * ny + nz * nz)
        if length < 1e-9:
            return (0.0, 0.0, 1.0)  # Default to Z-up
        return (nx / length, ny / length, nz / length)

    def mass(self, material: "Material") -> float:
        """
        Calculate the mass of this shell element.

        Mass = rho * t * A
        where:
            rho = material density (kg/m³)
            t = thickness (m)
            A = area (m²)

        Args:
            material: Material with density (rho)

        Returns:
            Mass in kg

        Raises:
            ValidationError: If nodes not set
        """
        area = self.area()
        return material.rho * self.thickness * area

    def weight(self, material: "Material", g: float = 9.81) -> float:
        """
        Calculate the weight of this shell element.

        Weight = mass * g

        Args:
            material: Material with density (rho)
            g: Gravitational acceleration (default 9.81 m/s²)

        Returns:
            Weight in kN

        Raises:
            ValidationError: If nodes not set
        """
        mass_kg = self.mass(material)
        return mass_kg * g / 1000  # Convert N to kN

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "node_ids": list(self.node_ids),
            "material_name": self.material_name,
            "thickness": self.thickness,
            "shell_type": self.shell_type.value,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Shell":
        """Create from dictionary."""
        shell_type_str = data.get("shell_type", "shell")
        try:
            shell_type = ShellType(shell_type_str)
        except ValueError:
            shell_type = ShellType.SHELL

        return cls(
            id=data.get("id", -1),
            node_ids=data["node_ids"],
            material_name=data["material_name"],
            thickness=data["thickness"],
            shell_type=shell_type,
            label=data.get("label", ""),
        )


# Minimum shell area in square meters
MIN_SHELL_AREA = 0.0001


def validate_shell_area(nodes: list[Node]) -> float:
    """
    Validate that shell area is above minimum.

    Args:
        nodes: List of 3 or 4 nodes

    Returns:
        Shell area

    Raises:
        ValidationError: If area is below minimum
    """
    if len(nodes) == 3:
        n1, n2, n3 = nodes
        v1 = (n2.x - n1.x, n2.y - n1.y, n2.z - n1.z)
        v2 = (n3.x - n1.x, n3.y - n1.y, n3.z - n1.z)
        cx = v1[1] * v2[2] - v1[2] * v2[1]
        cy = v1[2] * v2[0] - v1[0] * v2[2]
        cz = v1[0] * v2[1] - v1[1] * v2[0]
        area = 0.5 * sqrt(cx * cx + cy * cy + cz * cz)
    else:
        # Quad: sum of two triangles
        n1, n2, n3, n4 = nodes
        v1 = (n2.x - n1.x, n2.y - n1.y, n2.z - n1.z)
        v2 = (n3.x - n1.x, n3.y - n1.y, n3.z - n1.z)
        cx = v1[1] * v2[2] - v1[2] * v2[1]
        cy = v1[2] * v2[0] - v1[0] * v2[2]
        cz = v1[0] * v2[1] - v1[1] * v2[0]
        area1 = 0.5 * sqrt(cx * cx + cy * cy + cz * cz)

        v1 = (n3.x - n1.x, n3.y - n1.y, n3.z - n1.z)
        v2 = (n4.x - n1.x, n4.y - n1.y, n4.z - n1.z)
        cx = v1[1] * v2[2] - v1[2] * v2[1]
        cy = v1[2] * v2[0] - v1[0] * v2[2]
        cz = v1[0] * v2[1] - v1[1] * v2[0]
        area2 = 0.5 * sqrt(cx * cx + cy * cy + cz * cz)

        area = area1 + area2

    if area < MIN_SHELL_AREA:
        raise ValidationError(
            f"Shell area ({area:.6f}m²) is below minimum ({MIN_SHELL_AREA}m²)",
            field="area",
        )

    return area

"""
Local axes calculation for frame elements.

Follows SAP2000/ETABS convention for local coordinate systems:
- Axis 1 (x-local): Along element length, from node i to node j
- Axis 2 (y-local): Perpendicular to axis 1, typically horizontal for vertical elements
- Axis 3 (z-local): Perpendicular to 1 and 2 (right-hand rule)

The local axes determine how section properties (Ix, Iy) are oriented
and how loads/results are interpreted.
"""

from dataclasses import dataclass
from math import atan2, cos, sin, sqrt
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray


if TYPE_CHECKING:
    from paz.domain.model.node import Node


@dataclass(frozen=True)
class LocalAxes:
    """
    Local coordinate system for a frame element.

    Attributes:
        axis1: Unit vector along element (x-local), from i to j
        axis2: Unit vector perpendicular to axis1 (y-local)
        axis3: Unit vector perpendicular to 1 and 2 (z-local)
        rotation: Rotation angle in radians about axis1

    The axes form a right-handed coordinate system.
    """

    axis1: tuple[float, float, float]
    axis2: tuple[float, float, float]
    axis3: tuple[float, float, float]
    rotation: float = 0.0

    def to_matrix(self) -> NDArray[np.float64]:
        """
        Get transformation matrix from global to local coordinates.

        Returns:
            3x3 rotation matrix where rows are local axes in global coords
        """
        return np.array([self.axis1, self.axis2, self.axis3], dtype=np.float64)

    def global_to_local(self, vector: tuple[float, float, float]) -> tuple[float, float, float]:
        """Transform a vector from global to local coordinates."""
        v = np.array(vector, dtype=np.float64)
        local = self.to_matrix() @ v
        return (float(local[0]), float(local[1]), float(local[2]))

    def local_to_global(self, vector: tuple[float, float, float]) -> tuple[float, float, float]:
        """Transform a vector from local to global coordinates."""
        v = np.array(vector, dtype=np.float64)
        # Transpose of rotation matrix for inverse transformation
        glob = self.to_matrix().T @ v
        return (float(glob[0]), float(glob[1]), float(glob[2]))


def calculate_local_axes(
    node_i: "Node",
    node_j: "Node",
    rotation: float = 0.0,
) -> LocalAxes:
    """
    Calculate local axes for a frame element.

    Follows SAP2000 convention:
    - For non-vertical elements: axis2 is horizontal (in XY plane)
    - For vertical elements: axis2 is along global X
    - Rotation angle rotates axis2 and axis3 about axis1

    Args:
        node_i: Start node
        node_j: End node
        rotation: Rotation angle in radians about the element axis

    Returns:
        LocalAxes object with the three unit vectors

    Raises:
        ValueError: If nodes are coincident (zero length)
    """
    # Calculate element direction vector
    dx = node_j.x - node_i.x
    dy = node_j.y - node_i.y
    dz = node_j.z - node_i.z

    length = sqrt(dx * dx + dy * dy + dz * dz)

    if length < 1e-9:
        raise ValueError("Cannot calculate local axes for zero-length element")

    # Axis 1: unit vector along element
    ax1 = (dx / length, dy / length, dz / length)

    # Determine if element is vertical (parallel to global Z)
    horizontal_length = sqrt(dx * dx + dy * dy)
    is_vertical = horizontal_length < 1e-9

    if is_vertical:
        # Vertical element: use global X as reference for axis 2
        # axis2 initially along global X
        ax2_init = (1.0, 0.0, 0.0)
        # axis3 = axis1 x axis2 (will be along Y or -Y)
        ax3_init = _cross(ax1, ax2_init)
        ax3_init = _normalize(ax3_init)
        # Recalculate axis2 to ensure orthogonality
        ax2_init = _cross(ax3_init, ax1)
        ax2_init = _normalize(ax2_init)
    else:
        # Non-vertical element: axis2 is horizontal
        # Project axis1 onto XY plane and rotate 90° to get horizontal perpendicular
        # axis2 = (-dy, dx, 0) normalized (perpendicular to projection in XY)
        ax2_init = (-dy / horizontal_length, dx / horizontal_length, 0.0)
        # axis3 = axis1 x axis2
        ax3_init = _cross(ax1, ax2_init)
        ax3_init = _normalize(ax3_init)

    # Apply rotation about axis1 if specified
    if abs(rotation) > 1e-9:
        ax2 = _rotate_about_axis(ax2_init, ax1, rotation)
        ax3 = _rotate_about_axis(ax3_init, ax1, rotation)
    else:
        ax2 = ax2_init
        ax3 = ax3_init

    return LocalAxes(
        axis1=ax1,
        axis2=ax2,
        axis3=ax3,
        rotation=rotation,
    )


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    """Cross product of two 3D vectors."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    """Dot product of two 3D vectors."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    """Normalize a 3D vector to unit length."""
    length = sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length < 1e-12:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _rotate_about_axis(
    v: tuple[float, float, float],
    axis: tuple[float, float, float],
    angle: float,
) -> tuple[float, float, float]:
    """
    Rotate vector v about axis by angle (Rodrigues' rotation formula).

    Args:
        v: Vector to rotate
        axis: Unit vector defining rotation axis
        angle: Rotation angle in radians

    Returns:
        Rotated vector
    """
    c = cos(angle)
    s = sin(angle)

    # v_rot = v*cos(t) + (axis x v)*sin(t) + axis*(axis.v)*(1-cos(t))
    cross = _cross(axis, v)
    dot = _dot(axis, v)

    return (
        v[0] * c + cross[0] * s + axis[0] * dot * (1 - c),
        v[1] * c + cross[1] * s + axis[1] * dot * (1 - c),
        v[2] * c + cross[2] * s + axis[2] * dot * (1 - c),
    )


def calculate_element_angle(node_i: "Node", node_j: "Node") -> float:
    """
    Calculate the angle of the element projected onto the XY plane.

    Returns angle in radians from global X axis, measured counter-clockwise.

    Args:
        node_i: Start node
        node_j: End node

    Returns:
        Angle in radians (-π to π)
    """
    dx = node_j.x - node_i.x
    dy = node_j.y - node_i.y
    return atan2(dy, dx)

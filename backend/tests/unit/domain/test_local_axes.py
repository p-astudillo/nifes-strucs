"""Tests for LocalAxes calculation."""

import pytest
from math import pi, sqrt

from paz.domain.model.local_axes import (
    LocalAxes,
    calculate_element_angle,
    calculate_local_axes,
)
from paz.domain.model.node import Node
from paz.domain.model.restraint import FREE


class TestLocalAxes:
    """Tests for LocalAxes dataclass."""

    def test_to_matrix(self) -> None:
        """Test transformation matrix generation."""
        axes = LocalAxes(
            axis1=(1.0, 0.0, 0.0),
            axis2=(0.0, 1.0, 0.0),
            axis3=(0.0, 0.0, 1.0),
        )
        matrix = axes.to_matrix()

        assert matrix.shape == (3, 3)
        # First row is axis1
        assert abs(matrix[0, 0] - 1.0) < 1e-10
        # Second row is axis2
        assert abs(matrix[1, 1] - 1.0) < 1e-10
        # Third row is axis3
        assert abs(matrix[2, 2] - 1.0) < 1e-10

    def test_global_to_local(self) -> None:
        """Test global to local coordinate transformation."""
        # Standard axes - identity transformation
        axes = LocalAxes(
            axis1=(1.0, 0.0, 0.0),
            axis2=(0.0, 1.0, 0.0),
            axis3=(0.0, 0.0, 1.0),
        )
        local = axes.global_to_local((1.0, 2.0, 3.0))
        assert abs(local[0] - 1.0) < 1e-10
        assert abs(local[1] - 2.0) < 1e-10
        assert abs(local[2] - 3.0) < 1e-10

    def test_local_to_global(self) -> None:
        """Test local to global coordinate transformation."""
        axes = LocalAxes(
            axis1=(1.0, 0.0, 0.0),
            axis2=(0.0, 1.0, 0.0),
            axis3=(0.0, 0.0, 1.0),
        )
        glob = axes.local_to_global((1.0, 2.0, 3.0))
        assert abs(glob[0] - 1.0) < 1e-10
        assert abs(glob[1] - 2.0) < 1e-10
        assert abs(glob[2] - 3.0) < 1e-10

    def test_roundtrip_transformation(self) -> None:
        """Test that global->local->global returns original."""
        # Rotated axes
        s2 = sqrt(2) / 2
        axes = LocalAxes(
            axis1=(s2, s2, 0.0),
            axis2=(-s2, s2, 0.0),
            axis3=(0.0, 0.0, 1.0),
        )
        original = (5.0, 3.0, 2.0)
        local = axes.global_to_local(original)
        restored = axes.local_to_global(local)

        assert abs(restored[0] - original[0]) < 1e-9
        assert abs(restored[1] - original[1]) < 1e-9
        assert abs(restored[2] - original[2]) < 1e-9


class TestCalculateLocalAxes:
    """Tests for calculate_local_axes function."""

    def test_horizontal_beam_along_x(self) -> None:
        """Test local axes for horizontal beam along global X."""
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=5, y=0, z=0, restraint=FREE)

        axes = calculate_local_axes(node_i, node_j)

        # Axis 1 should be along +X
        assert abs(axes.axis1[0] - 1.0) < 1e-10
        assert abs(axes.axis1[1]) < 1e-10
        assert abs(axes.axis1[2]) < 1e-10

        # Axis 2 should be horizontal (no Z component for horizontal element)
        assert abs(axes.axis2[2]) < 1e-10

    def test_horizontal_beam_along_y(self) -> None:
        """Test local axes for horizontal beam along global Y."""
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=0, y=5, z=0, restraint=FREE)

        axes = calculate_local_axes(node_i, node_j)

        # Axis 1 should be along +Y
        assert abs(axes.axis1[0]) < 1e-10
        assert abs(axes.axis1[1] - 1.0) < 1e-10
        assert abs(axes.axis1[2]) < 1e-10

    def test_vertical_column(self) -> None:
        """Test local axes for vertical column."""
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=0, y=0, z=3, restraint=FREE)

        axes = calculate_local_axes(node_i, node_j)

        # Axis 1 should be along +Z
        assert abs(axes.axis1[0]) < 1e-10
        assert abs(axes.axis1[1]) < 1e-10
        assert abs(axes.axis1[2] - 1.0) < 1e-10

        # Axis 2 should be along X for vertical elements
        assert abs(axes.axis2[0] - 1.0) < 1e-10 or abs(axes.axis2[0] + 1.0) < 1e-10

    def test_inclined_beam(self) -> None:
        """Test local axes for inclined beam."""
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=3, y=4, z=0, restraint=FREE)  # 3-4-5 triangle

        axes = calculate_local_axes(node_i, node_j)

        # Axis 1 should be unit vector from i to j
        expected_ax1 = (0.6, 0.8, 0.0)  # 3/5, 4/5, 0
        assert abs(axes.axis1[0] - expected_ax1[0]) < 1e-10
        assert abs(axes.axis1[1] - expected_ax1[1]) < 1e-10
        assert abs(axes.axis1[2] - expected_ax1[2]) < 1e-10

    def test_3d_beam(self) -> None:
        """Test local axes for 3D beam."""
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=1, y=1, z=1, restraint=FREE)

        axes = calculate_local_axes(node_i, node_j)

        # Axis 1 should point from i to j
        length = sqrt(3)
        expected = 1 / length
        assert abs(axes.axis1[0] - expected) < 1e-10
        assert abs(axes.axis1[1] - expected) < 1e-10
        assert abs(axes.axis1[2] - expected) < 1e-10

        # All axes should be unit vectors
        for ax in [axes.axis1, axes.axis2, axes.axis3]:
            norm = sqrt(ax[0]**2 + ax[1]**2 + ax[2]**2)
            assert abs(norm - 1.0) < 1e-9

        # Axes should be orthogonal
        dot_12 = sum(a * b for a, b in zip(axes.axis1, axes.axis2))
        dot_13 = sum(a * b for a, b in zip(axes.axis1, axes.axis3))
        dot_23 = sum(a * b for a, b in zip(axes.axis2, axes.axis3))
        assert abs(dot_12) < 1e-9
        assert abs(dot_13) < 1e-9
        assert abs(dot_23) < 1e-9

    def test_with_rotation(self) -> None:
        """Test local axes with rotation angle."""
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=5, y=0, z=0, restraint=FREE)

        # Without rotation
        axes0 = calculate_local_axes(node_i, node_j, rotation=0)

        # With 90 degree rotation
        axes90 = calculate_local_axes(node_i, node_j, rotation=pi / 2)

        # Axis 1 should be the same (along element)
        assert abs(axes0.axis1[0] - axes90.axis1[0]) < 1e-10

        # Axis 2 and 3 should be rotated
        # Original axis2 should become axis3 (or -axis3)
        # Check that axes are different
        assert abs(axes0.axis2[2] - axes90.axis2[2]) > 0.5

    def test_zero_length_raises(self) -> None:
        """Test that zero-length element raises error."""
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=0, y=0, z=0, restraint=FREE)

        with pytest.raises(ValueError, match="zero-length"):
            calculate_local_axes(node_i, node_j)


class TestCalculateElementAngle:
    """Tests for calculate_element_angle function."""

    def test_along_x(self) -> None:
        """Test angle for element along +X."""
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=5, y=0, z=0, restraint=FREE)

        angle = calculate_element_angle(node_i, node_j)
        assert abs(angle) < 1e-10

    def test_along_y(self) -> None:
        """Test angle for element along +Y."""
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=0, y=5, z=0, restraint=FREE)

        angle = calculate_element_angle(node_i, node_j)
        assert abs(angle - pi / 2) < 1e-10

    def test_45_degrees(self) -> None:
        """Test angle for 45-degree element."""
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=5, y=5, z=0, restraint=FREE)

        angle = calculate_element_angle(node_i, node_j)
        assert abs(angle - pi / 4) < 1e-10

    def test_negative_x(self) -> None:
        """Test angle for element along -X."""
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=-5, y=0, z=0, restraint=FREE)

        angle = calculate_element_angle(node_i, node_j)
        assert abs(abs(angle) - pi) < 1e-10

"""Tests for Frame and FrameReleases models."""

import pytest
from math import pi, sqrt

from paz.core.exceptions import FrameError, ValidationError
from paz.domain.model.frame import (
    Frame,
    FrameReleases,
    MIN_FRAME_LENGTH,
    validate_frame_length,
)
from paz.domain.model.node import Node
from paz.domain.model.restraint import FREE


class TestFrameReleases:
    """Tests for FrameReleases dataclass."""

    def test_default_is_fixed(self) -> None:
        """Test that default releases are all fixed."""
        releases = FrameReleases()
        assert releases.is_fully_fixed()

    def test_fixed_fixed(self) -> None:
        """Test fixed-fixed factory."""
        releases = FrameReleases.fixed_fixed()
        assert releases.is_fully_fixed()

    def test_pinned_pinned(self) -> None:
        """Test pinned-pinned factory."""
        releases = FrameReleases.pinned_pinned()
        assert releases.M2_i is True
        assert releases.M3_i is True
        assert releases.M2_j is True
        assert releases.M3_j is True
        assert not releases.is_fully_fixed()

    def test_fixed_pinned(self) -> None:
        """Test fixed-pinned factory."""
        releases = FrameReleases.fixed_pinned()
        assert releases.M2_i is False
        assert releases.M3_i is False
        assert releases.M2_j is True
        assert releases.M3_j is True

    def test_pinned_fixed(self) -> None:
        """Test pinned-fixed factory."""
        releases = FrameReleases.pinned_fixed()
        assert releases.M2_i is True
        assert releases.M3_i is True
        assert releases.M2_j is False
        assert releases.M3_j is False

    def test_to_dict_from_dict(self) -> None:
        """Test serialization roundtrip."""
        releases = FrameReleases(M2_i=True, M3_j=True, T_i=True)
        data = releases.to_dict()

        restored = FrameReleases.from_dict(data)
        assert restored.M2_i is True
        assert restored.M3_j is True
        assert restored.T_i is True
        assert restored.P_i is False


class TestFrame:
    """Tests for Frame dataclass."""

    def test_create_frame(self) -> None:
        """Test creating a basic frame."""
        frame = Frame(
            node_i_id=1,
            node_j_id=2,
            material_name="A36",
            section_name="W14X30",
        )
        assert frame.node_i_id == 1
        assert frame.node_j_id == 2
        assert frame.material_name == "A36"
        assert frame.section_name == "W14X30"
        assert frame.rotation == 0.0
        assert frame.releases.is_fully_fixed()

    def test_frame_same_node_raises(self) -> None:
        """Test that frame connecting node to itself raises error."""
        with pytest.raises(ValidationError, match="cannot connect a node to itself"):
            Frame(node_i_id=1, node_j_id=1, material_name="A36", section_name="W14X30")

    def test_frame_empty_material_raises(self) -> None:
        """Test that empty material raises error."""
        with pytest.raises(ValidationError, match="material"):
            Frame(node_i_id=1, node_j_id=2, material_name="", section_name="W14X30")

    def test_frame_empty_section_raises(self) -> None:
        """Test that empty section raises error."""
        with pytest.raises(ValidationError, match="section"):
            Frame(node_i_id=1, node_j_id=2, material_name="A36", section_name="")

    def test_frame_with_releases(self) -> None:
        """Test frame with custom releases."""
        releases = FrameReleases.pinned_pinned()
        frame = Frame(
            node_i_id=1,
            node_j_id=2,
            material_name="A36",
            section_name="W14X30",
            releases=releases,
        )
        assert frame.releases.M2_i is True
        assert frame.releases.M2_j is True

    def test_frame_with_rotation(self) -> None:
        """Test frame with rotation."""
        frame = Frame(
            node_i_id=1,
            node_j_id=2,
            material_name="A36",
            section_name="W14X30",
            rotation=pi / 4,
        )
        assert abs(frame.rotation - pi / 4) < 1e-10

    def test_set_nodes(self) -> None:
        """Test setting node references."""
        frame = Frame(
            node_i_id=1,
            node_j_id=2,
            material_name="A36",
            section_name="W14X30",
        )
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=3, y=4, z=0, restraint=FREE)

        frame.set_nodes(node_i, node_j)

        # Now length should work
        assert abs(frame.length() - 5.0) < 1e-10

    def test_set_nodes_wrong_id_raises(self) -> None:
        """Test that setting wrong nodes raises error."""
        frame = Frame(
            node_i_id=1,
            node_j_id=2,
            material_name="A36",
            section_name="W14X30",
        )
        node_i = Node(id=99, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=3, y=4, z=0, restraint=FREE)

        with pytest.raises(FrameError, match="mismatch"):
            frame.set_nodes(node_i, node_j)

    def test_length_without_nodes_raises(self) -> None:
        """Test that length without nodes raises error."""
        frame = Frame(
            node_i_id=1,
            node_j_id=2,
            material_name="A36",
            section_name="W14X30",
        )
        with pytest.raises(FrameError, match="Node references not set"):
            frame.length()

    def test_length_calculation(self) -> None:
        """Test length calculation."""
        frame = Frame(node_i_id=1, node_j_id=2, material_name="A36", section_name="W14X30")
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=1, y=0, z=0, restraint=FREE)
        frame.set_nodes(node_i, node_j)

        assert abs(frame.length() - 1.0) < 1e-10

    def test_length_3d(self) -> None:
        """Test 3D length calculation."""
        frame = Frame(node_i_id=1, node_j_id=2, material_name="A36", section_name="W14X30")
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=1, y=2, z=2, restraint=FREE)  # length = 3
        frame.set_nodes(node_i, node_j)

        assert abs(frame.length() - 3.0) < 1e-10

    def test_midpoint(self) -> None:
        """Test midpoint calculation."""
        frame = Frame(node_i_id=1, node_j_id=2, material_name="A36", section_name="W14X30")
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=4, y=2, z=6, restraint=FREE)
        frame.set_nodes(node_i, node_j)

        mid = frame.midpoint()
        assert abs(mid[0] - 2.0) < 1e-10
        assert abs(mid[1] - 1.0) < 1e-10
        assert abs(mid[2] - 3.0) < 1e-10

    def test_direction_vector(self) -> None:
        """Test direction vector calculation."""
        frame = Frame(node_i_id=1, node_j_id=2, material_name="A36", section_name="W14X30")
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=3, y=0, z=0, restraint=FREE)
        frame.set_nodes(node_i, node_j)

        direction = frame.direction_vector()
        assert abs(direction[0] - 1.0) < 1e-10
        assert abs(direction[1] - 0.0) < 1e-10
        assert abs(direction[2] - 0.0) < 1e-10

    def test_point_at(self) -> None:
        """Test point along frame."""
        frame = Frame(node_i_id=1, node_j_id=2, material_name="A36", section_name="W14X30")
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=10, y=0, z=0, restraint=FREE)
        frame.set_nodes(node_i, node_j)

        # At t=0, should be at node i
        p0 = frame.point_at(0)
        assert abs(p0[0] - 0.0) < 1e-10

        # At t=0.5, should be at midpoint
        p5 = frame.point_at(0.5)
        assert abs(p5[0] - 5.0) < 1e-10

        # At t=1, should be at node j
        p1 = frame.point_at(1)
        assert abs(p1[0] - 10.0) < 1e-10

    def test_to_dict_from_dict(self) -> None:
        """Test serialization roundtrip."""
        releases = FrameReleases(M2_i=True)
        frame = Frame(
            id=42,
            node_i_id=1,
            node_j_id=2,
            material_name="A36",
            section_name="W14X30",
            rotation=0.5,
            releases=releases,
            label="Beam 1",
        )
        data = frame.to_dict()

        restored = Frame.from_dict(data)
        assert restored.id == 42
        assert restored.node_i_id == 1
        assert restored.node_j_id == 2
        assert restored.material_name == "A36"
        assert restored.section_name == "W14X30"
        assert abs(restored.rotation - 0.5) < 1e-10
        assert restored.releases.M2_i is True
        assert restored.label == "Beam 1"


class TestValidateFrameLength:
    """Tests for frame length validation."""

    def test_valid_length(self) -> None:
        """Test that valid length passes."""
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=1, y=0, z=0, restraint=FREE)

        length = validate_frame_length(node_i, node_j)
        assert abs(length - 1.0) < 1e-10

    def test_too_short_raises(self) -> None:
        """Test that too short frame raises error."""
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=0.001, y=0, z=0, restraint=FREE)  # 1mm < MIN_FRAME_LENGTH

        with pytest.raises(ValidationError, match="below minimum"):
            validate_frame_length(node_i, node_j)

    def test_exactly_minimum_passes(self) -> None:
        """Test that exactly minimum length passes."""
        node_i = Node(id=1, x=0, y=0, z=0, restraint=FREE)
        node_j = Node(id=2, x=MIN_FRAME_LENGTH, y=0, z=0, restraint=FREE)

        length = validate_frame_length(node_i, node_j)
        assert abs(length - MIN_FRAME_LENGTH) < 1e-10

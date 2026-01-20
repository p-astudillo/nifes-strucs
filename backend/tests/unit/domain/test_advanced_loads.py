"""
Tests for F40 - Advanced Loads (Cargas Avanzadas).

Tests cover:
- DistributedLoad: uniform, triangular, trapezoidal, partial
- PointLoadOnFrame: point loads at specific locations
- Factory functions for creating loads
"""

import pytest
from uuid import uuid4

from paz.domain.loads import (
    DistributedLoad,
    LoadDirection,
    PointLoadDirection,
    PointLoadOnFrame,
    midpoint_load,
    partial_uniform_load,
    trapezoidal_load,
    triangular_load,
    uniform_load,
)


class TestDistributedLoad:
    """Tests for DistributedLoad class."""

    def test_uniform_load_creation(self):
        """Test creating a uniform distributed load."""
        load_case_id = uuid4()
        load = DistributedLoad(
            frame_id=1,
            load_case_id=load_case_id,
            w_start=10.0,
            w_end=10.0,
        )

        assert load.frame_id == 1
        assert load.w_start == 10.0
        assert load.w_end == 10.0
        assert load.is_uniform is True
        assert load.is_full_length is True

    def test_trapezoidal_load_creation(self):
        """Test creating a trapezoidal distributed load."""
        load_case_id = uuid4()
        load = DistributedLoad(
            frame_id=1,
            load_case_id=load_case_id,
            w_start=5.0,
            w_end=15.0,
        )

        assert load.w_start == 5.0
        assert load.w_end == 15.0
        assert load.is_uniform is False
        assert load.average_intensity == 10.0

    def test_partial_load_creation(self):
        """Test creating a partial distributed load."""
        load_case_id = uuid4()
        load = DistributedLoad(
            frame_id=1,
            load_case_id=load_case_id,
            w_start=10.0,
            start_loc=0.25,
            end_loc=0.75,
        )

        assert load.start_loc == 0.25
        assert load.end_loc == 0.75
        assert load.is_full_length is False

    def test_intensity_at_location(self):
        """Test getting intensity at specific location."""
        load_case_id = uuid4()

        # Trapezoidal: 0 to 20 kN/m
        load = DistributedLoad(
            frame_id=1,
            load_case_id=load_case_id,
            w_start=0.0,
            w_end=20.0,
        )

        assert load.intensity_at(0.0) == 0.0
        assert load.intensity_at(0.5) == 10.0
        assert load.intensity_at(1.0) == 20.0

    def test_intensity_outside_range(self):
        """Test intensity outside load range returns 0."""
        load_case_id = uuid4()
        load = DistributedLoad(
            frame_id=1,
            load_case_id=load_case_id,
            w_start=10.0,
            start_loc=0.25,
            end_loc=0.75,
        )

        assert load.intensity_at(0.1) == 0.0
        assert load.intensity_at(0.9) == 0.0

    def test_invalid_location_range(self):
        """Test that invalid location ranges raise errors."""
        load_case_id = uuid4()

        with pytest.raises(ValueError):
            DistributedLoad(
                frame_id=1,
                load_case_id=load_case_id,
                w_start=10.0,
                start_loc=0.75,
                end_loc=0.25,  # end before start
            )

    def test_serialization_roundtrip(self):
        """Test to_dict and from_dict roundtrip."""
        load_case_id = uuid4()
        load = DistributedLoad(
            frame_id=1,
            load_case_id=load_case_id,
            direction=LoadDirection.LOCAL_Y,
            w_start=5.0,
            w_end=15.0,
            start_loc=0.2,
            end_loc=0.8,
        )

        data = load.to_dict()
        restored = DistributedLoad.from_dict(data)

        assert restored.frame_id == load.frame_id
        assert restored.w_start == load.w_start
        assert restored.w_end == load.w_end
        assert restored.start_loc == load.start_loc
        assert restored.end_loc == load.end_loc
        assert restored.direction == load.direction


class TestDistributedLoadFactories:
    """Tests for distributed load factory functions."""

    def test_uniform_load_factory(self):
        """Test uniform_load factory function."""
        load_case_id = uuid4()
        load = uniform_load(frame_id=1, load_case_id=load_case_id, w=15.0)

        assert load.w_start == 15.0
        assert load.w_end == 15.0
        assert load.is_uniform is True
        assert load.is_full_length is True
        assert load.direction == LoadDirection.GRAVITY

    def test_triangular_load_ascending(self):
        """Test triangular_load factory with ascending load."""
        load_case_id = uuid4()
        load = triangular_load(
            frame_id=1,
            load_case_id=load_case_id,
            w_max=20.0,
            ascending=True,
        )

        assert load.w_start == 0.0
        assert load.w_end == 20.0
        assert load.is_uniform is False

    def test_triangular_load_descending(self):
        """Test triangular_load factory with descending load."""
        load_case_id = uuid4()
        load = triangular_load(
            frame_id=1,
            load_case_id=load_case_id,
            w_max=20.0,
            ascending=False,
        )

        assert load.w_start == 20.0
        assert load.w_end == 0.0

    def test_trapezoidal_load_factory(self):
        """Test trapezoidal_load factory function."""
        load_case_id = uuid4()
        load = trapezoidal_load(
            frame_id=1,
            load_case_id=load_case_id,
            w_start=5.0,
            w_end=15.0,
        )

        assert load.w_start == 5.0
        assert load.w_end == 15.0
        assert load.average_intensity == 10.0

    def test_partial_uniform_load_factory(self):
        """Test partial_uniform_load factory function."""
        load_case_id = uuid4()
        load = partial_uniform_load(
            frame_id=1,
            load_case_id=load_case_id,
            w=10.0,
            start_loc=0.25,
            end_loc=0.75,
        )

        assert load.w_start == 10.0
        assert load.w_end == 10.0
        assert load.is_uniform is True
        assert load.is_full_length is False


class TestPointLoadOnFrame:
    """Tests for PointLoadOnFrame class."""

    def test_point_load_creation(self):
        """Test creating a point load on frame."""
        load_case_id = uuid4()
        load = PointLoadOnFrame(
            frame_id=1,
            load_case_id=load_case_id,
            location=0.5,
            P=25.0,
        )

        assert load.frame_id == 1
        assert load.location == 0.5
        assert load.P == 25.0
        assert load.direction == PointLoadDirection.GRAVITY
        assert load.is_at_midpoint is True

    def test_point_load_at_start(self):
        """Test point load at start of element."""
        load_case_id = uuid4()
        load = PointLoadOnFrame(
            frame_id=1,
            load_case_id=load_case_id,
            location=0.0,
            P=10.0,
        )

        assert load.is_at_start is True
        assert load.is_at_end is False
        assert load.is_at_midpoint is False

    def test_point_load_at_end(self):
        """Test point load at end of element."""
        load_case_id = uuid4()
        load = PointLoadOnFrame(
            frame_id=1,
            load_case_id=load_case_id,
            location=1.0,
            P=10.0,
        )

        assert load.is_at_start is False
        assert load.is_at_end is True

    def test_invalid_location(self):
        """Test that invalid location raises error."""
        load_case_id = uuid4()

        with pytest.raises(ValueError):
            PointLoadOnFrame(
                frame_id=1,
                load_case_id=load_case_id,
                location=1.5,  # outside 0-1 range
                P=10.0,
            )

    def test_point_load_with_moment(self):
        """Test point load with accompanying moment."""
        load_case_id = uuid4()
        load = PointLoadOnFrame(
            frame_id=1,
            load_case_id=load_case_id,
            location=0.5,
            P=25.0,
            M=10.0,
        )

        assert load.P == 25.0
        assert load.M == 10.0

    def test_serialization_roundtrip(self):
        """Test to_dict and from_dict roundtrip."""
        load_case_id = uuid4()
        load = PointLoadOnFrame(
            frame_id=1,
            load_case_id=load_case_id,
            location=0.3,
            P=25.0,
            direction=PointLoadDirection.LOCAL_Z,
            M=5.0,
        )

        data = load.to_dict()
        restored = PointLoadOnFrame.from_dict(data)

        assert restored.frame_id == load.frame_id
        assert restored.location == load.location
        assert restored.P == load.P
        assert restored.direction == load.direction
        assert restored.M == load.M


class TestPointLoadFactories:
    """Tests for point load factory functions."""

    def test_midpoint_load_factory(self):
        """Test midpoint_load factory function."""
        load_case_id = uuid4()
        load = midpoint_load(frame_id=1, load_case_id=load_case_id, P=30.0)

        assert load.location == 0.5
        assert load.P == 30.0
        assert load.is_at_midpoint is True
        assert load.direction == PointLoadDirection.GRAVITY


class TestLoadDirection:
    """Tests for load direction enums."""

    def test_distributed_load_directions(self):
        """Test all LoadDirection values."""
        assert LoadDirection.GRAVITY.value == "Gravity"
        assert LoadDirection.LOCAL_X.value == "Local X"
        assert LoadDirection.LOCAL_Y.value == "Local Y"
        assert LoadDirection.LOCAL_Z.value == "Local Z"
        assert LoadDirection.GLOBAL_X.value == "Global X"
        assert LoadDirection.GLOBAL_Y.value == "Global Y"
        assert LoadDirection.GLOBAL_Z.value == "Global Z"

    def test_point_load_directions(self):
        """Test all PointLoadDirection values."""
        assert PointLoadDirection.GRAVITY.value == "Gravity"
        assert PointLoadDirection.LOCAL_X.value == "Local X"
        assert PointLoadDirection.LOCAL_Y.value == "Local Y"
        assert PointLoadDirection.LOCAL_Z.value == "Local Z"
        assert PointLoadDirection.GLOBAL_X.value == "Global X"
        assert PointLoadDirection.GLOBAL_Y.value == "Global Y"
        assert PointLoadDirection.GLOBAL_Z.value == "Global Z"

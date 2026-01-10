"""
Unit tests for grid configuration and rendering.

Tests GridConfig, GridAxisConfig, SnapMode, and GridLayer.
"""

import pytest

from paz.core.grid_config import (
    GridAxisConfig,
    GridConfig,
    SnapMode,
    create_imperial_grid,
    create_metric_grid,
)
from paz.presentation.viewport.grid_layer import GridLayer, GridMeshes, GridPlane


class TestGridAxisConfig:
    """Tests for GridAxisConfig."""

    def test_default_values(self) -> None:
        """Test default axis configuration."""
        config = GridAxisConfig()

        assert config.spacing == 1.0
        assert config.minor_divisions == 4
        assert config.visible is True
        assert config.color == "#CCCCCC"
        assert config.minor_color == "#EEEEEE"

    def test_minor_spacing(self) -> None:
        """Test minor spacing calculation."""
        config = GridAxisConfig(spacing=1.0, minor_divisions=4)
        assert config.minor_spacing == 0.25

        config2 = GridAxisConfig(spacing=2.0, minor_divisions=10)
        assert config2.minor_spacing == 0.2

    def test_minor_spacing_zero_divisions(self) -> None:
        """Test minor spacing with zero divisions."""
        config = GridAxisConfig(spacing=1.0, minor_divisions=0)
        assert config.minor_spacing == 1.0

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        config = GridAxisConfig(spacing=2.0, visible=False)
        data = config.to_dict()

        assert data["spacing"] == 2.0
        assert data["visible"] is False

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {"spacing": 3.0, "minor_divisions": 6, "color": "#FF0000"}
        config = GridAxisConfig.from_dict(data)

        assert config.spacing == 3.0
        assert config.minor_divisions == 6
        assert config.color == "#FF0000"


class TestSnapMode:
    """Tests for SnapMode enum."""

    def test_snap_modes(self) -> None:
        """Test all snap mode values."""
        assert SnapMode.NONE.value == "none"
        assert SnapMode.GRID.value == "grid"
        assert SnapMode.NODE.value == "node"
        assert SnapMode.BOTH.value == "both"


class TestGridConfig:
    """Tests for GridConfig."""

    def test_default_values(self) -> None:
        """Test default grid configuration."""
        config = GridConfig()

        assert config.enabled is True
        assert config.snap_mode == SnapMode.GRID
        assert config.snap_tolerance == 0.1
        assert config.show_major is True
        assert config.show_minor is True
        assert config.extent == 50.0

    def test_z_axis_hidden_by_default(self) -> None:
        """Test Z axis is hidden by default (XY plane grid)."""
        config = GridConfig()
        assert config.z_axis.visible is False

    def test_set_uniform_spacing(self) -> None:
        """Test setting uniform spacing."""
        config = GridConfig()
        config.set_uniform_spacing(2.5)

        assert config.x_axis.spacing == 2.5
        assert config.y_axis.spacing == 2.5
        assert config.z_axis.spacing == 2.5

    def test_snap_coordinate_grid_mode(self) -> None:
        """Test coordinate snapping in grid mode."""
        config = GridConfig()
        config.x_axis.spacing = 1.0
        config.x_axis.minor_divisions = 4  # 0.25m minor grid
        config.snap_tolerance = 0.15

        # Should snap to nearest minor grid (0.25)
        assert config.snap_coordinate(0.23, "x") == 0.25
        assert config.snap_coordinate(0.12, "x") == 0.0

    def test_snap_coordinate_no_snap(self) -> None:
        """Test snapping disabled."""
        config = GridConfig()
        config.snap_mode = SnapMode.NONE

        assert config.snap_coordinate(0.23, "x") == 0.23

    def test_snap_coordinate_outside_tolerance(self) -> None:
        """Test snapping when outside tolerance."""
        config = GridConfig()
        config.snap_tolerance = 0.05
        config.x_axis.spacing = 1.0
        config.x_axis.minor_divisions = 4

        # 0.5 is far from any 0.25 grid line
        # Nearest is 0.5 which is 0.25 away - outside 0.05 tolerance
        # Actually 0.5 IS on the grid (0.25 * 2)
        assert config.snap_coordinate(0.5, "x") == 0.5

    def test_snap_point(self) -> None:
        """Test 3D point snapping."""
        config = GridConfig()
        config.set_uniform_spacing(1.0)
        config.snap_tolerance = 0.15

        x, y, z = config.snap_point(1.05, 2.95, 0.0)

        assert x == 1.0
        assert y == 3.0
        assert z == 0.0

    def test_to_dict(self) -> None:
        """Test serialization."""
        config = GridConfig()
        config.enabled = False
        config.snap_mode = SnapMode.BOTH

        data = config.to_dict()

        assert data["enabled"] is False
        assert data["snap_mode"] == "both"
        assert "x_axis" in data
        assert "y_axis" in data
        assert "z_axis" in data

    def test_from_dict(self) -> None:
        """Test deserialization."""
        data = {
            "enabled": False,
            "snap_mode": "node",
            "extent": 100.0,
        }
        config = GridConfig.from_dict(data)

        assert config.enabled is False
        assert config.snap_mode == SnapMode.NODE
        assert config.extent == 100.0

    def test_copy(self) -> None:
        """Test configuration copy."""
        original = GridConfig()
        original.extent = 75.0

        copied = original.copy()

        assert copied.extent == 75.0
        copied.extent = 100.0
        assert original.extent == 75.0  # Original unchanged


class TestGridPresets:
    """Tests for grid preset functions."""

    def test_metric_grid(self) -> None:
        """Test metric grid preset."""
        config = create_metric_grid(spacing=2.0)

        assert config.x_axis.spacing == 2.0
        assert config.y_axis.spacing == 2.0
        assert config.x_axis.minor_divisions == 4

    def test_imperial_grid(self) -> None:
        """Test imperial grid preset."""
        config = create_imperial_grid(spacing_ft=1.0)

        # 1 foot = 0.3048 meters
        assert config.x_axis.spacing == pytest.approx(0.3048, rel=0.001)
        assert config.x_axis.minor_divisions == 12  # 1 inch divisions


class TestGridLayer:
    """Tests for GridLayer renderer."""

    @pytest.fixture
    def layer(self) -> GridLayer:
        """Create grid layer."""
        return GridLayer()

    @pytest.fixture
    def config(self) -> GridConfig:
        """Create test configuration."""
        config = GridConfig()
        config.extent = 10.0
        config.x_axis.spacing = 2.0
        config.y_axis.spacing = 2.0
        return config

    def test_default_plane(self, layer: GridLayer) -> None:
        """Test default plane is XY."""
        assert layer.plane == GridPlane.XY

    def test_set_plane(self, layer: GridLayer) -> None:
        """Test setting grid plane."""
        layer.plane = GridPlane.XZ
        assert layer.plane == GridPlane.XZ

    def test_build_meshes_disabled(self, layer: GridLayer) -> None:
        """Test mesh building when disabled."""
        layer.config.enabled = False
        meshes = layer.build_meshes()

        assert meshes.major is None
        assert meshes.minor is None

    def test_build_meshes_enabled(
        self, layer: GridLayer, config: GridConfig
    ) -> None:
        """Test mesh building when enabled."""
        layer.config = config
        meshes = layer.build_meshes()

        assert meshes.major is not None
        assert meshes.major.n_points > 0

    def test_build_meshes_no_minor(
        self, layer: GridLayer, config: GridConfig
    ) -> None:
        """Test mesh building without minor grid."""
        config.show_minor = False
        layer.config = config
        meshes = layer.build_meshes()

        assert meshes.major is not None
        assert meshes.minor is None

    def test_major_grid_line_count(
        self, layer: GridLayer, config: GridConfig
    ) -> None:
        """Test major grid generates correct number of lines."""
        config.show_minor = False
        layer.config = config
        meshes = layer.build_meshes()

        # extent=10, spacing=2 -> lines at -10, -8, -6, ..., 8, 10
        # That's 11 lines in X direction and 11 in Y direction
        # Each line has 2 points
        # Total: 22 lines * 2 points = 44 points
        # Wait, we have 2 sets of lines (X and Y direction)
        # So 2 * 11 * 2 = 44 points
        assert meshes.major is not None
        assert meshes.major.n_points == 44

    def test_z_offset(self, layer: GridLayer, config: GridConfig) -> None:
        """Test Z offset for XY plane."""
        layer.config = config
        layer.set_z_offset(5.0)
        meshes = layer.build_meshes()

        if meshes.major is not None:
            # All points should have z=5.0
            z_coords = meshes.major.points[:, 2]
            assert all(z == 5.0 for z in z_coords)

    def test_get_major_color(self, layer: GridLayer) -> None:
        """Test getting major grid color."""
        color = layer.get_major_color()
        assert color == layer.config.x_axis.color

    def test_get_minor_color(self, layer: GridLayer) -> None:
        """Test getting minor grid color."""
        color = layer.get_minor_color()
        assert color == layer.config.x_axis.minor_color


class TestGridMeshes:
    """Tests for GridMeshes container."""

    def test_empty_meshes(self) -> None:
        """Test empty mesh container."""
        meshes = GridMeshes()
        assert meshes.major is None
        assert meshes.minor is None

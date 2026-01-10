"""
Unit tests for extruded section rendering.

Tests ProfileGenerator, ProfileGeometry, and ExtrudedRenderer.
"""

import numpy as np
import pytest

from paz.domain.model import StructuralModel
from paz.domain.model.restraint import FIXED
from paz.domain.sections import Section, SectionShape
from paz.domain.sections.profile_geometry import ProfileGenerator, ProfileGeometry
from paz.presentation.viewport.extruded_renderer import (
    ExtrudedRenderer,
    ExtrudedSettings,
    get_color_for_material,
)


class TestProfileGeometry:
    """Tests for ProfileGeometry dataclass."""

    def test_n_vertices(self) -> None:
        """Test vertex count property."""
        vertices = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        profile = ProfileGeometry(vertices=vertices, holes=[], centroid=(0.5, 0.5))
        assert profile.n_vertices == 4

    def test_has_holes_false(self) -> None:
        """Test has_holes property when no holes."""
        vertices = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        profile = ProfileGeometry(vertices=vertices, holes=[], centroid=(0.5, 0.5))
        assert not profile.has_holes

    def test_has_holes_true(self) -> None:
        """Test has_holes property when holes exist."""
        outer = np.array([[0, 0], [2, 0], [2, 2], [0, 2]])
        inner = np.array([[0.5, 0.5], [1.5, 0.5], [1.5, 1.5], [0.5, 1.5]])
        profile = ProfileGeometry(vertices=outer, holes=[inner], centroid=(1.0, 1.0))
        assert profile.has_holes


class TestProfileGenerator:
    """Tests for ProfileGenerator."""

    @pytest.fixture
    def generator(self) -> ProfileGenerator:
        """Create a profile generator."""
        return ProfileGenerator(circle_segments=16)

    @pytest.fixture
    def w_section(self) -> Section:
        """Create a W section."""
        return Section(
            name="W12x26",
            shape=SectionShape.W,
            A=0.0049,
            Ix=8.55e-5,
            Iy=1.74e-5,
            d=0.31,
            bf=0.165,
            tf=0.0096,
            tw=0.0058,
        )

    @pytest.fixture
    def hss_rect_section(self) -> Section:
        """Create a rectangular HSS section."""
        return Section(
            name="HSS6x4x1/4",
            shape=SectionShape.HSS_RECT,
            A=0.0029,
            Ix=3.5e-5,
            Iy=1.8e-5,
            d=0.152,
            bf=0.102,
            t=0.00635,
        )

    @pytest.fixture
    def pipe_section(self) -> Section:
        """Create a pipe section."""
        return Section(
            name="PIPE6STD",
            shape=SectionShape.PIPE,
            A=0.0022,
            Ix=2.8e-5,
            Iy=2.8e-5,
            OD=0.168,
            t=0.0071,
        )

    def test_generate_i_section(
        self, generator: ProfileGenerator, w_section: Section
    ) -> None:
        """Test I-section profile generation."""
        profile = generator.generate(w_section)

        assert profile.n_vertices == 12
        assert not profile.has_holes
        assert profile.centroid == (0.0, 0.0)

    def test_i_section_dimensions(
        self, generator: ProfileGenerator, w_section: Section
    ) -> None:
        """Test I-section profile has correct dimensions."""
        profile = generator.generate(w_section)

        # Check bounds match section dimensions
        x_min, x_max = profile.vertices[:, 0].min(), profile.vertices[:, 0].max()
        y_min, y_max = profile.vertices[:, 1].min(), profile.vertices[:, 1].max()

        assert x_max - x_min == pytest.approx(w_section.bf, rel=0.01)
        assert y_max - y_min == pytest.approx(w_section.d, rel=0.01)

    def test_generate_rectangular_hollow(
        self, generator: ProfileGenerator, hss_rect_section: Section
    ) -> None:
        """Test rectangular hollow section generation."""
        profile = generator.generate(hss_rect_section)

        assert profile.n_vertices == 4  # Outer rectangle
        assert profile.has_holes
        assert len(profile.holes) == 1
        assert len(profile.holes[0]) == 4  # Inner rectangle

    def test_generate_pipe(
        self, generator: ProfileGenerator, pipe_section: Section
    ) -> None:
        """Test pipe section generation."""
        profile = generator.generate(pipe_section)

        assert profile.n_vertices == 16  # circle_segments
        assert profile.has_holes
        assert len(profile.holes[0]) == 16

    def test_angle_section(self, generator: ProfileGenerator) -> None:
        """Test angle section generation."""
        section = Section(
            name="L4x4x1/4",
            shape=SectionShape.L,
            A=0.0012,
            Ix=8.3e-6,
            Iy=8.3e-6,
            d=0.102,
            bf=0.102,
            t=0.00635,
        )
        profile = generator.generate(section)

        assert profile.n_vertices == 6  # L-shape
        assert not profile.has_holes

    def test_channel_section(self, generator: ProfileGenerator) -> None:
        """Test channel section generation."""
        section = Section(
            name="C10x15.3",
            shape=SectionShape.C,
            A=0.0029,
            Ix=6.7e-5,
            Iy=6.2e-6,
            d=0.254,
            bf=0.069,
            tf=0.0102,
            tw=0.0065,
        )
        profile = generator.generate(section)

        assert profile.n_vertices == 8  # C-shape
        assert not profile.has_holes

    def test_t_section(self, generator: ProfileGenerator) -> None:
        """Test T-section generation."""
        section = Section(
            name="WT6x13",
            shape=SectionShape.WT,
            A=0.0025,
            Ix=3.3e-5,
            Iy=1.0e-5,
            d=0.155,
            bf=0.165,
            tf=0.0096,
            tw=0.0058,
        )
        profile = generator.generate(section)

        assert profile.n_vertices == 8  # T-shape
        assert not profile.has_holes


class TestExtrudedRenderer:
    """Tests for ExtrudedRenderer."""

    @pytest.fixture
    def renderer(self) -> ExtrudedRenderer:
        """Create renderer instance."""
        return ExtrudedRenderer()

    @pytest.fixture
    def simple_model(self) -> StructuralModel:
        """Create simple model with one frame."""
        model = StructuralModel()
        model.add_node(0.0, 0.0, 0.0, restraint=FIXED)
        model.add_node(5.0, 0.0, 0.0)
        model.add_frame(1, 2, "A36", "W12x26")
        return model

    @pytest.fixture
    def sections(self) -> dict[str, Section]:
        """Create sections dictionary."""
        return {
            "W12x26": Section(
                name="W12x26",
                shape=SectionShape.W,
                A=0.0049,
                Ix=8.55e-5,
                Iy=1.74e-5,
                d=0.31,
                bf=0.165,
                tf=0.0096,
                tw=0.0058,
            )
        }

    def test_default_settings(self, renderer: ExtrudedRenderer) -> None:
        """Test default settings."""
        assert renderer.settings.show_end_caps is True
        assert renderer.settings.smooth_shading is True
        assert renderer.settings.high_detail_segments == 32

    def test_build_extruded_mesh_empty_model(
        self, renderer: ExtrudedRenderer
    ) -> None:
        """Test with empty model."""
        model = StructuralModel()
        mesh = renderer.build_extruded_mesh(model, {})
        assert mesh.n_points == 0

    def test_build_extruded_mesh_no_sections(
        self, renderer: ExtrudedRenderer, simple_model: StructuralModel
    ) -> None:
        """Test with model but no section data."""
        mesh = renderer.build_extruded_mesh(simple_model, {})
        assert mesh.n_points == 0

    def test_build_extruded_mesh_with_section(
        self,
        renderer: ExtrudedRenderer,
        simple_model: StructuralModel,
        sections: dict[str, Section],
    ) -> None:
        """Test building extruded mesh."""
        mesh = renderer.build_extruded_mesh(simple_model, sections)

        # Should have points for start and end profiles
        # I-section has 12 vertices, so 24 total (start + end)
        assert mesh.n_points == 24
        assert mesh.n_cells > 0  # Should have faces

    def test_build_extruded_mesh_by_material(
        self,
        renderer: ExtrudedRenderer,
        simple_model: StructuralModel,
        sections: dict[str, Section],
    ) -> None:
        """Test building mesh grouped by material."""
        meshes = renderer.build_extruded_mesh_by_material(simple_model, sections)

        assert "A36" in meshes
        assert meshes["A36"].n_points > 0

    def test_clear_cache(self, renderer: ExtrudedRenderer) -> None:
        """Test cache clearing."""
        # Should not raise
        renderer.clear_cache()

    def test_triangulate_polygon_triangle(self, renderer: ExtrudedRenderer) -> None:
        """Test triangulation of triangle."""
        vertices = np.array([[0, 0], [1, 0], [0.5, 1]])
        triangles = renderer._triangulate_polygon(vertices)

        assert len(triangles) == 1
        assert triangles[0] == (0, 1, 2)

    def test_triangulate_polygon_quad(self, renderer: ExtrudedRenderer) -> None:
        """Test triangulation of quadrilateral."""
        vertices = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        triangles = renderer._triangulate_polygon(vertices)

        assert len(triangles) == 2

    def test_triangulate_polygon_empty(self, renderer: ExtrudedRenderer) -> None:
        """Test triangulation of empty polygon."""
        vertices = np.array([]).reshape(0, 2)
        triangles = renderer._triangulate_polygon(vertices)

        assert len(triangles) == 0


class TestExtrudedSettings:
    """Tests for ExtrudedSettings."""

    def test_default_values(self) -> None:
        """Test default settings values."""
        settings = ExtrudedSettings()

        assert settings.lod_high_threshold == 50.0
        assert settings.lod_medium_threshold == 200.0
        assert settings.high_detail_segments == 32
        assert settings.medium_detail_segments == 16
        assert settings.low_detail_segments == 8
        assert settings.show_end_caps is True
        assert settings.smooth_shading is True

    def test_custom_values(self) -> None:
        """Test custom settings values."""
        settings = ExtrudedSettings(
            high_detail_segments=48,
            show_end_caps=False,
        )

        assert settings.high_detail_segments == 48
        assert settings.show_end_caps is False


class TestMaterialColors:
    """Tests for material color functions."""

    def test_steel_color(self) -> None:
        """Test steel materials get gray color."""
        assert get_color_for_material("A36") == "#708090"
        assert get_color_for_material("A572") == "#708090"
        assert get_color_for_material("STEEL_A992") == "#708090"

    def test_concrete_color(self) -> None:
        """Test concrete materials."""
        assert get_color_for_material("H25") == "#A9A9A9"
        assert get_color_for_material("concrete_H30") == "#A9A9A9"

    def test_unknown_material(self) -> None:
        """Test unknown material gets default color."""
        assert get_color_for_material("UNKNOWN") == "#4169E1"

    def test_case_insensitive(self) -> None:
        """Test color matching is case insensitive."""
        assert get_color_for_material("a36") == "#708090"
        assert get_color_for_material("A36") == "#708090"
        assert get_color_for_material("Steel_A36") == "#708090"


class TestMultiFrameExtrusion:
    """Tests for multi-frame extrusion."""

    @pytest.fixture
    def portal_model(self) -> StructuralModel:
        """Create a portal frame model."""
        model = StructuralModel()
        # Columns
        model.add_node(0.0, 0.0, 0.0, restraint=FIXED)
        model.add_node(0.0, 0.0, 3.0)
        model.add_node(5.0, 0.0, 0.0, restraint=FIXED)
        model.add_node(5.0, 0.0, 3.0)
        # Frames
        model.add_frame(1, 2, "A36", "W12x26")  # Left column
        model.add_frame(2, 4, "A36", "W12x26")  # Beam
        model.add_frame(3, 4, "A36", "W12x26")  # Right column
        return model

    @pytest.fixture
    def sections(self) -> dict[str, Section]:
        """Create sections dictionary."""
        return {
            "W12x26": Section(
                name="W12x26",
                shape=SectionShape.W,
                A=0.0049,
                Ix=8.55e-5,
                Iy=1.74e-5,
                d=0.31,
                bf=0.165,
                tf=0.0096,
                tw=0.0058,
            )
        }

    def test_multi_frame_extrusion(
        self,
        portal_model: StructuralModel,
        sections: dict[str, Section],
    ) -> None:
        """Test extrusion of multiple frames."""
        renderer = ExtrudedRenderer()
        mesh = renderer.build_extruded_mesh(portal_model, sections)

        # 3 frames * 24 points each (12 vertices start + 12 end)
        assert mesh.n_points == 72

"""
Unit tests for viewport presentation layer.

Tests render modes, mesh building, and deformed rendering.
Qt widget tests are skipped without Qt application context.
"""

from uuid import uuid4

import numpy as np
import pytest

from paz.domain.model import StructuralModel
from paz.domain.model.restraint import FIXED
from paz.domain.results import AnalysisResults
from paz.domain.results.nodal_results import NodalDisplacement
from paz.presentation.viewport.deformed_renderer import DeformedRenderer
from paz.presentation.viewport.mesh_builder import MeshBuilder
from paz.presentation.viewport.render_modes import (
    ColorMapType,
    DisplacementComponent,
    RenderMode,
    ViewportSettings,
)


class TestViewportSettings:
    """Tests for ViewportSettings configuration."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        settings = ViewportSettings()

        assert settings.render_mode == RenderMode.WIREFRAME
        assert settings.displacement_component == DisplacementComponent.TOTAL
        assert settings.color_map == ColorMapType.VIRIDIS
        assert settings.deformation_scale == 100.0
        assert settings.show_original is True
        assert settings.show_deformed is True
        assert settings.show_nodes is True
        assert settings.show_supports is True
        assert settings.original_opacity == 0.3
        assert settings.line_width == 2.0
        assert settings.node_size == 10.0

    def test_custom_settings(self) -> None:
        """Test custom settings values."""
        settings = ViewportSettings(
            render_mode=RenderMode.SOLID,
            deformation_scale=500.0,
            color_map=ColorMapType.RAINBOW,
            show_original=False,
        )

        assert settings.render_mode == RenderMode.SOLID
        assert settings.deformation_scale == 500.0
        assert settings.color_map == ColorMapType.RAINBOW
        assert settings.show_original is False

    def test_settings_validation_scale(self) -> None:
        """Test validation rejects invalid scale."""
        settings = ViewportSettings(deformation_scale=0.5)

        with pytest.raises(ValueError, match="Deformation scale"):
            settings.validate()

    def test_settings_validation_opacity(self) -> None:
        """Test validation rejects invalid opacity."""
        settings = ViewportSettings(original_opacity=1.5)

        with pytest.raises(ValueError, match="Opacity"):
            settings.validate()

    def test_settings_validation_node_size(self) -> None:
        """Test validation rejects invalid node size."""
        settings = ViewportSettings(node_size=-1.0)

        with pytest.raises(ValueError, match="Node size"):
            settings.validate()

    def test_settings_copy(self) -> None:
        """Test settings copy creates independent copy."""
        original = ViewportSettings(deformation_scale=200.0)
        copy = original.copy()

        copy.deformation_scale = 500.0

        assert original.deformation_scale == 200.0
        assert copy.deformation_scale == 500.0


class TestRenderModeEnums:
    """Tests for rendering enums."""

    def test_render_mode_values(self) -> None:
        """Test RenderMode enum values exist."""
        assert RenderMode.WIREFRAME is not None
        assert RenderMode.SOLID is not None
        assert RenderMode.WIREFRAME_SOLID is not None

    def test_displacement_component_values(self) -> None:
        """Test DisplacementComponent enum values."""
        assert DisplacementComponent.UX.value == "Ux"
        assert DisplacementComponent.UY.value == "Uy"
        assert DisplacementComponent.UZ.value == "Uz"
        assert DisplacementComponent.TOTAL.value == "Total"

    def test_colormap_values(self) -> None:
        """Test ColorMapType enum values."""
        assert ColorMapType.VIRIDIS.value == "viridis"
        assert ColorMapType.RAINBOW.value == "rainbow"
        assert ColorMapType.COOLWARM.value == "coolwarm"
        assert ColorMapType.JET.value == "jet"


class TestMeshBuilder:
    """Tests for MeshBuilder mesh generation."""

    @pytest.fixture
    def simple_model(self) -> StructuralModel:
        """Create a simple 2-node, 1-frame model."""
        model = StructuralModel()
        model.add_node(0.0, 0.0, 0.0, restraint=FIXED)
        model.add_node(5.0, 0.0, 0.0)
        model.add_frame(1, 2, "A36", "W12x26")
        return model

    @pytest.fixture
    def three_frame_model(self) -> StructuralModel:
        """Create a 4-node, 3-frame L-shaped model."""
        model = StructuralModel()
        model.add_node(0.0, 0.0, 0.0, restraint=FIXED)
        model.add_node(5.0, 0.0, 0.0)
        model.add_node(5.0, 5.0, 0.0)
        model.add_node(5.0, 5.0, 3.0, restraint=FIXED)

        model.add_frame(1, 2, "A36", "W12x26")
        model.add_frame(2, 3, "A36", "W12x26")
        model.add_frame(3, 4, "A36", "W12x26")

        return model

    def test_build_frame_mesh_empty_model(self) -> None:
        """Test mesh builder with empty model."""
        model = StructuralModel()
        builder = MeshBuilder()
        mesh = builder.build_frame_mesh(model)

        assert mesh.n_points == 0

    def test_build_frame_mesh_single_frame(self, simple_model: StructuralModel) -> None:
        """Test mesh builder with single frame."""
        builder = MeshBuilder()
        mesh = builder.build_frame_mesh(simple_model)

        assert mesh.n_points == 2
        assert len(mesh.lines) > 0

    def test_build_frame_mesh_multiple_frames(
        self, three_frame_model: StructuralModel
    ) -> None:
        """Test mesh builder with multiple frames."""
        builder = MeshBuilder()
        mesh = builder.build_frame_mesh(three_frame_model)

        # 3 frames * 2 points each = 6 points
        assert mesh.n_points == 6

    def test_build_node_points(self, simple_model: StructuralModel) -> None:
        """Test node point cloud generation."""
        builder = MeshBuilder()
        points = builder.build_node_points(simple_model)

        assert points.n_points == 2
        assert "node_id" in points.array_names

    def test_build_node_points_empty_model(self) -> None:
        """Test node points with empty model."""
        model = StructuralModel()
        builder = MeshBuilder()
        points = builder.build_node_points(model)

        assert points.n_points == 0

    def test_build_support_glyphs(self, simple_model: StructuralModel) -> None:
        """Test support glyph generation."""
        builder = MeshBuilder()
        glyphs = builder.build_support_glyphs(simple_model)

        # Should have 1 support (fixed node at origin)
        assert glyphs is not None
        assert glyphs.n_points > 0

    def test_build_support_glyphs_no_supports(self) -> None:
        """Test support glyphs with no supported nodes."""
        model = StructuralModel()
        model.add_node(0.0, 0.0, 0.0)  # Free node
        model.add_node(1.0, 0.0, 0.0)  # Free node
        model.add_frame(1, 2, "A36", "W12x26")

        builder = MeshBuilder()
        glyphs = builder.build_support_glyphs(model)

        assert glyphs is None

    def test_build_node_labels(self, simple_model: StructuralModel) -> None:
        """Test node label generation."""
        builder = MeshBuilder()
        positions, labels = builder.build_node_labels(simple_model)

        assert len(positions) == 2
        assert len(labels) == 2
        assert "1" in labels
        assert "2" in labels

    def test_build_frame_labels(self, simple_model: StructuralModel) -> None:
        """Test frame label generation at midpoints."""
        builder = MeshBuilder()
        positions, labels = builder.build_frame_labels(simple_model)

        assert len(positions) == 1
        assert len(labels) == 1
        # Midpoint of frame from (0,0,0) to (5,0,0) is (2.5,0,0)
        assert positions[0][0] == pytest.approx(2.5)


class TestDeformedRenderer:
    """Tests for DeformedRenderer deformation calculations."""

    @pytest.fixture
    def model_with_results(self) -> tuple[StructuralModel, AnalysisResults]:
        """Create model with analysis results."""
        model = StructuralModel()
        model.add_node(0.0, 0.0, 0.0, restraint=FIXED)
        model.add_node(5.0, 0.0, 0.0)
        model.add_frame(1, 2, "A36", "W12x26")

        load_case_id = uuid4()
        results = AnalysisResults(load_case_id=load_case_id, success=True)
        results.add_displacement(NodalDisplacement(node_id=1, Ux=0.0, Uy=0.0, Uz=0.0))
        results.add_displacement(
            NodalDisplacement(node_id=2, Ux=0.001, Uy=0.002, Uz=-0.005)
        )

        return model, results

    def test_build_deformed_mesh(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test deformed mesh generation."""
        model, results = model_with_results
        renderer = DeformedRenderer(interpolation_points=5)

        mesh, scalars = renderer.build_deformed_mesh(
            model=model,
            results=results,
            scale=100.0,
            component=DisplacementComponent.TOTAL,
        )

        assert mesh.n_points == 5
        assert len(scalars) == 5

    def test_deformed_mesh_interpolation_points(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test different interpolation point counts."""
        model, results = model_with_results
        renderer = DeformedRenderer(interpolation_points=20)

        mesh, scalars = renderer.build_deformed_mesh(
            model=model,
            results=results,
            scale=100.0,
            component=DisplacementComponent.TOTAL,
        )

        assert mesh.n_points == 20
        assert len(scalars) == 20

    def test_scalar_values_ux_component(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test scalar values for Ux component."""
        model, results = model_with_results
        renderer = DeformedRenderer(interpolation_points=2)

        mesh, scalars = renderer.build_deformed_mesh(
            model=model,
            results=results,
            scale=1.0,
            component=DisplacementComponent.UX,
        )

        # First point: node 1 with Ux=0
        # Last point: node 2 with Ux=0.001
        assert scalars[0] == pytest.approx(0.0)
        assert scalars[-1] == pytest.approx(0.001)

    def test_scalar_values_total_component(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test scalar values for Total (magnitude) component."""
        model, results = model_with_results
        renderer = DeformedRenderer(interpolation_points=2)

        mesh, scalars = renderer.build_deformed_mesh(
            model=model,
            results=results,
            scale=1.0,
            component=DisplacementComponent.TOTAL,
        )

        # Node 1: magnitude = 0
        assert scalars[0] == pytest.approx(0.0)

        # Node 2: magnitude = sqrt(0.001^2 + 0.002^2 + 0.005^2)
        expected = np.sqrt(0.001**2 + 0.002**2 + 0.005**2)
        assert scalars[-1] == pytest.approx(expected)

    def test_deformed_position_calculation(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test single node deformed position."""
        model, results = model_with_results
        renderer = DeformedRenderer()

        pos = renderer.get_deformed_node_position(
            node_id=2,
            model=model,
            results=results,
            scale=100.0,
        )

        # Original: (5.0, 0.0, 0.0)
        # Displacement: (0.001, 0.002, -0.005)
        # Deformed: (5.0 + 100*0.001, 0.0 + 100*0.002, 0.0 + 100*(-0.005))
        assert pos[0] == pytest.approx(5.1)
        assert pos[1] == pytest.approx(0.2)
        assert pos[2] == pytest.approx(-0.5)

    def test_deformed_position_no_displacement(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test deformed position for node without displacement data."""
        model, results = model_with_results

        # Add node without displacement
        model.add_node(10.0, 0.0, 0.0)

        renderer = DeformedRenderer()
        pos = renderer.get_deformed_node_position(
            node_id=3,
            model=model,
            results=results,
            scale=100.0,
        )

        # Should return original position
        assert pos[0] == pytest.approx(10.0)
        assert pos[1] == pytest.approx(0.0)
        assert pos[2] == pytest.approx(0.0)

    def test_displacement_range(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test displacement range calculation."""
        model, results = model_with_results
        renderer = DeformedRenderer()

        min_val, max_val = renderer.get_displacement_range(
            results=results,
            component=DisplacementComponent.TOTAL,
        )

        assert min_val == pytest.approx(0.0)
        expected_max = np.sqrt(0.001**2 + 0.002**2 + 0.005**2)
        assert max_val == pytest.approx(expected_max)

    def test_interpolation_points_setter(self) -> None:
        """Test interpolation points setter enforces minimum."""
        renderer = DeformedRenderer(interpolation_points=10)
        assert renderer.interpolation_points == 10

        renderer.interpolation_points = 1  # Should be clamped to 2
        assert renderer.interpolation_points == 2

    def test_build_deformed_nodes(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test deformed node point cloud generation."""
        model, results = model_with_results
        renderer = DeformedRenderer()

        points, scalars = renderer.build_deformed_nodes(
            model=model,
            results=results,
            scale=100.0,
            component=DisplacementComponent.TOTAL,
        )

        assert points.n_points == 2
        assert len(scalars) == 2
        assert "node_id" in points.array_names


class TestEmptyModelEdgeCases:
    """Tests for edge cases with empty or minimal models."""

    def test_empty_model_frame_mesh(self) -> None:
        """Test frame mesh with empty model."""
        model = StructuralModel()
        builder = MeshBuilder()
        mesh = builder.build_frame_mesh(model)

        assert mesh.n_points == 0

    def test_empty_model_deformed_mesh(self) -> None:
        """Test deformed mesh with empty model."""
        model = StructuralModel()
        results = AnalysisResults(load_case_id=uuid4(), success=True)
        renderer = DeformedRenderer()

        mesh, scalars = renderer.build_deformed_mesh(
            model=model,
            results=results,
            scale=100.0,
            component=DisplacementComponent.TOTAL,
        )

        assert mesh.n_points == 0
        assert len(scalars) == 0

    def test_empty_results_displacement_range(self) -> None:
        """Test displacement range with empty results."""
        results = AnalysisResults(load_case_id=uuid4(), success=True)
        renderer = DeformedRenderer()

        min_val, max_val = renderer.get_displacement_range(
            results=results,
            component=DisplacementComponent.TOTAL,
        )

        assert min_val == 0.0
        assert max_val == 0.0

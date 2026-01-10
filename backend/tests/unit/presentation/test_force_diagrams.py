"""
Unit tests for force diagram rendering.

Tests ForceDiagramRenderer, ForceType, and DiagramSettings.
"""

from uuid import uuid4

import numpy as np
import pytest

from paz.domain.model import StructuralModel
from paz.domain.model.restraint import FIXED
from paz.domain.results import AnalysisResults
from paz.domain.results.frame_results import FrameForces, FrameResult
from paz.presentation.viewport.force_diagrams import (
    DiagramSettings,
    ForceDiagramRenderer,
    ForceType,
)


class TestForceType:
    """Tests for ForceType enum."""

    def test_force_type_values(self) -> None:
        """Test ForceType enum values."""
        assert ForceType.P.value == "P"
        assert ForceType.V2.value == "V2"
        assert ForceType.V3.value == "V3"
        assert ForceType.T.value == "T"
        assert ForceType.M2.value == "M2"
        assert ForceType.M3.value == "M3"

    def test_all_force_types_exist(self) -> None:
        """Test all expected force types are defined."""
        force_types = list(ForceType)
        assert len(force_types) == 6


class TestDiagramSettings:
    """Tests for DiagramSettings configuration."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        settings = DiagramSettings()

        assert settings.force_type == ForceType.M3
        assert settings.scale == 1.0
        assert settings.positive_color == "red"
        assert settings.negative_color == "blue"
        assert settings.line_width == 2.0
        assert settings.fill_opacity == 0.3
        assert settings.show_values is True
        assert settings.show_max_values is True
        assert settings.interpolation_points == 20

    def test_custom_settings(self) -> None:
        """Test custom settings values."""
        settings = DiagramSettings(
            force_type=ForceType.V2,
            scale=0.5,
            positive_color="green",
            interpolation_points=10,
        )

        assert settings.force_type == ForceType.V2
        assert settings.scale == 0.5
        assert settings.positive_color == "green"
        assert settings.interpolation_points == 10

    def test_diagram_directions_defined(self) -> None:
        """Test DIAGRAM_DIRECTIONS class variable is defined."""
        assert ForceType.M3 in DiagramSettings.DIAGRAM_DIRECTIONS
        assert ForceType.V2 in DiagramSettings.DIAGRAM_DIRECTIONS
        assert ForceType.P in DiagramSettings.DIAGRAM_DIRECTIONS


class TestForceDiagramRenderer:
    """Tests for ForceDiagramRenderer."""

    @pytest.fixture
    def simple_model(self) -> StructuralModel:
        """Create a simple cantilever model."""
        model = StructuralModel()
        model.add_node(0.0, 0.0, 0.0, restraint=FIXED)
        model.add_node(5.0, 0.0, 0.0)
        model.add_frame(1, 2, "A36", "W12x26")
        return model

    @pytest.fixture
    def model_with_results(self) -> tuple[StructuralModel, AnalysisResults]:
        """Create model with frame force results."""
        model = StructuralModel()
        model.add_node(0.0, 0.0, 0.0, restraint=FIXED)
        model.add_node(5.0, 0.0, 0.0)
        model.add_frame(1, 2, "A36", "W12x26")

        load_case_id = uuid4()
        results = AnalysisResults(load_case_id=load_case_id, success=True)

        # Add frame forces (simulating a cantilever with tip load)
        frame_result = FrameResult(frame_id=1, forces=[
            FrameForces(location=0.0, P=0.0, V2=10.0, V3=0.0, T=0.0, M2=0.0, M3=-50.0),
            FrameForces(location=0.5, P=0.0, V2=10.0, V3=0.0, T=0.0, M2=0.0, M3=-25.0),
            FrameForces(location=1.0, P=0.0, V2=10.0, V3=0.0, T=0.0, M2=0.0, M3=0.0),
        ])
        results.add_frame_result(frame_result)

        return model, results

    def test_default_settings(self) -> None:
        """Test renderer initializes with default settings."""
        renderer = ForceDiagramRenderer()
        assert renderer.settings.force_type == ForceType.M3
        assert renderer.settings.scale == 1.0

    def test_custom_settings(self) -> None:
        """Test renderer accepts custom settings."""
        settings = DiagramSettings(force_type=ForceType.V2, scale=0.5)
        renderer = ForceDiagramRenderer(settings=settings)

        assert renderer.settings.force_type == ForceType.V2
        assert renderer.settings.scale == 0.5

    def test_build_diagram_mesh_empty(self) -> None:
        """Test diagram mesh with empty model."""
        model = StructuralModel()
        results = AnalysisResults(load_case_id=uuid4(), success=True)
        renderer = ForceDiagramRenderer()

        mesh, scalars = renderer.build_diagram_mesh(model, results)

        assert mesh.n_points == 0
        assert len(scalars) == 0

    def test_build_diagram_mesh_no_results(
        self, simple_model: StructuralModel
    ) -> None:
        """Test diagram mesh with no frame results."""
        results = AnalysisResults(load_case_id=uuid4(), success=True)
        renderer = ForceDiagramRenderer()

        mesh, scalars = renderer.build_diagram_mesh(simple_model, results)

        assert mesh.n_points == 0
        assert len(scalars) == 0

    def test_build_diagram_mesh_with_results(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test diagram mesh generation with frame results."""
        model, results = model_with_results
        settings = DiagramSettings(interpolation_points=5)
        renderer = ForceDiagramRenderer(settings=settings)

        mesh, scalars = renderer.build_diagram_mesh(model, results, ForceType.M3)

        # Should have 5 points for the diagram line
        assert mesh.n_points == 5
        assert len(scalars) == 5

    def test_build_filled_diagram_mesh(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test filled diagram mesh generation."""
        model, results = model_with_results
        settings = DiagramSettings(interpolation_points=5)
        renderer = ForceDiagramRenderer(settings=settings)

        mesh, scalars = renderer.build_filled_diagram_mesh(model, results, ForceType.M3)

        # Filled mesh has base points + diagram points
        assert mesh.n_points == 10  # 5 base + 5 diagram
        assert len(scalars) == 10

    def test_scalar_values_m3(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test scalar values for M3 component."""
        model, results = model_with_results
        settings = DiagramSettings(interpolation_points=3)
        renderer = ForceDiagramRenderer(settings=settings)

        mesh, scalars = renderer.build_diagram_mesh(model, results, ForceType.M3)

        # M3 values: -50, -25, 0 at locations 0, 0.5, 1
        assert scalars[0] == pytest.approx(-50.0)
        assert scalars[-1] == pytest.approx(0.0)

    def test_scalar_values_v2(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test scalar values for V2 component."""
        model, results = model_with_results
        settings = DiagramSettings(interpolation_points=3)
        renderer = ForceDiagramRenderer(settings=settings)

        mesh, scalars = renderer.build_diagram_mesh(model, results, ForceType.V2)

        # V2 is constant at 10.0
        assert all(s == pytest.approx(10.0) for s in scalars)

    def test_get_global_extremes(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test global extreme values calculation."""
        _, results = model_with_results
        renderer = ForceDiagramRenderer()

        extremes = renderer.get_global_extremes(results, ForceType.M3)

        assert extremes["max"] == pytest.approx(0.0)
        assert extremes["min"] == pytest.approx(-50.0)
        assert extremes["abs_max"] == pytest.approx(50.0)

    def test_get_global_extremes_empty(self) -> None:
        """Test global extremes with empty results."""
        results = AnalysisResults(load_case_id=uuid4(), success=True)
        renderer = ForceDiagramRenderer()

        extremes = renderer.get_global_extremes(results, ForceType.M3)

        assert extremes["max"] == 0.0
        assert extremes["min"] == 0.0
        assert extremes["abs_max"] == 0.0

    def test_get_frame_with_max_value(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test finding frame with maximum value."""
        _, results = model_with_results
        renderer = ForceDiagramRenderer()

        frame_id, max_val = renderer.get_frame_with_max_value(results, ForceType.M3)

        assert frame_id == 1
        assert max_val == pytest.approx(-50.0)

    def test_get_frame_with_max_value_empty(self) -> None:
        """Test finding max frame with empty results."""
        results = AnalysisResults(load_case_id=uuid4(), success=True)
        renderer = ForceDiagramRenderer()

        frame_id, max_val = renderer.get_frame_with_max_value(results, ForceType.M3)

        assert frame_id is None
        assert max_val == 0.0

    def test_get_value_labels(
        self, model_with_results: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test value label generation."""
        model, results = model_with_results
        renderer = ForceDiagramRenderer()

        positions, labels = renderer.get_value_labels(model, results, ForceType.M3)

        # For cantilever with M=0 at free end, only start label is generated
        # (values ~0 are not labeled)
        assert len(positions) >= 1
        assert len(labels) >= 1
        # Labels should be string representations of values
        assert any("-50" in label for label in labels)

    def test_settings_property(self) -> None:
        """Test settings getter and setter."""
        renderer = ForceDiagramRenderer()
        original_settings = renderer.settings

        new_settings = DiagramSettings(scale=2.0)
        renderer.settings = new_settings

        assert renderer.settings.scale == 2.0
        assert renderer.settings.scale != original_settings.scale


class TestMultiFrameModel:
    """Tests with multiple frames."""

    @pytest.fixture
    def portal_frame_model(self) -> tuple[StructuralModel, AnalysisResults]:
        """Create a simple portal frame model."""
        model = StructuralModel()
        # Columns
        model.add_node(0.0, 0.0, 0.0, restraint=FIXED)  # 1
        model.add_node(0.0, 0.0, 3.0)  # 2
        model.add_node(5.0, 0.0, 0.0, restraint=FIXED)  # 3
        model.add_node(5.0, 0.0, 3.0)  # 4

        # Left column
        model.add_frame(1, 2, "A36", "W12x26")  # Frame 1
        # Beam
        model.add_frame(2, 4, "A36", "W12x26")  # Frame 2
        # Right column
        model.add_frame(3, 4, "A36", "W12x26")  # Frame 3

        load_case_id = uuid4()
        results = AnalysisResults(load_case_id=load_case_id, success=True)

        # Add frame results
        results.add_frame_result(FrameResult(frame_id=1, forces=[
            FrameForces(location=0.0, P=-10.0, V2=5.0, M3=15.0),
            FrameForces(location=1.0, P=-10.0, V2=5.0, M3=0.0),
        ]))
        results.add_frame_result(FrameResult(frame_id=2, forces=[
            FrameForces(location=0.0, P=0.0, V2=10.0, M3=-20.0),
            FrameForces(location=0.5, P=0.0, V2=0.0, M3=5.0),
            FrameForces(location=1.0, P=0.0, V2=-10.0, M3=-20.0),
        ]))
        results.add_frame_result(FrameResult(frame_id=3, forces=[
            FrameForces(location=0.0, P=-10.0, V2=-5.0, M3=-15.0),
            FrameForces(location=1.0, P=-10.0, V2=-5.0, M3=0.0),
        ]))

        return model, results

    def test_multiple_frames_diagram(
        self, portal_frame_model: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test diagram generation for multiple frames."""
        model, results = portal_frame_model
        settings = DiagramSettings(interpolation_points=5)
        renderer = ForceDiagramRenderer(settings=settings)

        mesh, scalars = renderer.build_diagram_mesh(model, results, ForceType.M3)

        # Should have points for all 3 frames
        assert mesh.n_points == 15  # 3 frames * 5 points

    def test_find_max_in_multiple_frames(
        self, portal_frame_model: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test finding max value across multiple frames."""
        _, results = portal_frame_model
        renderer = ForceDiagramRenderer()

        frame_id, max_val = renderer.get_frame_with_max_value(results, ForceType.M3)

        # Max moment is in beam (frame 2) at -20.0
        assert frame_id == 2
        assert abs(max_val) == pytest.approx(20.0)

    def test_global_extremes_multiple_frames(
        self, portal_frame_model: tuple[StructuralModel, AnalysisResults]
    ) -> None:
        """Test global extremes with multiple frames."""
        _, results = portal_frame_model
        renderer = ForceDiagramRenderer()

        extremes = renderer.get_global_extremes(results, ForceType.M3)

        assert extremes["max"] == pytest.approx(15.0)  # Left column base
        assert extremes["min"] == pytest.approx(-20.0)  # Beam end
        assert extremes["abs_max"] == pytest.approx(20.0)

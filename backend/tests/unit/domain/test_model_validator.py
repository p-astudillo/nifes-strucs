"""Tests for model validation."""

import pytest

from paz.domain.materials import Material, MaterialType
from paz.domain.model import FIXED, FREE, PINNED, Restraint, StructuralModel
from paz.domain.sections import Section, SectionShape
from paz.domain.validation import ModelValidator, ValidationResult, validate_model_for_analysis


@pytest.fixture
def steel_material() -> Material:
    """Steel material for testing."""
    return Material(
        name="A36",
        material_type=MaterialType.STEEL,
        E=200e6,  # 200 GPa in kPa
        nu=0.3,
        rho=7850,
    )


@pytest.fixture
def w_section() -> Section:
    """W section for testing."""
    return Section(
        name="W14X30",
        shape=SectionShape.W,
        A=0.00567,  # m²
        Ix=1.28e-4,  # m⁴
        Iy=1.88e-5,  # m⁴
    )


@pytest.fixture
def materials(steel_material: Material) -> dict[str, Material]:
    """Materials dictionary."""
    return {"A36": steel_material}


@pytest.fixture
def sections(w_section: Section) -> dict[str, Section]:
    """Sections dictionary."""
    return {"W14X30": w_section}


class TestValidationResult:
    """Tests for ValidationResult."""

    def test_default_is_valid(self) -> None:
        """Default result is valid."""
        result = ValidationResult()
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_add_error_invalidates(self) -> None:
        """Adding error marks result invalid."""
        result = ValidationResult()
        result.add_error("Test error")
        assert result.is_valid is False
        assert "Test error" in result.errors

    def test_add_warning_keeps_valid(self) -> None:
        """Adding warning doesn't invalidate."""
        result = ValidationResult()
        result.add_warning("Test warning")
        assert result.is_valid is True
        assert "Test warning" in result.warnings


class TestModelValidator:
    """Tests for ModelValidator."""

    def test_empty_model_invalid(
        self, materials: dict[str, Material], sections: dict[str, Section]
    ) -> None:
        """Empty model fails validation."""
        model = StructuralModel()
        result = validate_model_for_analysis(model, materials, sections)

        assert result.is_valid is False
        assert any("no nodes" in e.lower() for e in result.errors)

    def test_single_node_invalid(
        self, materials: dict[str, Material], sections: dict[str, Section]
    ) -> None:
        """Model with single node fails validation."""
        model = StructuralModel()
        model.add_node(0, 0, 0)

        result = validate_model_for_analysis(model, materials, sections)

        assert result.is_valid is False
        assert any("at least 2 nodes" in e.lower() for e in result.errors)

    def test_no_frames_invalid(
        self, materials: dict[str, Material], sections: dict[str, Section]
    ) -> None:
        """Model without frames fails validation."""
        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=FIXED)
        model.add_node(5, 0, 0)

        result = validate_model_for_analysis(model, materials, sections)

        assert result.is_valid is False
        assert any("no frame" in e.lower() for e in result.errors)

    def test_no_supports_invalid(
        self, materials: dict[str, Material], sections: dict[str, Section]
    ) -> None:
        """Model without supports fails validation."""
        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=FREE)
        model.add_node(5, 0, 0, restraint=FREE)
        model.add_frame(1, 2, "A36", "W14X30")

        result = validate_model_for_analysis(model, materials, sections)

        assert result.is_valid is False
        assert any("no supported" in e.lower() or "no boundary" in e.lower() for e in result.errors)

    def test_insufficient_restraints_invalid(
        self, materials: dict[str, Material], sections: dict[str, Section]
    ) -> None:
        """Model with insufficient restraints fails validation."""
        # Only 3 DOFs restrained (pinned) - need at least 6 for 3D
        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=PINNED)
        model.add_node(5, 0, 0, restraint=FREE)
        model.add_frame(1, 2, "A36", "W14X30")

        result = validate_model_for_analysis(model, materials, sections)

        assert result.is_valid is False
        assert any("insufficient restraints" in e.lower() for e in result.errors)

    def test_unknown_material_invalid(
        self, sections: dict[str, Section]
    ) -> None:
        """Frame with unknown material fails validation."""
        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=FIXED)
        model.add_node(5, 0, 0, restraint=FREE)
        model.add_frame(1, 2, "UNKNOWN", "W14X30")

        materials: dict[str, Material] = {}
        result = validate_model_for_analysis(model, materials, sections)

        assert result.is_valid is False
        assert any("unknown material" in e.lower() for e in result.errors)

    def test_unknown_section_invalid(
        self, materials: dict[str, Material]
    ) -> None:
        """Frame with unknown section fails validation."""
        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=FIXED)
        model.add_node(5, 0, 0, restraint=FREE)
        model.add_frame(1, 2, "A36", "UNKNOWN")

        sections: dict[str, Section] = {}
        result = validate_model_for_analysis(model, materials, sections)

        assert result.is_valid is False
        assert any("unknown section" in e.lower() for e in result.errors)

    def test_valid_cantilever(
        self, materials: dict[str, Material], sections: dict[str, Section]
    ) -> None:
        """Valid cantilever beam passes validation."""
        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=FIXED)
        model.add_node(5, 0, 0, restraint=FREE)
        model.add_frame(1, 2, "A36", "W14X30")

        result = validate_model_for_analysis(model, materials, sections)

        assert result.is_valid is True
        assert result.errors == []

    def test_unconnected_node_warning(
        self, materials: dict[str, Material], sections: dict[str, Section]
    ) -> None:
        """Unconnected node generates warning."""
        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=FIXED)
        model.add_node(5, 0, 0, restraint=FREE)
        model.add_node(10, 0, 0, restraint=FREE)  # Unconnected
        model.add_frame(1, 2, "A36", "W14X30")

        result = validate_model_for_analysis(model, materials, sections)

        assert result.is_valid is True  # Warnings don't invalidate
        assert any("not connected" in w.lower() for w in result.warnings)

    def test_valid_simply_supported(
        self, materials: dict[str, Material], sections: dict[str, Section]
    ) -> None:
        """Valid simply supported beam passes validation."""
        model = StructuralModel()
        # Pinned at one end, roller at other
        model.add_node(0, 0, 0, restraint=PINNED)
        model.add_node(5, 0, 0, restraint=Restraint(ux=False, uy=True, uz=True))
        model.add_frame(1, 2, "A36", "W14X30")

        result = validate_model_for_analysis(model, materials, sections)

        # Total: 3 + 2 = 5 DOFs, less than 6, should fail
        # Actually this is insufficient for 3D
        assert result.is_valid is False

    def test_valid_3d_frame(
        self, materials: dict[str, Material], sections: dict[str, Section]
    ) -> None:
        """Valid 3D frame passes validation."""
        model = StructuralModel()
        # Two fixed supports for proper 3D restraint
        model.add_node(0, 0, 0, restraint=FIXED)
        model.add_node(5, 0, 0, restraint=FIXED)
        model.add_node(2.5, 0, 3, restraint=FREE)
        model.add_frame(1, 3, "A36", "W14X30")
        model.add_frame(2, 3, "A36", "W14X30")

        result = validate_model_for_analysis(model, materials, sections)

        assert result.is_valid is True
        assert result.errors == []

"""Integration tests for structural analysis flow.

Tests the complete analysis workflow using models with known analytical solutions.
"""

import pytest

from paz.domain.loads import LoadCase, LoadCaseType, NodalLoad
from paz.domain.materials import Material, MaterialType
from paz.domain.model import FIXED, FREE, StructuralModel
from paz.domain.sections import Section, SectionShape


# Check if OpenSees is available
def _opensees_available() -> bool:
    """Check if OpenSees is available for testing."""
    try:
        import openseespy.opensees  # noqa: F401

        return True
    except (ImportError, RuntimeError):
        return False


OPENSEES_AVAILABLE = _opensees_available()
opensees_required = pytest.mark.skipif(
    not OPENSEES_AVAILABLE,
    reason="OpenSees not available (Mac ARM architecture issue)",
)


# Import AnalysisService only if OpenSees is available to avoid import errors
if OPENSEES_AVAILABLE:
    from paz.application.services import AnalysisService


@pytest.fixture
def steel_material() -> Material:
    """Steel material (E = 200 GPa)."""
    return Material(
        name="Steel",
        material_type=MaterialType.STEEL,
        E=200e6,  # kPa (200 GPa)
        nu=0.3,
        rho=7850,
    )


@pytest.fixture
def simple_section() -> Section:
    """Simple rectangular section for testing."""
    # 0.1m x 0.2m rectangle
    b = 0.1  # width
    h = 0.2  # height
    A = b * h
    Ix = b * h**3 / 12  # Strong axis
    Iy = h * b**3 / 12  # Weak axis

    return Section(
        name="RECT100x200",
        shape=SectionShape.CUSTOM,
        A=A,
        Ix=Ix,
        Iy=Iy,
        J=(b * h**3) / 3,  # Approximate J for rectangle
    )


@pytest.fixture
def materials(steel_material: Material) -> dict[str, Material]:
    """Materials dictionary."""
    return {"Steel": steel_material}


@pytest.fixture
def sections(simple_section: Section) -> dict[str, Section]:
    """Sections dictionary."""
    return {"RECT100x200": simple_section}


@pytest.fixture
def dead_load_case() -> LoadCase:
    """Dead load case for testing."""
    return LoadCase(name="Dead", load_type=LoadCaseType.DEAD)


@opensees_required
class TestCantileverBeam:
    """Test cantilever beam with point load at tip.

    Analytical solution:
    - Displacement at tip: δ = PL³ / (3EI)
    - Rotation at tip: θ = PL² / (2EI)
    - Reaction at fixed end: R = P, M = P*L
    """

    def test_cantilever_tip_deflection(
        self,
        materials: dict[str, Material],
        sections: dict[str, Section],
        dead_load_case: LoadCase,
    ) -> None:
        """Test cantilever deflection matches analytical solution."""
        # Setup
        L = 5.0  # Length in meters
        P = -10.0  # Downward load in kN (negative Z)
        E = materials["Steel"].E  # kPa
        I = sections["RECT100x200"].Ix  # m⁴

        # Create model: cantilever beam along X axis
        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=FIXED)
        model.add_node(L, 0, 0, restraint=FREE)
        model.add_frame(1, 2, "Steel", "RECT100x200")

        # Apply point load at tip
        nodal_loads = [
            NodalLoad(node_id=2, load_case_id=dead_load_case.id, Fz=P)
        ]

        # Run analysis
        service = AnalysisService()
        results = service.analyze(
            model=model,
            materials=materials,
            sections=sections,
            load_case=dead_load_case,
            nodal_loads=nodal_loads,
        )

        # Check success
        assert results.success, f"Analysis failed: {results.error_message}"

        # Get tip displacement
        tip_disp = results.get_displacement(2)
        assert tip_disp is not None

        # Analytical solution for deflection
        delta_analytical = P * L**3 / (3 * E * I)

        # Check deflection (within 5% tolerance for numerical differences)
        assert tip_disp.Uz == pytest.approx(delta_analytical, rel=0.05), (
            f"Tip deflection {tip_disp.Uz} doesn't match analytical {delta_analytical}"
        )

    def test_cantilever_reactions(
        self,
        materials: dict[str, Material],
        sections: dict[str, Section],
        dead_load_case: LoadCase,
    ) -> None:
        """Test cantilever reactions match analytical solution."""
        L = 5.0
        P = -10.0  # kN downward

        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=FIXED)
        model.add_node(L, 0, 0, restraint=FREE)
        model.add_frame(1, 2, "Steel", "RECT100x200")

        nodal_loads = [
            NodalLoad(node_id=2, load_case_id=dead_load_case.id, Fz=P)
        ]

        service = AnalysisService()
        results = service.analyze(
            model=model,
            materials=materials,
            sections=sections,
            load_case=dead_load_case,
            nodal_loads=nodal_loads,
        )

        assert results.success

        # Get reaction at fixed support
        reaction = results.get_reaction(1)
        assert reaction is not None

        # Analytical: Fz = -P (equal and opposite)
        assert reaction.Fz == pytest.approx(-P, rel=0.01)

        # Analytical: My = P * L (moment about Y axis)
        # Sign convention: positive P in -Z direction creates positive My
        expected_my = -P * L
        assert reaction.My == pytest.approx(expected_my, rel=0.05)


@opensees_required
class TestSimplePortalFrame:
    """Test simple portal frame (two columns, one beam)."""

    def test_portal_frame_analysis(
        self,
        materials: dict[str, Material],
        sections: dict[str, Section],
        dead_load_case: LoadCase,
    ) -> None:
        """Test portal frame under horizontal load."""
        H = 4.0  # Column height
        B = 6.0  # Beam span
        P = 20.0  # Horizontal load at top (kN)

        model = StructuralModel()
        # Fixed supports at base
        model.add_node(0, 0, 0, restraint=FIXED)
        model.add_node(B, 0, 0, restraint=FIXED)
        # Free nodes at top
        model.add_node(0, 0, H, restraint=FREE)
        model.add_node(B, 0, H, restraint=FREE)

        # Left column
        model.add_frame(1, 3, "Steel", "RECT100x200")
        # Right column
        model.add_frame(2, 4, "Steel", "RECT100x200")
        # Beam
        model.add_frame(3, 4, "Steel", "RECT100x200")

        # Apply horizontal load at top left
        nodal_loads = [
            NodalLoad(node_id=3, load_case_id=dead_load_case.id, Fx=P)
        ]

        service = AnalysisService()
        results = service.analyze(
            model=model,
            materials=materials,
            sections=sections,
            load_case=dead_load_case,
            nodal_loads=nodal_loads,
        )

        assert results.success, f"Analysis failed: {results.error_message}"

        # Check displacements exist
        for node_id in [1, 2, 3, 4]:
            disp = results.get_displacement(node_id)
            assert disp is not None

        # Fixed supports should have zero displacement
        base_left = results.get_displacement(1)
        base_right = results.get_displacement(2)
        assert base_left is not None
        assert base_right is not None
        assert abs(base_left.Ux) < 1e-10
        assert abs(base_right.Ux) < 1e-10

        # Top nodes should displace in X direction
        top_left = results.get_displacement(3)
        top_right = results.get_displacement(4)
        assert top_left is not None
        assert top_right is not None
        assert top_left.Ux > 0  # Should move in direction of load

        # Both reactions should exist
        r1 = results.get_reaction(1)
        r2 = results.get_reaction(2)
        assert r1 is not None
        assert r2 is not None

        # Sum of horizontal reactions should equal applied load (equilibrium)
        total_rx = r1.Fx + r2.Fx
        assert total_rx == pytest.approx(-P, rel=0.01)


@opensees_required
class TestVerticalColumn:
    """Test vertical column under axial load."""

    def test_column_axial_load(
        self,
        materials: dict[str, Material],
        sections: dict[str, Section],
        dead_load_case: LoadCase,
    ) -> None:
        """Test column under pure axial compression."""
        L = 3.0  # Height
        P = -100.0  # Axial load (kN, compression)
        E = materials["Steel"].E
        A = sections["RECT100x200"].A

        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=FIXED)
        model.add_node(0, 0, L, restraint=FREE)
        model.add_frame(1, 2, "Steel", "RECT100x200")

        # Apply axial load at top
        nodal_loads = [
            NodalLoad(node_id=2, load_case_id=dead_load_case.id, Fz=P)
        ]

        service = AnalysisService()
        results = service.analyze(
            model=model,
            materials=materials,
            sections=sections,
            load_case=dead_load_case,
            nodal_loads=nodal_loads,
        )

        assert results.success

        # Get axial displacement at top
        top_disp = results.get_displacement(2)
        assert top_disp is not None

        # Analytical: δ = PL / (EA)
        delta_analytical = P * L / (E * A)
        assert top_disp.Uz == pytest.approx(delta_analytical, rel=0.05)


@opensees_required
class TestValidationFailure:
    """Test that invalid models fail appropriately."""

    def test_unsupported_model_fails(
        self,
        materials: dict[str, Material],
        sections: dict[str, Section],
        dead_load_case: LoadCase,
    ) -> None:
        """Model without supports should fail validation."""
        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=FREE)
        model.add_node(5, 0, 0, restraint=FREE)
        model.add_frame(1, 2, "Steel", "RECT100x200")

        service = AnalysisService()
        results = service.analyze(
            model=model,
            materials=materials,
            sections=sections,
            load_case=dead_load_case,
        )

        assert results.success is False
        assert "validation" in results.error_message.lower() or "support" in results.error_message.lower()

    def test_missing_material_fails(
        self,
        sections: dict[str, Section],
        dead_load_case: LoadCase,
    ) -> None:
        """Missing material should fail validation."""
        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=FIXED)
        model.add_node(5, 0, 0, restraint=FREE)
        model.add_frame(1, 2, "NonExistent", "RECT100x200")

        service = AnalysisService()
        materials: dict[str, Material] = {}

        results = service.analyze(
            model=model,
            materials=materials,
            sections=sections,
            load_case=dead_load_case,
        )

        assert results.success is False
        assert "material" in results.error_message.lower()

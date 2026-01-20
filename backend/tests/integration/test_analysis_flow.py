"""Integration tests for structural analysis flow.

Tests the complete analysis workflow using models with known analytical solutions.
"""

import pytest

from paz.domain.loads import LoadCase, LoadCaseType, NodalLoad
from paz.domain.materials import Material, MaterialType
from paz.domain.model import FIXED, FREE, PINNED, ROLLER_X, ROLLER_Y, StructuralModel
from paz.domain.sections import Section, SectionShape


# Check if OpenSees is available
def _opensees_available() -> bool:
    """Check if OpenSees binary is available for testing."""
    import shutil

    # Check if binary is in PATH
    if shutil.which("OpenSees") or shutil.which("opensees"):
        return True

    # Fallback: check for openseespy
    try:
        import openseespy.opensees  # noqa: F401

        return True
    except (ImportError, RuntimeError):
        return False


OPENSEES_AVAILABLE = _opensees_available()
opensees_required = pytest.mark.skipif(
    not OPENSEES_AVAILABLE,
    reason="OpenSees not available",
)


# Import AnalysisService (works with binary OpenSees)
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
        # With P = -10 kN (downward at tip), moment at support is:
        # My = P * L = -10 * 5 = -50 kN·m
        expected_my = P * L
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


@opensees_required
class TestAdvancedRestraintTypes:
    """Tests for F39 - Advanced Restraint Types.

    Verifies that different restraint types produce correct analysis results.
    Note: 3D stability requires minimum 6 restrained DOFs total.
    """

    def test_portal_with_pinned_and_fixed(
        self,
        materials: dict[str, Material],
        sections: dict[str, Section],
        dead_load_case: LoadCase,
    ) -> None:
        """Test portal frame with one pinned and one fixed support."""
        H = 4.0  # Column height
        B = 6.0  # Beam span
        P = 20.0  # Horizontal load (kN)

        model = StructuralModel()
        # Pinned support at left base (3 DOFs)
        model.add_node(0, 0, 0, restraint=PINNED)
        # Fixed support at right base (6 DOFs)
        model.add_node(B, 0, 0, restraint=FIXED)
        # Free nodes at top
        model.add_node(0, 0, H, restraint=FREE)
        model.add_node(B, 0, H, restraint=FREE)

        # Columns and beam
        model.add_frame(1, 3, "Steel", "RECT100x200")
        model.add_frame(2, 4, "Steel", "RECT100x200")
        model.add_frame(3, 4, "Steel", "RECT100x200")

        # Apply horizontal load
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

        # Pinned support should have zero displacement
        base_left = results.get_displacement(1)
        assert base_left is not None
        assert abs(base_left.Ux) < 1e-10
        assert abs(base_left.Uy) < 1e-10
        assert abs(base_left.Uz) < 1e-10

        # But pinned support can rotate
        # The rotation values exist (may be zero or non-zero depending on geometry)

        # Fixed support should have zero everything
        base_right = results.get_displacement(2)
        assert base_right is not None
        assert abs(base_right.Ux) < 1e-10
        assert abs(base_right.Uz) < 1e-10

        # Check equilibrium - sum of horizontal reactions equals applied load
        r1 = results.get_reaction(1)
        r2 = results.get_reaction(2)
        assert r1 is not None
        assert r2 is not None
        total_rx = r1.Fx + r2.Fx
        assert total_rx == pytest.approx(-P, rel=0.01)

    def test_cantilever_with_roller_tip(
        self,
        materials: dict[str, Material],
        sections: dict[str, Section],
        dead_load_case: LoadCase,
    ) -> None:
        """Test cantilever with roller support at tip (propped cantilever)."""
        L = 5.0
        P = -10.0  # kN downward at midspan

        model = StructuralModel()
        # Fixed at base
        model.add_node(0, 0, 0, restraint=FIXED)
        # Free at midspan
        model.add_node(L / 2, 0, 0, restraint=FREE)
        # Roller at tip (vertical support only)
        model.add_node(L, 0, 0, restraint=ROLLER_X)

        model.add_frame(1, 2, "Steel", "RECT100x200")
        model.add_frame(2, 3, "Steel", "RECT100x200")

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

        assert results.success, f"Analysis failed: {results.error_message}"

        # Roller tip should be able to move horizontally
        tip_disp = results.get_displacement(3)
        assert tip_disp is not None
        # But vertical displacement at roller should be restrained
        # (roller is fixed in Y and Z for ROLLER_X)
        assert abs(tip_disp.Uz) < 1e-6  # Z is fixed
        assert abs(tip_disp.Uy) < 1e-6  # Y is fixed

        # Reactions should exist at both supports
        r_fixed = results.get_reaction(1)
        r_roller = results.get_reaction(3)
        assert r_fixed is not None
        assert r_roller is not None

        # Sum of vertical reactions should equal applied load
        total_fz = r_fixed.Fz + r_roller.Fz
        assert total_fz == pytest.approx(-P, rel=0.05)

    def test_roller_y_in_stable_frame(
        self,
        materials: dict[str, Material],
        sections: dict[str, Section],
        dead_load_case: LoadCase,
    ) -> None:
        """Test ROLLER_Y support in a stable 2-column frame."""
        H = 4.0
        B = 6.0

        model = StructuralModel()
        # Fixed at left
        model.add_node(0, 0, 0, restraint=FIXED)
        # ROLLER_Y at right (free in Y only)
        model.add_node(B, 0, 0, restraint=ROLLER_Y)
        # Free nodes at top
        model.add_node(0, 0, H, restraint=FREE)
        model.add_node(B, 0, H, restraint=FREE)

        model.add_frame(1, 3, "Steel", "RECT100x200")
        model.add_frame(2, 4, "Steel", "RECT100x200")
        model.add_frame(3, 4, "Steel", "RECT100x200")

        # Apply load in Y direction at top
        P_y = 15.0  # kN
        nodal_loads = [
            NodalLoad(node_id=3, load_case_id=dead_load_case.id, Fy=P_y)
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

        # Check that frame deforms appropriately
        top_left = results.get_displacement(3)
        assert top_left is not None
        # Top nodes should move in Y due to load
        assert abs(top_left.Uy) > 0

        # Roller support should be able to move in Y if connected frame allows
        roller_disp = results.get_displacement(2)
        assert roller_disp is not None
        # X and Z are restrained
        assert abs(roller_disp.Ux) < 1e-10
        assert abs(roller_disp.Uz) < 1e-10


@opensees_required
class TestDistributedLoads:
    """Tests for F40 - Advanced Loads (Cargas Avanzadas).

    Tests distributed loads on beams with known analytical solutions.
    """

    def test_simply_supported_uniform_load(
        self,
        materials: dict[str, Material],
        sections: dict[str, Section],
        dead_load_case: LoadCase,
    ) -> None:
        """Test simply supported beam with uniform distributed load.

        Analytical solutions:
        - Max deflection at center: δ = 5wL⁴ / (384EI)
        - Reactions at supports: R = wL / 2
        """
        from paz.domain.loads import DistributedLoad, LoadDirection
        from paz.domain.model import Restraint

        L = 6.0  # Span in meters
        w = 10.0  # Uniform load in kN/m (downward)
        E = materials["Steel"].E  # kPa
        I = sections["RECT100x200"].Ix  # m⁴

        # Create simply supported beam along X axis
        # For 3D stability, need 6 DOFs minimum
        model = StructuralModel()
        # Pinned at left with torsion restrained (4 DOFs)
        pinned_with_torsion = Restraint(ux=True, uy=True, uz=True, rx=True, ry=False, rz=False)
        model.add_node(0, 0, 0, restraint=pinned_with_torsion)
        # Roller at right (2 DOFs: Uy, Uz)
        model.add_node(L, 0, 0, restraint=ROLLER_X)
        # Midpoint node for deflection check
        model.add_node(L / 2, 0, 0, restraint=FREE)

        # Two beam segments
        model.add_frame(1, 3, "Steel", "RECT100x200")  # Left half
        model.add_frame(3, 2, "Steel", "RECT100x200")  # Right half

        # Apply uniform distributed load to both segments
        distributed_loads = [
            DistributedLoad(
                frame_id=1,
                load_case_id=dead_load_case.id,
                direction=LoadDirection.GRAVITY,
                w_start=w,
                w_end=w,
            ),
            DistributedLoad(
                frame_id=2,
                load_case_id=dead_load_case.id,
                direction=LoadDirection.GRAVITY,
                w_start=w,
                w_end=w,
            ),
        ]

        # Run analysis
        service = AnalysisService()
        results = service.analyze(
            model=model,
            materials=materials,
            sections=sections,
            load_case=dead_load_case,
            distributed_loads=distributed_loads,
        )

        assert results.success, f"Analysis failed: {results.error_message}"

        # Check midpoint deflection
        mid_disp = results.get_displacement(3)
        assert mid_disp is not None

        # Analytical max deflection: δ = 5wL⁴ / (384EI)
        # Note: w is positive but load is downward (gravity), so deflection is negative
        delta_analytical = -5 * w * L**4 / (384 * E * I)

        assert mid_disp.Uz == pytest.approx(delta_analytical, rel=0.10), (
            f"Midpoint deflection {mid_disp.Uz:.6e} doesn't match "
            f"analytical {delta_analytical:.6e}"
        )

        # Check reactions
        r_left = results.get_reaction(1)
        r_right = results.get_reaction(2)
        assert r_left is not None
        assert r_right is not None

        # Analytical reaction: R = wL / 2
        R_analytical = w * L / 2

        assert r_left.Fz == pytest.approx(R_analytical, rel=0.05), (
            f"Left reaction {r_left.Fz} doesn't match analytical {R_analytical}"
        )
        assert r_right.Fz == pytest.approx(R_analytical, rel=0.05), (
            f"Right reaction {r_right.Fz} doesn't match analytical {R_analytical}"
        )

    def test_cantilever_uniform_load(
        self,
        materials: dict[str, Material],
        sections: dict[str, Section],
        dead_load_case: LoadCase,
    ) -> None:
        """Test cantilever with uniform distributed load.

        Analytical solutions:
        - Tip deflection: δ = wL⁴ / (8EI)
        - Reaction at fixed end: R = wL
        - Moment at fixed end: M = wL² / 2
        """
        from paz.domain.loads import uniform_load

        L = 5.0  # Length in meters
        w = 10.0  # Uniform load in kN/m
        E = materials["Steel"].E
        I = sections["RECT100x200"].Ix

        # Create cantilever
        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=FIXED)
        model.add_node(L, 0, 0, restraint=FREE)
        model.add_frame(1, 2, "Steel", "RECT100x200")

        # Uniform load over full length
        distributed_loads = [
            uniform_load(
                frame_id=1,
                load_case_id=dead_load_case.id,
                w=w,
            )
        ]

        service = AnalysisService()
        results = service.analyze(
            model=model,
            materials=materials,
            sections=sections,
            load_case=dead_load_case,
            distributed_loads=distributed_loads,
        )

        assert results.success, f"Analysis failed: {results.error_message}"

        # Check tip deflection
        tip_disp = results.get_displacement(2)
        assert tip_disp is not None

        # Analytical tip deflection for uniform load: δ = wL⁴ / (8EI)
        delta_analytical = -w * L**4 / (8 * E * I)

        assert tip_disp.Uz == pytest.approx(delta_analytical, rel=0.10), (
            f"Tip deflection {tip_disp.Uz:.6e} doesn't match "
            f"analytical {delta_analytical:.6e}"
        )

        # Check reaction
        reaction = results.get_reaction(1)
        assert reaction is not None

        # Analytical reaction: R = wL (total load)
        R_analytical = w * L
        assert reaction.Fz == pytest.approx(R_analytical, rel=0.05)


@opensees_required
class TestPointLoadsOnFrames:
    """Tests for point loads applied at specific locations on frames."""

    def test_simply_supported_midpoint_load(
        self,
        materials: dict[str, Material],
        sections: dict[str, Section],
        dead_load_case: LoadCase,
    ) -> None:
        """Test simply supported beam with point load at midpoint.

        Analytical solutions:
        - Max deflection at center: δ = PL³ / (48EI)
        - Reactions at supports: R = P / 2
        """
        from paz.domain.loads import midpoint_load
        from paz.domain.model import Restraint

        L = 6.0  # Span in meters
        P = 20.0  # Point load in kN (downward)
        E = materials["Steel"].E
        I = sections["RECT100x200"].Ix

        # Create simply supported beam
        # For 3D stability, need 6 DOFs minimum
        model = StructuralModel()
        # Pinned at left with torsion restrained (4 DOFs)
        pinned_with_torsion = Restraint(ux=True, uy=True, uz=True, rx=True, ry=False, rz=False)
        model.add_node(0, 0, 0, restraint=pinned_with_torsion)
        model.add_node(L, 0, 0, restraint=ROLLER_X)
        model.add_frame(1, 2, "Steel", "RECT100x200")

        # Apply point load at midpoint
        point_loads = [
            midpoint_load(
                frame_id=1,
                load_case_id=dead_load_case.id,
                P=P,
            )
        ]

        service = AnalysisService()
        results = service.analyze(
            model=model,
            materials=materials,
            sections=sections,
            load_case=dead_load_case,
            point_loads=point_loads,
        )

        assert results.success, f"Analysis failed: {results.error_message}"

        # Check reactions
        r_left = results.get_reaction(1)
        r_right = results.get_reaction(2)
        assert r_left is not None
        assert r_right is not None

        # Analytical reaction: R = P / 2
        R_analytical = P / 2

        assert r_left.Fz == pytest.approx(R_analytical, rel=0.05), (
            f"Left reaction {r_left.Fz} doesn't match analytical {R_analytical}"
        )
        assert r_right.Fz == pytest.approx(R_analytical, rel=0.05), (
            f"Right reaction {r_right.Fz} doesn't match analytical {R_analytical}"
        )

    def test_cantilever_point_load_at_quarter(
        self,
        materials: dict[str, Material],
        sections: dict[str, Section],
        dead_load_case: LoadCase,
    ) -> None:
        """Test cantilever with point load at L/4 from fixed end.

        Analytical solutions for load P at distance 'a' from fixed end:
        - Deflection at load point: δ_a = Pa³ / (3EI)
        - Deflection at tip: δ_L = Pa² * (3L - a) / (6EI)
        """
        from paz.domain.loads import PointLoadOnFrame, PointLoadDirection

        L = 4.0  # Length in meters
        a = L / 4  # Load position (1m from fixed end)
        P = 15.0  # Point load in kN
        E = materials["Steel"].E
        I = sections["RECT100x200"].Ix

        # Create cantilever
        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=FIXED)
        model.add_node(L, 0, 0, restraint=FREE)
        model.add_frame(1, 2, "Steel", "RECT100x200")

        # Point load at L/4 (location = 0.25)
        point_loads = [
            PointLoadOnFrame(
                frame_id=1,
                load_case_id=dead_load_case.id,
                location=0.25,  # L/4
                P=P,
                direction=PointLoadDirection.GRAVITY,
            )
        ]

        service = AnalysisService()
        results = service.analyze(
            model=model,
            materials=materials,
            sections=sections,
            load_case=dead_load_case,
            point_loads=point_loads,
        )

        assert results.success, f"Analysis failed: {results.error_message}"

        # Check tip deflection
        tip_disp = results.get_displacement(2)
        assert tip_disp is not None

        # Analytical tip deflection: δ_L = Pa² * (3L - a) / (6EI)
        delta_tip_analytical = -P * a**2 * (3 * L - a) / (6 * E * I)

        assert tip_disp.Uz == pytest.approx(delta_tip_analytical, rel=0.10), (
            f"Tip deflection {tip_disp.Uz:.6e} doesn't match "
            f"analytical {delta_tip_analytical:.6e}"
        )

        # Check reaction
        reaction = results.get_reaction(1)
        assert reaction is not None

        # Vertical reaction should equal applied load
        assert reaction.Fz == pytest.approx(P, rel=0.05)

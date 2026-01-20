"""Tests for TclWriter frame releases functionality."""

import pytest
from pathlib import Path
import tempfile

from paz.domain.model.frame import FrameReleases
from paz.domain.model.restraint import Restraint, RestraintType
from paz.domain.model.structural_model import StructuralModel
from paz.domain.materials import Material
from paz.domain.sections import Section
from paz.domain.loads import LoadCase
from paz.infrastructure.engines.tcl_writer import (
    TclWriter,
    RELEASE_NODE_OFFSET,
    RELEASE_ELEMENT_OFFSET,
    RELEASE_MATERIAL_TAG,
    RIGID_STIFFNESS,
    RELEASE_STIFFNESS,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def basic_material() -> Material:
    """Create a basic steel material."""
    return Material(
        name="A36",
        material_type="Steel",
        E=200e9,
        nu=0.3,
        rho=7850,
    )


@pytest.fixture
def basic_section() -> Section:
    """Create a basic W section."""
    return Section(
        name="W14X22",
        shape="WideFlange",
        A=0.00419,
        Ix=8.91e-5,
        Iy=1.19e-5,
        J=2.0e-7,
    )


@pytest.fixture
def simple_model() -> StructuralModel:
    """Create a simple beam model (2 nodes, no frames)."""
    model = StructuralModel()

    # Fixed support at node 1
    fixed = Restraint.from_type(RestraintType.FIXED)
    model.add_node(0, 0, 0, restraint=fixed)

    # Free node at node 2
    free = Restraint.from_type(RestraintType.FREE)
    model.add_node(5, 0, 0, restraint=free)

    return model


class TestTclWriterReleases:
    """Tests for TclWriter release generation."""

    def test_frame_without_releases(
        self,
        temp_dir: Path,
        simple_model: StructuralModel,
        basic_material: Material,
        basic_section: Section,
    ) -> None:
        """Test that frame without releases generates normal element."""
        # Add frame without releases (default)
        simple_model.add_frame(
            node_i_id=1,
            node_j_id=2,
            material_name="A36",
            section_name="W14X22",
        )

        writer = TclWriter(temp_dir)
        tcl_path = writer.write_model(
            model=simple_model,
            materials={"A36": basic_material},
            sections={"W14X22": basic_section},
            load_case=LoadCase(name="LC1", load_type="Dead"),
            nodal_loads=[],
            distributed_loads=[],
        )

        content = tcl_path.read_text()

        # Should NOT have zeroLength elements
        assert "element zeroLength" not in content

        # Should have normal element connecting nodes 1 and 2
        assert "element elasticBeamColumn 1 1 2" in content

    def test_frame_with_pinned_end_i(
        self,
        temp_dir: Path,
        simple_model: StructuralModel,
        basic_material: Material,
        basic_section: Section,
    ) -> None:
        """Test frame with pinned end at node i."""
        releases = FrameReleases(M2_i=True, M3_i=True)
        simple_model.add_frame(
            node_i_id=1,
            node_j_id=2,
            material_name="A36",
            section_name="W14X22",
            releases=releases,
        )

        writer = TclWriter(temp_dir)
        tcl_path = writer.write_model(
            model=simple_model,
            materials={"A36": basic_material},
            sections={"W14X22": basic_section},
            load_case=LoadCase(name="LC1", load_type="Dead"),
            nodal_loads=[],
            distributed_loads=[],
        )

        content = tcl_path.read_text()

        # Should have release node for end i
        release_node_i = RELEASE_NODE_OFFSET + 1 * 2  # frame.id * 2
        assert f"node {release_node_i}" in content

        # Should have zeroLength element at end i
        release_ele_i = RELEASE_ELEMENT_OFFSET + 1 * 2
        assert f"element zeroLength {release_ele_i}" in content

        # Frame should connect to release node at end i
        assert f"element elasticBeamColumn 1 {release_node_i} 2" in content

    def test_frame_with_pinned_end_j(
        self,
        temp_dir: Path,
        simple_model: StructuralModel,
        basic_material: Material,
        basic_section: Section,
    ) -> None:
        """Test frame with pinned end at node j."""
        releases = FrameReleases(M2_j=True, M3_j=True)
        simple_model.add_frame(
            node_i_id=1,
            node_j_id=2,
            material_name="A36",
            section_name="W14X22",
            releases=releases,
        )

        writer = TclWriter(temp_dir)
        tcl_path = writer.write_model(
            model=simple_model,
            materials={"A36": basic_material},
            sections={"W14X22": basic_section},
            load_case=LoadCase(name="LC1", load_type="Dead"),
            nodal_loads=[],
            distributed_loads=[],
        )

        content = tcl_path.read_text()

        # Should have release node for end j
        release_node_j = RELEASE_NODE_OFFSET + 1 * 2 + 1  # frame.id * 2 + 1
        assert f"node {release_node_j}" in content

        # Should have zeroLength element at end j
        release_ele_j = RELEASE_ELEMENT_OFFSET + 1 * 2 + 1
        assert f"element zeroLength {release_ele_j}" in content

        # Frame should connect to release node at end j
        assert f"element elasticBeamColumn 1 1 {release_node_j}" in content

    def test_frame_with_pinned_pinned(
        self,
        temp_dir: Path,
        simple_model: StructuralModel,
        basic_material: Material,
        basic_section: Section,
    ) -> None:
        """Test frame with both ends pinned."""
        releases = FrameReleases.pinned_pinned()
        simple_model.add_frame(
            node_i_id=1,
            node_j_id=2,
            material_name="A36",
            section_name="W14X22",
            releases=releases,
        )

        writer = TclWriter(temp_dir)
        tcl_path = writer.write_model(
            model=simple_model,
            materials={"A36": basic_material},
            sections={"W14X22": basic_section},
            load_case=LoadCase(name="LC1", load_type="Dead"),
            nodal_loads=[],
            distributed_loads=[],
        )

        content = tcl_path.read_text()

        # Should have release nodes for both ends
        release_node_i = RELEASE_NODE_OFFSET + 1 * 2
        release_node_j = RELEASE_NODE_OFFSET + 1 * 2 + 1
        assert f"node {release_node_i}" in content
        assert f"node {release_node_j}" in content

        # Should have zeroLength elements at both ends
        release_ele_i = RELEASE_ELEMENT_OFFSET + 1 * 2
        release_ele_j = RELEASE_ELEMENT_OFFSET + 1 * 2 + 1
        assert f"element zeroLength {release_ele_i}" in content
        assert f"element zeroLength {release_ele_j}" in content

        # Frame should connect to both release nodes
        assert f"element elasticBeamColumn 1 {release_node_i} {release_node_j}" in content

    def test_release_materials_created(
        self,
        temp_dir: Path,
        simple_model: StructuralModel,
        basic_material: Material,
        basic_section: Section,
    ) -> None:
        """Test that release materials are created with correct stiffness."""
        releases = FrameReleases(M2_i=True)
        simple_model.add_frame(
            node_i_id=1,
            node_j_id=2,
            material_name="A36",
            section_name="W14X22",
            releases=releases,
        )

        writer = TclWriter(temp_dir)
        tcl_path = writer.write_model(
            model=simple_model,
            materials={"A36": basic_material},
            sections={"W14X22": basic_section},
            load_case=LoadCase(name="LC1", load_type="Dead"),
            nodal_loads=[],
            distributed_loads=[],
        )

        content = tcl_path.read_text()

        # Should have rigid material
        assert f"uniaxialMaterial Elastic {RELEASE_MATERIAL_TAG}" in content
        assert f"{RIGID_STIFFNESS:.6e}" in content

        # Should have release material
        assert f"uniaxialMaterial Elastic {RELEASE_MATERIAL_TAG + 1}" in content
        assert f"{RELEASE_STIFFNESS:.6e}" in content

    def test_multiple_frames_with_different_releases(
        self,
        temp_dir: Path,
        basic_material: Material,
        basic_section: Section,
    ) -> None:
        """Test multiple frames with different release configurations."""
        model = StructuralModel()

        # Create nodes
        fixed = Restraint.from_type(RestraintType.FIXED)
        free = Restraint.from_type(RestraintType.FREE)

        model.add_node(0, 0, 0, restraint=fixed)
        model.add_node(5, 0, 0, restraint=free)
        model.add_node(10, 0, 0, restraint=fixed)

        # Frame 1: fixed-fixed (no releases)
        model.add_frame(
            node_i_id=1,
            node_j_id=2,
            material_name="A36",
            section_name="W14X22",
        )

        # Frame 2: pinned at end i
        model.add_frame(
            node_i_id=2,
            node_j_id=3,
            material_name="A36",
            section_name="W14X22",
            releases=FrameReleases(M2_i=True, M3_i=True),
        )

        writer = TclWriter(temp_dir)
        tcl_path = writer.write_model(
            model=model,
            materials={"A36": basic_material},
            sections={"W14X22": basic_section},
            load_case=LoadCase(name="LC1", load_type="Dead"),
            nodal_loads=[],
            distributed_loads=[],
        )

        content = tcl_path.read_text()

        # Frame 1 should connect to original nodes (no releases)
        assert "element elasticBeamColumn 1 1 2" in content

        # Frame 2 should connect to release node at end i
        release_node_i = RELEASE_NODE_OFFSET + 2 * 2
        assert f"element elasticBeamColumn 2 {release_node_i} 3" in content

    def test_torsion_release(
        self,
        temp_dir: Path,
        simple_model: StructuralModel,
        basic_material: Material,
        basic_section: Section,
    ) -> None:
        """Test frame with torsion release."""
        releases = FrameReleases(T_i=True)
        simple_model.add_frame(
            node_i_id=1,
            node_j_id=2,
            material_name="A36",
            section_name="W14X22",
            releases=releases,
        )

        writer = TclWriter(temp_dir)
        tcl_path = writer.write_model(
            model=simple_model,
            materials={"A36": basic_material},
            sections={"W14X22": basic_section},
            load_case=LoadCase(name="LC1", load_type="Dead"),
            nodal_loads=[],
            distributed_loads=[],
        )

        content = tcl_path.read_text()

        # Should have release node
        release_node_i = RELEASE_NODE_OFFSET + 1 * 2
        assert f"node {release_node_i}" in content

        # Should have zeroLength with torsion release (DOF 4)
        assert "element zeroLength" in content
        assert "-dir 1 2 3 4 5 6" in content

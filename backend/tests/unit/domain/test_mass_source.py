"""Unit tests for mass source and frame mass calculations."""

import pytest

from paz.domain.analysis import MassSource, MassSourceType
from paz.domain.analysis.mass_source import LoadMassFactor
from paz.domain.materials import Material, MaterialType
from paz.domain.model import Frame, Node
from paz.domain.sections import Section, SectionShape


class TestLoadMassFactor:
    """Tests for LoadMassFactor dataclass."""

    def test_creation(self) -> None:
        """Test creating a load mass factor."""
        lmf = LoadMassFactor(load_case_name="Dead", factor=1.0)
        assert lmf.load_case_name == "Dead"
        assert lmf.factor == 1.0

    def test_default_factor(self) -> None:
        """Test default factor is 1.0."""
        lmf = LoadMassFactor(load_case_name="Live")
        assert lmf.factor == 1.0

    def test_serialization(self) -> None:
        """Test to_dict and from_dict."""
        lmf = LoadMassFactor(load_case_name="Live", factor=0.25)
        data = lmf.to_dict()
        restored = LoadMassFactor.from_dict(data)

        assert restored.load_case_name == "Live"
        assert restored.factor == 0.25


class TestMassSourceType:
    """Tests for MassSourceType enum."""

    def test_enum_values(self) -> None:
        """Test all enum values exist."""
        assert MassSourceType.SELF_WEIGHT.value == "self_weight"
        assert MassSourceType.LOADS.value == "loads"
        assert MassSourceType.SELF_WEIGHT_PLUS_LOADS.value == "self_weight_plus_loads"
        assert MassSourceType.CUSTOM.value == "custom"


class TestMassSource:
    """Tests for MassSource configuration."""

    def test_default_creation(self) -> None:
        """Test creating a mass source with defaults."""
        ms = MassSource()
        assert ms.source_type == MassSourceType.SELF_WEIGHT
        assert ms.include_self_weight is True
        assert ms.self_weight_factor == 1.0
        assert ms.load_factors == []
        assert ms.lumped_mass is True

    def test_self_weight_only_factory(self) -> None:
        """Test self_weight_only factory method."""
        ms = MassSource.self_weight_only()
        assert ms.source_type == MassSourceType.SELF_WEIGHT
        assert ms.include_self_weight is True
        assert ms.self_weight_factor == 1.0

    def test_dead_plus_live_factory(self) -> None:
        """Test dead_plus_live factory method."""
        ms = MassSource.dead_plus_live(live_factor=0.25)

        assert ms.source_type == MassSourceType.SELF_WEIGHT_PLUS_LOADS
        assert ms.include_self_weight is True
        assert len(ms.load_factors) == 2

        dead_factor = ms.get_load_factor("Dead")
        live_factor = ms.get_load_factor("Live")
        assert dead_factor == 1.0
        assert live_factor == 0.25

    def test_add_load_factor(self) -> None:
        """Test adding load factors."""
        ms = MassSource()
        ms.add_load_factor("Dead", 1.0)
        ms.add_load_factor("Live", 0.25)

        assert len(ms.load_factors) == 2
        assert ms.get_load_factor("Dead") == 1.0
        assert ms.get_load_factor("Live") == 0.25

    def test_add_load_factor_replaces_existing(self) -> None:
        """Test adding a load factor replaces existing one for same load case."""
        ms = MassSource()
        ms.add_load_factor("Live", 0.25)
        ms.add_load_factor("Live", 0.5)

        assert len(ms.load_factors) == 1
        assert ms.get_load_factor("Live") == 0.5

    def test_remove_load_factor(self) -> None:
        """Test removing a load factor."""
        ms = MassSource()
        ms.add_load_factor("Dead", 1.0)
        ms.add_load_factor("Live", 0.25)
        ms.remove_load_factor("Live")

        assert len(ms.load_factors) == 1
        assert ms.get_load_factor("Live") is None

    def test_get_load_factor_not_found(self) -> None:
        """Test getting a non-existent load factor returns None."""
        ms = MassSource()
        assert ms.get_load_factor("NonExistent") is None

    def test_negative_self_weight_factor_raises(self) -> None:
        """Test that negative self_weight_factor raises error."""
        with pytest.raises(ValueError, match="self_weight_factor cannot be negative"):
            MassSource(self_weight_factor=-0.5)

    def test_negative_load_factor_raises(self) -> None:
        """Test that negative load factor raises error."""
        with pytest.raises(ValueError, match="cannot be negative"):
            MassSource(load_factors=[LoadMassFactor("Dead", -1.0)])

    def test_serialization(self) -> None:
        """Test to_dict and from_dict."""
        ms = MassSource.dead_plus_live(0.3)
        data = ms.to_dict()
        restored = MassSource.from_dict(data)

        assert restored.source_type == MassSourceType.SELF_WEIGHT_PLUS_LOADS
        assert restored.include_self_weight is True
        assert restored.self_weight_factor == 1.0
        assert len(restored.load_factors) == 2
        assert restored.get_load_factor("Live") == 0.3


class TestFrameMass:
    """Tests for Frame.mass() and Frame.weight() methods."""

    @pytest.fixture
    def steel_material(self) -> Material:
        """Steel material with standard density (7850 kg/m³)."""
        return Material(
            name="Steel",
            material_type=MaterialType.STEEL,
            E=200e6,  # kPa
            nu=0.3,
            rho=7850,  # kg/m³
        )

    @pytest.fixture
    def rectangular_section(self) -> Section:
        """Rectangular section 0.1m x 0.2m."""
        b = 0.1  # width
        h = 0.2  # height
        A = b * h  # 0.02 m²
        Ix = b * h**3 / 12
        Iy = h * b**3 / 12

        return Section(
            name="RECT100x200",
            shape=SectionShape.CUSTOM,
            A=A,
            Ix=Ix,
            Iy=Iy,
        )

    @pytest.fixture
    def simple_frame(self) -> Frame:
        """Frame of 5m length."""
        node_i = Node(id=1, x=0, y=0, z=0)
        node_j = Node(id=2, x=5, y=0, z=0)

        frame = Frame(
            id=1,
            node_i_id=1,
            node_j_id=2,
            material_name="Steel",
            section_name="RECT100x200",
        )
        frame.set_nodes(node_i, node_j)
        return frame

    def test_frame_mass_calculation(
        self,
        simple_frame: Frame,
        steel_material: Material,
        rectangular_section: Section,
    ) -> None:
        """Test frame mass is calculated correctly.

        Mass = rho * A * L
        rho = 7850 kg/m³
        A = 0.1 * 0.2 = 0.02 m²
        L = 5 m
        Expected mass = 7850 * 0.02 * 5 = 785 kg
        """
        mass = simple_frame.mass(steel_material, rectangular_section)

        expected_mass = 7850 * 0.02 * 5  # 785 kg
        assert mass == pytest.approx(expected_mass, rel=1e-6)

    def test_frame_weight_calculation(
        self,
        simple_frame: Frame,
        steel_material: Material,
        rectangular_section: Section,
    ) -> None:
        """Test frame weight is calculated correctly.

        Weight = mass * g / 1000 (kN)
        mass = 785 kg
        g = 9.81 m/s²
        Expected weight = 785 * 9.81 / 1000 = 7.7 kN
        """
        weight = simple_frame.weight(steel_material, rectangular_section)

        expected_weight = 785 * 9.81 / 1000  # 7.7 kN approximately
        assert weight == pytest.approx(expected_weight, rel=1e-6)

    def test_frame_weight_custom_gravity(
        self,
        simple_frame: Frame,
        steel_material: Material,
        rectangular_section: Section,
    ) -> None:
        """Test frame weight with custom gravity."""
        weight = simple_frame.weight(steel_material, rectangular_section, g=10.0)

        expected_weight = 785 * 10.0 / 1000  # 7.85 kN
        assert weight == pytest.approx(expected_weight, rel=1e-6)

    def test_frame_mass_different_lengths(
        self,
        steel_material: Material,
        rectangular_section: Section,
    ) -> None:
        """Test mass scales linearly with length."""
        # 10m frame
        node_i = Node(id=1, x=0, y=0, z=0)
        node_j = Node(id=2, x=10, y=0, z=0)

        frame = Frame(
            id=1,
            node_i_id=1,
            node_j_id=2,
            material_name="Steel",
            section_name="RECT100x200",
        )
        frame.set_nodes(node_i, node_j)

        mass = frame.mass(steel_material, rectangular_section)

        expected_mass = 7850 * 0.02 * 10  # 1570 kg
        assert mass == pytest.approx(expected_mass, rel=1e-6)

    def test_frame_mass_requires_nodes(
        self,
        steel_material: Material,
        rectangular_section: Section,
    ) -> None:
        """Test that mass calculation requires nodes to be set."""
        frame = Frame(
            id=1,
            node_i_id=1,
            node_j_id=2,
            material_name="Steel",
            section_name="RECT100x200",
        )

        with pytest.raises(Exception):  # FrameError
            frame.mass(steel_material, rectangular_section)

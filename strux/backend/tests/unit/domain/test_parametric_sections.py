"""Tests for parametric section classes."""

import pytest
from math import pi, sqrt

from paz.core.exceptions import ValidationError
from paz.domain.sections import (
    Angle,
    Channel,
    CircularHollow,
    CircularSolid,
    ISection,
    Pipe,
    RectangularHollow,
    RectangularSolid,
    SectionShape,
    SectionStandard,
    TSection,
)


class TestISection:
    """Tests for ISection (Wide Flange)."""

    def test_create_i_section(self) -> None:
        """Test creating an I-section."""
        section = ISection(
            name="W14X30-like",
            d=0.351,  # 13.8 in
            bf=0.171,  # 6.73 in
            tf=0.00978,  # 0.385 in
            tw=0.00686,  # 0.270 in
        )
        assert section.name == "W14X30-like"
        assert section.d == 0.351
        assert section.A > 0
        assert section.Ix > 0
        assert section.Iy > 0

    def test_i_section_area(self) -> None:
        """Test I-section area calculation."""
        # Simple case: 200mm deep, 100mm wide flanges, 10mm thick
        section = ISection(
            d=0.200,
            bf=0.100,
            tf=0.010,
            tw=0.008,
        )
        # A = 2 * bf * tf + hw * tw
        # A = 2 * 0.1 * 0.01 + 0.18 * 0.008 = 0.002 + 0.00144 = 0.00344 m²
        expected_A = 2 * 0.100 * 0.010 + 0.180 * 0.008
        assert abs(section.A - expected_A) < 1e-9

    def test_i_section_moment_of_inertia(self) -> None:
        """Test I-section moment of inertia calculation."""
        section = ISection(
            d=0.200,
            bf=0.100,
            tf=0.010,
            tw=0.008,
        )
        # Strong axis Ix should be larger than Iy for typical I-section
        assert section.Ix > section.Iy

    def test_i_section_radii_of_gyration(self) -> None:
        """Test radii of gyration calculation."""
        section = ISection(d=0.300, bf=0.150, tf=0.015, tw=0.010)
        # rx should be larger than ry for I-section
        assert section.rx > section.ry
        # r = sqrt(I/A)
        assert abs(section.rx - sqrt(section.Ix / section.A)) < 1e-10
        assert abs(section.ry - sqrt(section.Iy / section.A)) < 1e-10

    def test_i_section_to_section(self) -> None:
        """Test conversion to standard Section object."""
        i_section = ISection(
            name="Test I",
            d=0.300,
            bf=0.150,
            tf=0.015,
            tw=0.010,
            description="Test description",
        )
        section = i_section.to_section()

        assert section.name == "Test I"
        assert section.shape == SectionShape.W
        assert section.standard == SectionStandard.CUSTOM
        assert section.is_custom is True
        assert section.A == i_section.A
        assert section.Ix == i_section.Ix
        assert section.d == 0.300
        assert section.bf == 0.150

    def test_i_section_invalid_depth(self) -> None:
        """Test that invalid depth raises error."""
        with pytest.raises(ValidationError):
            ISection(d=0, bf=0.1, tf=0.01, tw=0.008)

    def test_i_section_invalid_web_height(self) -> None:
        """Test that flanges thicker than half depth raises error."""
        with pytest.raises(ValueError, match="Web height"):
            ISection(d=0.020, bf=0.1, tf=0.015, tw=0.008)  # 2*tf = 0.03 > d


class TestRectangularSolid:
    """Tests for solid rectangular sections."""

    def test_create_rectangular_solid(self) -> None:
        """Test creating a solid rectangle."""
        section = RectangularSolid(name="Rect", B=0.200, H=0.300)
        assert section.B == 0.200
        assert section.H == 0.300

    def test_rectangular_solid_area(self) -> None:
        """Test area calculation."""
        section = RectangularSolid(B=0.200, H=0.300)
        assert abs(section.A - 0.06) < 1e-10

    def test_rectangular_solid_inertia(self) -> None:
        """Test moment of inertia calculation."""
        section = RectangularSolid(B=0.200, H=0.300)
        # Ix = B * H³ / 12
        expected_Ix = 0.200 * 0.300**3 / 12
        assert abs(section.Ix - expected_Ix) < 1e-12
        # Iy = H * B³ / 12
        expected_Iy = 0.300 * 0.200**3 / 12
        assert abs(section.Iy - expected_Iy) < 1e-12

    def test_rectangular_solid_section_modulus(self) -> None:
        """Test elastic section modulus calculation."""
        section = RectangularSolid(B=0.200, H=0.300)
        # Sx = B * H² / 6
        expected_Sx = 0.200 * 0.300**2 / 6
        assert abs(section.Sx - expected_Sx) < 1e-12

    def test_rectangular_solid_plastic_modulus(self) -> None:
        """Test plastic section modulus calculation."""
        section = RectangularSolid(B=0.200, H=0.300)
        # Zx = B * H² / 4
        expected_Zx = 0.200 * 0.300**2 / 4
        assert abs(section._calculate_Zx() - expected_Zx) < 1e-12


class TestRectangularHollow:
    """Tests for hollow rectangular (box) sections."""

    def test_create_rectangular_hollow(self) -> None:
        """Test creating a hollow rectangle."""
        section = RectangularHollow(name="HSS", B=0.200, H=0.300, t=0.010)
        assert section.B == 0.200
        assert section.H == 0.300
        assert section.t == 0.010

    def test_rectangular_hollow_area(self) -> None:
        """Test area calculation."""
        section = RectangularHollow(B=0.200, H=0.300, t=0.010)
        # A = B*H - (B-2t)*(H-2t)
        outer = 0.200 * 0.300
        inner = 0.180 * 0.280
        assert abs(section.A - (outer - inner)) < 1e-10

    def test_rectangular_hollow_inner_dimensions(self) -> None:
        """Test inner dimension properties."""
        section = RectangularHollow(B=0.200, H=0.300, t=0.010)
        assert abs(section.Bi - 0.180) < 1e-10
        assert abs(section.Hi - 0.280) < 1e-10

    def test_rectangular_hollow_inertia(self) -> None:
        """Test moment of inertia is less than solid."""
        hollow = RectangularHollow(B=0.200, H=0.300, t=0.010)
        solid = RectangularSolid(B=0.200, H=0.300)
        assert hollow.Ix < solid.Ix
        assert hollow.Iy < solid.Iy

    def test_rectangular_hollow_shape(self) -> None:
        """Test that shape is HSS_RECT."""
        section = RectangularHollow(B=0.1, H=0.15, t=0.005)
        assert section._get_shape() == SectionShape.HSS_RECT

    def test_rectangular_hollow_invalid_thickness(self) -> None:
        """Test that thickness >= B/2 raises error."""
        with pytest.raises(ValidationError, match="Thickness"):
            RectangularHollow(B=0.100, H=0.200, t=0.060)


class TestCircularSolid:
    """Tests for solid circular sections."""

    def test_create_circular_solid(self) -> None:
        """Test creating a solid circle."""
        section = CircularSolid(name="Rod", D=0.100)
        assert section.D == 0.100

    def test_circular_solid_area(self) -> None:
        """Test area calculation."""
        section = CircularSolid(D=0.100)
        expected = pi * 0.100**2 / 4
        assert abs(section.A - expected) < 1e-12

    def test_circular_solid_inertia(self) -> None:
        """Test moment of inertia calculation."""
        section = CircularSolid(D=0.100)
        expected = pi * 0.100**4 / 64
        assert abs(section.Ix - expected) < 1e-15
        assert abs(section.Iy - expected) < 1e-15  # Symmetric

    def test_circular_solid_torsional_constant(self) -> None:
        """Test torsional constant calculation."""
        section = CircularSolid(D=0.100)
        expected = pi * 0.100**4 / 32  # J = 2*Ix for circle
        assert abs(section.J - expected) < 1e-15


class TestCircularHollow:
    """Tests for hollow circular (pipe) sections."""

    def test_create_circular_hollow(self) -> None:
        """Test creating a hollow circle."""
        section = CircularHollow(name="Pipe", D=0.100, t=0.005)
        assert section.D == 0.100
        assert section.t == 0.005

    def test_circular_hollow_inner_diameter(self) -> None:
        """Test inner diameter calculation."""
        section = CircularHollow(D=0.100, t=0.005)
        assert abs(section.Di - 0.090) < 1e-10

    def test_circular_hollow_area(self) -> None:
        """Test area calculation."""
        section = CircularHollow(D=0.100, t=0.005)
        expected = pi * (0.100**2 - 0.090**2) / 4
        assert abs(section.A - expected) < 1e-12

    def test_circular_hollow_inertia(self) -> None:
        """Test moment of inertia is less than solid."""
        hollow = CircularHollow(D=0.100, t=0.005)
        solid = CircularSolid(D=0.100)
        assert hollow.Ix < solid.Ix

    def test_pipe_alias(self) -> None:
        """Test that Pipe is an alias for CircularHollow."""
        pipe = Pipe(D=0.100, t=0.005)
        assert isinstance(pipe, CircularHollow)

    def test_circular_hollow_shape(self) -> None:
        """Test that shape is PIPE."""
        section = CircularHollow(D=0.1, t=0.005)
        assert section._get_shape() == SectionShape.PIPE


class TestAngle:
    """Tests for angle (L-shape) sections."""

    def test_create_equal_angle(self) -> None:
        """Test creating an equal-leg angle."""
        section = Angle(name="L4x4x1/2", L1=0.100, L2=0.100, t=0.012)
        assert section.L1 == 0.100
        assert section.L2 == 0.100
        assert section.is_equal is True

    def test_create_unequal_angle(self) -> None:
        """Test creating an unequal-leg angle."""
        section = Angle(name="L6x4x1/2", L1=0.150, L2=0.100, t=0.012)
        assert section.is_equal is False

    def test_angle_area(self) -> None:
        """Test area calculation."""
        section = Angle(L1=0.100, L2=0.100, t=0.010)
        # A = t * (L1 + L2 - t)
        expected = 0.010 * (0.100 + 0.100 - 0.010)
        assert abs(section.A - expected) < 1e-10

    def test_angle_shape(self) -> None:
        """Test that shape is L."""
        section = Angle(L1=0.1, L2=0.1, t=0.01)
        assert section._get_shape() == SectionShape.L

    def test_angle_inertia_positive(self) -> None:
        """Test that moments of inertia are positive."""
        section = Angle(L1=0.100, L2=0.080, t=0.008)
        assert section.Ix > 0
        assert section.Iy > 0

    def test_angle_invalid_thickness(self) -> None:
        """Test that thickness >= leg length raises error."""
        with pytest.raises(ValueError, match="Thickness"):
            Angle(L1=0.050, L2=0.100, t=0.060)


class TestChannel:
    """Tests for channel (C-shape) sections."""

    def test_create_channel(self) -> None:
        """Test creating a channel section."""
        section = Channel(name="C10x30", d=0.254, bf=0.077, tf=0.013, tw=0.010)
        assert section.d == 0.254
        assert section.bf == 0.077

    def test_channel_area(self) -> None:
        """Test area calculation."""
        section = Channel(d=0.200, bf=0.075, tf=0.010, tw=0.006)
        # A = hw * tw + 2 * bf * tf
        hw = 0.200 - 2 * 0.010
        expected = hw * 0.006 + 2 * 0.075 * 0.010
        assert abs(section.A - expected) < 1e-10

    def test_channel_web_height(self) -> None:
        """Test web height property."""
        section = Channel(d=0.200, bf=0.075, tf=0.010, tw=0.006)
        assert abs(section.hw - 0.180) < 1e-10

    def test_channel_shape(self) -> None:
        """Test that shape is C."""
        section = Channel(d=0.2, bf=0.075, tf=0.01, tw=0.006)
        assert section._get_shape() == SectionShape.C

    def test_channel_centroid_offset(self) -> None:
        """Test that centroid is not at geometric center."""
        section = Channel(d=0.200, bf=0.075, tf=0.010, tw=0.006)
        # Centroid should be between web back and flange tip
        xc = section._centroid_x
        assert 0 < xc < section.bf


class TestTSection:
    """Tests for T-section."""

    def test_create_t_section(self) -> None:
        """Test creating a T-section."""
        section = TSection(name="WT", d=0.200, bf=0.150, tf=0.015, tw=0.010)
        assert section.d == 0.200
        assert section.bf == 0.150

    def test_t_section_area(self) -> None:
        """Test area calculation."""
        section = TSection(d=0.200, bf=0.150, tf=0.015, tw=0.010)
        # A = bf * tf + hs * tw
        hs = 0.200 - 0.015
        expected = 0.150 * 0.015 + hs * 0.010
        assert abs(section.A - expected) < 1e-10

    def test_t_section_stem_height(self) -> None:
        """Test stem height property."""
        section = TSection(d=0.200, bf=0.150, tf=0.015, tw=0.010)
        assert abs(section.hs - 0.185) < 1e-10

    def test_t_section_shape(self) -> None:
        """Test that shape is WT."""
        section = TSection(d=0.2, bf=0.15, tf=0.015, tw=0.01)
        assert section._get_shape() == SectionShape.WT

    def test_t_section_centroid_offset(self) -> None:
        """Test that centroid is not at geometric center."""
        section = TSection(d=0.200, bf=0.150, tf=0.015, tw=0.010)
        # Centroid should be closer to flange (top) than bottom of stem
        yc = section._centroid_y
        assert yc > section.d / 2  # Above geometric center


class TestParametricSectionConversion:
    """Tests for converting parametric sections to standard Section."""

    def test_all_sections_convert_to_section(self) -> None:
        """Test that all parametric sections can convert to Section."""
        sections = [
            ISection(d=0.3, bf=0.15, tf=0.015, tw=0.01),
            RectangularSolid(B=0.2, H=0.3),
            RectangularHollow(B=0.2, H=0.3, t=0.01),
            CircularSolid(D=0.1),
            CircularHollow(D=0.1, t=0.005),
            Angle(L1=0.1, L2=0.1, t=0.01),
            Channel(d=0.2, bf=0.075, tf=0.01, tw=0.006),
            TSection(d=0.2, bf=0.15, tf=0.015, tw=0.01),
        ]

        for parametric in sections:
            section = parametric.to_section()
            assert section.A > 0
            assert section.Ix > 0
            assert section.Iy > 0
            assert section.is_custom is True
            assert section.standard == SectionStandard.CUSTOM

    def test_to_dict_serialization(self) -> None:
        """Test that parametric sections can serialize to dict."""
        section = ISection(name="Test", d=0.3, bf=0.15, tf=0.015, tw=0.01)
        data = section.to_dict()

        assert data["name"] == "Test"
        assert data["A"] > 0
        assert "Ix" in data
        assert "Iy" in data

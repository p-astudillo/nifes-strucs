"""Tests for Section Designer."""

from math import isclose, pi

import pytest

from paz.domain.sections.section import Section, SectionShape, SectionStandard
from paz.domain.sections.section_designer import (
    RegionShape,
    SectionDesigner,
    SectionRegion,
    create_built_up_section,
    create_double_angle,
)


class TestSectionRegion:
    """Tests for SectionRegion class."""

    def test_rectangle_properties(self) -> None:
        """Calculate rectangle properties."""
        region = SectionRegion(
            shape=RegionShape.RECTANGLE,
            width=0.3,  # 300mm
            height=0.5,  # 500mm
        )

        props = region.calculate_properties()

        # A = b * h = 0.3 * 0.5 = 0.15 m²
        assert isclose(props["A"], 0.15, rel_tol=1e-9)

        # Ix = b * h³ / 12 = 0.3 * 0.5³ / 12 = 0.003125 m⁴
        assert isclose(props["Ix_local"], 0.003125, rel_tol=1e-9)

        # Iy = h * b³ / 12 = 0.5 * 0.3³ / 12 = 0.001125 m⁴
        assert isclose(props["Iy_local"], 0.001125, rel_tol=1e-9)

    def test_circle_solid_properties(self) -> None:
        """Calculate solid circle properties."""
        region = SectionRegion(
            shape=RegionShape.CIRCLE,
            radius=0.15,  # 150mm radius
        )

        props = region.calculate_properties()

        # A = π * r² = π * 0.15² ≈ 0.0707 m²
        expected_A = pi * 0.15**2
        assert isclose(props["A"], expected_A, rel_tol=1e-9)

        # I = π * r⁴ / 4
        expected_I = pi * 0.15**4 / 4
        assert isclose(props["Ix_local"], expected_I, rel_tol=1e-9)
        assert isclose(props["Iy_local"], expected_I, rel_tol=1e-9)

    def test_circle_hollow_properties(self) -> None:
        """Calculate hollow circle properties."""
        region = SectionRegion(
            shape=RegionShape.CIRCLE,
            radius=0.15,
            inner_radius=0.12,
        )

        props = region.calculate_properties()

        # A = π * (r_o² - r_i²)
        expected_A = pi * (0.15**2 - 0.12**2)
        assert isclose(props["A"], expected_A, rel_tol=1e-9)

    def test_i_shape_properties(self) -> None:
        """Calculate I-shape properties."""
        region = SectionRegion(
            shape=RegionShape.I_SHAPE,
            d=0.350,    # 350mm depth
            bf=0.170,   # 170mm flange width
            tf=0.0115,  # 11.5mm flange thickness
            tw=0.0075,  # 7.5mm web thickness
        )

        props = region.calculate_properties()

        # Basic checks
        assert props["A"] > 0
        assert props["Ix_local"] > 0
        assert props["Iy_local"] > 0
        assert props["Ix_local"] > props["Iy_local"]  # Strong axis > weak axis

    def test_polygon_triangle_properties(self) -> None:
        """Calculate triangle polygon properties."""
        # Right triangle with base 0.3m and height 0.4m
        region = SectionRegion(
            shape=RegionShape.POLYGON,
            vertices=[(0, 0), (0.3, 0), (0, 0.4)],
        )

        props = region.calculate_properties()

        # A = 0.5 * base * height = 0.5 * 0.3 * 0.4 = 0.06 m²
        assert isclose(props["A"], 0.06, rel_tol=1e-6)

    def test_modular_ratio(self) -> None:
        """Modular ratio scales properties."""
        region = SectionRegion(
            shape=RegionShape.RECTANGLE,
            width=0.3,
            height=0.5,
            modular_ratio=2.0,
        )

        props = region.calculate_properties()

        # Properties should be doubled
        assert isclose(props["A"], 0.15 * 2.0, rel_tol=1e-9)

    def test_missing_parameters_raises(self) -> None:
        """Missing parameters raise error."""
        region = SectionRegion(shape=RegionShape.RECTANGLE)

        with pytest.raises(Exception):  # ValidationError
            region.calculate_properties()


class TestSectionDesigner:
    """Tests for SectionDesigner class."""

    def test_simple_rectangle(self) -> None:
        """Create simple rectangular section."""
        designer = SectionDesigner("Rect300x500")
        designer.add_rectangle(width=0.3, height=0.5)

        section = designer.build()

        assert section.name == "Rect300x500"
        assert section.shape == SectionShape.CUSTOM
        assert section.is_custom is True
        assert isclose(section.A, 0.15, rel_tol=1e-9)

    def test_composite_section(self) -> None:
        """Create composite section with multiple regions."""
        designer = SectionDesigner("CompositeBeam")

        # Main I-beam
        designer.add_i_shape(d=0.4, bf=0.2, tf=0.02, tw=0.01)

        # Top plate
        designer.add_rectangle(width=0.3, height=0.02, cy=0.21)

        section = designer.build()

        # Should have combined properties
        assert section.A > 0
        assert section.Ix > 0
        assert section.is_custom is True

    def test_parallel_axis_theorem(self) -> None:
        """Verify parallel axis theorem for offset regions."""
        # Two rectangles side by side
        designer = SectionDesigner("TwoRectangles")
        designer.add_rectangle(width=0.1, height=0.2, cx=-0.1)
        designer.add_rectangle(width=0.1, height=0.2, cx=0.1)

        section = designer.build()

        # Area = 2 * 0.1 * 0.2 = 0.04 m²
        assert isclose(section.A, 0.04, rel_tol=1e-9)

        # Iy should be greater than 2 * local Iy due to offset
        single_Iy = (0.2 * 0.1**3) / 12  # About centroid
        offset_contribution = 0.02 * 0.1**2  # A * d²
        expected_Iy = 2 * (single_Iy + offset_contribution)
        assert isclose(section.Iy, expected_Iy, rel_tol=1e-6)

    def test_method_chaining(self) -> None:
        """Designer methods return self for chaining."""
        section = (
            SectionDesigner("ChainedSection")
            .add_rectangle(width=0.3, height=0.5)
            .add_circle(radius=0.05, cx=0, cy=0.3)
            .set_description("Test section")
            .build()
        )

        assert section.name == "ChainedSection"
        assert section.description == "Test section"

    def test_empty_designer_raises(self) -> None:
        """Building empty designer raises error."""
        designer = SectionDesigner("Empty")

        with pytest.raises(Exception):  # ValidationError
            designer.build()

    def test_clear_regions(self) -> None:
        """Clear removes all regions."""
        designer = SectionDesigner("Test")
        designer.add_rectangle(width=0.3, height=0.5)
        designer.clear()

        assert len(designer.regions) == 0

    def test_calculated_radii(self) -> None:
        """Section has calculated radii of gyration."""
        designer = SectionDesigner("WithRadii")
        designer.add_rectangle(width=0.3, height=0.5)

        section = designer.build()

        assert section.rx is not None
        assert section.ry is not None
        assert section.rx > 0
        assert section.ry > 0

    def test_polygon_section(self) -> None:
        """Create section from polygon vertices."""
        designer = SectionDesigner("LShape")

        # L-shape as polygon
        vertices = [
            (0, 0),
            (0.3, 0),
            (0.3, 0.05),
            (0.05, 0.05),
            (0.05, 0.3),
            (0, 0.3),
        ]
        designer.add_polygon(vertices)

        section = designer.build()

        assert section.A > 0
        assert section.Ix > 0


class TestCreateDoubleAngle:
    """Tests for create_double_angle function."""

    def test_double_angle_doubles_area(self) -> None:
        """Double angle has 2x the area."""
        single = Section(
            name="L4x4x1/2",
            shape=SectionShape.L,
            A=0.005,
            Ix=0.000001,
            Iy=0.000001,
            bf=0.1,
        )

        double = create_double_angle(single, gap=0.01)

        assert isclose(double.A, 2 * single.A, rel_tol=1e-9)
        assert double.shape == SectionShape.DOUBLE_L
        assert "2L" in double.name

    def test_double_angle_custom_name(self) -> None:
        """Double angle with custom name."""
        single = Section(
            name="L4x4",
            shape=SectionShape.L,
            A=0.005,
            Ix=0.000001,
            Iy=0.000001,
        )

        double = create_double_angle(single, name="CustomDoubleAngle")

        assert double.name == "CustomDoubleAngle"


class TestCreateBuiltUpSection:
    """Tests for create_built_up_section function."""

    def test_built_up_with_top_plate(self) -> None:
        """Built-up section with top cover plate."""
        base = Section(
            name="W14x22",
            shape=SectionShape.W,
            A=0.00418,
            Ix=0.0001174,
            Iy=0.0000049,
            d=0.349,
            bf=0.127,
            tf=0.0085,
            tw=0.0058,
        )

        built_up = create_built_up_section(
            base,
            plate_width=0.2,
            plate_thickness=0.01,
            position="top",
        )

        # Should have more area than base
        assert built_up.A > base.A
        assert built_up.is_custom is True
        assert "PL" in built_up.name

    def test_built_up_with_both_plates(self) -> None:
        """Built-up section with plates on both flanges."""
        base = Section(
            name="W14x22",
            shape=SectionShape.W,
            A=0.00418,
            Ix=0.0001174,
            Iy=0.0000049,
            d=0.349,
            bf=0.127,
            tf=0.0085,
            tw=0.0058,
        )

        built_up = create_built_up_section(
            base,
            plate_width=0.2,
            plate_thickness=0.01,
            position="both",
        )

        # With both plates, should have even more area
        single_plate_area = 0.2 * 0.01
        expected_min_area = base.A + 2 * single_plate_area

        assert built_up.A >= expected_min_area * 0.9  # Allow some tolerance

    def test_built_up_missing_dimensions_raises(self) -> None:
        """Built-up with incomplete base section raises error."""
        base = Section(
            name="Incomplete",
            shape=SectionShape.W,
            A=0.005,
            Ix=0.0001,
            Iy=0.00001,
            # Missing d, bf, tf, tw
        )

        with pytest.raises(Exception):  # ValidationError
            create_built_up_section(base, plate_width=0.2, plate_thickness=0.01)

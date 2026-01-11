"""Tests for SectionDialog."""

import pytest

from paz.domain.sections.section import Section, SectionShape, SectionStandard
from paz.infrastructure.repositories.sections_repository import SectionsRepository


class TestSectionDialogLogic:
    """Test SectionDialog logic without Qt UI."""

    def test_repository_loads_sections(self) -> None:
        """Test that SectionsRepository loads sections."""
        repo = SectionsRepository()
        sections = repo.all()

        # Should have some predefined sections
        assert len(sections) > 0

    def test_repository_filter_by_shape(self) -> None:
        """Test filtering sections by shape."""
        repo = SectionsRepository()

        w_sections = repo.filter_by_shape(SectionShape.W)

        # All W sections should have W shape
        for section in w_sections:
            assert section.shape == SectionShape.W

    def test_repository_search(self) -> None:
        """Test searching sections by name."""
        repo = SectionsRepository()

        # Search for W14 sections
        results = repo.search("W14")

        # All results should contain W14
        for section in results:
            assert "W14" in section.name.upper()

    def test_repository_get_by_name(self) -> None:
        """Test getting section by exact name."""
        repo = SectionsRepository()

        # Get list of names and try to get one
        names = repo.get_names()
        if names:
            section = repo.get(names[0])
            assert section is not None
            assert section.name == names[0]

    def test_section_properties_are_valid(self) -> None:
        """Test that section properties are valid."""
        repo = SectionsRepository()

        for section in repo.all():
            # Area must be positive
            assert section.A > 0

            # Moments of inertia must be positive
            assert section.Ix > 0
            assert section.Iy > 0

            # Radii of gyration should be calculable
            rx = section.rx_calculated
            ry = section.ry_calculated
            assert rx > 0
            assert ry > 0

    def test_w_sections_have_dimensional_properties(self) -> None:
        """Test that W sections have depth and flange properties."""
        repo = SectionsRepository()

        w_sections = repo.filter_by_shape(SectionShape.W)

        for section in w_sections:
            # W sections should have d, bf, tw, tf
            assert section.d is not None and section.d > 0
            assert section.bf is not None and section.bf > 0
            assert section.tw is not None and section.tw > 0
            assert section.tf is not None and section.tf > 0

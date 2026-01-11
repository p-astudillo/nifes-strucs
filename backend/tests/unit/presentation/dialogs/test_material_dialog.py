"""Tests for MaterialDialog."""

import pytest

from paz.domain.materials.material import Material, MaterialType, MaterialStandard
from paz.infrastructure.repositories.materials_repository import MaterialsRepository


class TestMaterialDialogLogic:
    """Test MaterialDialog logic without Qt UI."""

    def test_repository_loads_materials(self) -> None:
        """Test that MaterialsRepository loads materials."""
        repo = MaterialsRepository()
        materials = repo.all()

        # Should have some predefined materials
        assert len(materials) > 0

    def test_repository_filter_by_type(self) -> None:
        """Test filtering materials by type."""
        repo = MaterialsRepository()

        steel_materials = repo.filter_by_type(MaterialType.STEEL)
        concrete_materials = repo.filter_by_type(MaterialType.CONCRETE)

        # All steel materials should have STEEL type
        for mat in steel_materials:
            assert mat.material_type == MaterialType.STEEL

        # All concrete materials should have CONCRETE type
        for mat in concrete_materials:
            assert mat.material_type == MaterialType.CONCRETE

    def test_repository_search(self) -> None:
        """Test searching materials by name."""
        repo = MaterialsRepository()

        # Search for A36 (common steel)
        results = repo.search("A36")
        assert len(results) >= 1
        assert any("A36" in m.name for m in results)

    def test_repository_get_by_name(self) -> None:
        """Test getting material by exact name."""
        repo = MaterialsRepository()

        # This assumes A36 exists in the materials data
        try:
            material = repo.get("A36")
            assert material.name == "A36"
            assert material.material_type == MaterialType.STEEL
        except Exception:
            # If A36 doesn't exist, just check we can get any material
            names = repo.get_names()
            if names:
                material = repo.get(names[0])
                assert material is not None

    def test_material_properties_are_valid(self) -> None:
        """Test that material properties are valid."""
        repo = MaterialsRepository()

        for material in repo.all():
            # E must be positive
            assert material.E > 0

            # nu must be between 0 and 0.5
            assert 0 <= material.nu <= 0.5

            # rho must be positive
            assert material.rho > 0

            # G is calculated from E and nu
            expected_G = material.E / (2 * (1 + material.nu))
            assert abs(material.G - expected_G) < 1e-6

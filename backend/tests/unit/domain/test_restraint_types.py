"""
Tests for restraint types (F39 - Tipos de Apoyo Avanzados).

Tests cover:
- RestraintType enum values
- Restraint.from_type() factory method
- Restraint.get_type() detection method
- All predefined restraint presets
"""

import pytest

from paz.domain.model.restraint import (
    FREE,
    FIXED,
    PINNED,
    ROLLER_X,
    ROLLER_Y,
    ROLLER_Z,
    VERTICAL_ONLY,
    Restraint,
    RestraintType,
    RESTRAINT_TYPE_LABELS,
    RESTRAINT_TYPE_DESCRIPTIONS,
)


class TestRestraintType:
    """Tests for RestraintType enum."""

    def test_enum_values(self):
        """All restraint types should have expected string values."""
        assert RestraintType.FREE.value == "free"
        assert RestraintType.FIXED.value == "fixed"
        assert RestraintType.PINNED.value == "pinned"
        assert RestraintType.ROLLER_X.value == "roller_x"
        assert RestraintType.ROLLER_Y.value == "roller_y"
        assert RestraintType.ROLLER_Z.value == "roller_z"
        assert RestraintType.VERTICAL_ONLY.value == "vertical_only"
        assert RestraintType.CUSTOM.value == "custom"

    def test_enum_from_string(self):
        """RestraintType should be creatable from string value."""
        assert RestraintType("free") == RestraintType.FREE
        assert RestraintType("fixed") == RestraintType.FIXED
        assert RestraintType("pinned") == RestraintType.PINNED

    def test_all_types_have_labels(self):
        """All restraint types should have UI labels."""
        for rt in RestraintType:
            assert rt in RESTRAINT_TYPE_LABELS
            assert isinstance(RESTRAINT_TYPE_LABELS[rt], str)
            assert len(RESTRAINT_TYPE_LABELS[rt]) > 0

    def test_all_types_have_descriptions(self):
        """All restraint types should have descriptions."""
        for rt in RestraintType:
            assert rt in RESTRAINT_TYPE_DESCRIPTIONS
            assert isinstance(RESTRAINT_TYPE_DESCRIPTIONS[rt], str)
            assert len(RESTRAINT_TYPE_DESCRIPTIONS[rt]) > 0


class TestRestraintPresets:
    """Tests for predefined restraint constants."""

    def test_free_preset(self):
        """FREE should have all DOFs free."""
        assert FREE.ux is False
        assert FREE.uy is False
        assert FREE.uz is False
        assert FREE.rx is False
        assert FREE.ry is False
        assert FREE.rz is False
        assert FREE.is_free is True

    def test_fixed_preset(self):
        """FIXED should have all DOFs restrained."""
        assert FIXED.ux is True
        assert FIXED.uy is True
        assert FIXED.uz is True
        assert FIXED.rx is True
        assert FIXED.ry is True
        assert FIXED.rz is True
        assert FIXED.is_fixed is True

    def test_pinned_preset(self):
        """PINNED should have translations restrained, rotations free."""
        assert PINNED.ux is True
        assert PINNED.uy is True
        assert PINNED.uz is True
        assert PINNED.rx is False
        assert PINNED.ry is False
        assert PINNED.rz is False
        assert PINNED.is_pinned is True

    def test_roller_x_preset(self):
        """ROLLER_X should be free in X, fixed in Y/Z."""
        assert ROLLER_X.ux is False
        assert ROLLER_X.uy is True
        assert ROLLER_X.uz is True
        assert ROLLER_X.rx is False
        assert ROLLER_X.ry is False
        assert ROLLER_X.rz is False

    def test_roller_y_preset(self):
        """ROLLER_Y should be free in Y, fixed in X/Z."""
        assert ROLLER_Y.ux is True
        assert ROLLER_Y.uy is False
        assert ROLLER_Y.uz is True
        assert ROLLER_Y.rx is False
        assert ROLLER_Y.ry is False
        assert ROLLER_Y.rz is False

    def test_roller_z_preset(self):
        """ROLLER_Z should be free in Z, fixed in X/Y."""
        assert ROLLER_Z.ux is True
        assert ROLLER_Z.uy is True
        assert ROLLER_Z.uz is False
        assert ROLLER_Z.rx is False
        assert ROLLER_Z.ry is False
        assert ROLLER_Z.rz is False

    def test_vertical_only_preset(self):
        """VERTICAL_ONLY should only have Uz restrained."""
        assert VERTICAL_ONLY.ux is False
        assert VERTICAL_ONLY.uy is False
        assert VERTICAL_ONLY.uz is True
        assert VERTICAL_ONLY.rx is False
        assert VERTICAL_ONLY.ry is False
        assert VERTICAL_ONLY.rz is False


class TestRestraintFromType:
    """Tests for Restraint.from_type() factory method."""

    def test_from_type_free(self):
        """from_type(FREE) should return FREE restraint."""
        r = Restraint.from_type(RestraintType.FREE)
        assert r == FREE

    def test_from_type_fixed(self):
        """from_type(FIXED) should return FIXED restraint."""
        r = Restraint.from_type(RestraintType.FIXED)
        assert r == FIXED

    def test_from_type_pinned(self):
        """from_type(PINNED) should return PINNED restraint."""
        r = Restraint.from_type(RestraintType.PINNED)
        assert r == PINNED

    def test_from_type_roller_x(self):
        """from_type(ROLLER_X) should return ROLLER_X restraint."""
        r = Restraint.from_type(RestraintType.ROLLER_X)
        assert r == ROLLER_X

    def test_from_type_roller_y(self):
        """from_type(ROLLER_Y) should return ROLLER_Y restraint."""
        r = Restraint.from_type(RestraintType.ROLLER_Y)
        assert r == ROLLER_Y

    def test_from_type_roller_z(self):
        """from_type(ROLLER_Z) should return ROLLER_Z restraint."""
        r = Restraint.from_type(RestraintType.ROLLER_Z)
        assert r == ROLLER_Z

    def test_from_type_vertical_only(self):
        """from_type(VERTICAL_ONLY) should return VERTICAL_ONLY restraint."""
        r = Restraint.from_type(RestraintType.VERTICAL_ONLY)
        assert r == VERTICAL_ONLY

    def test_from_type_custom_returns_free(self):
        """from_type(CUSTOM) should return FREE as starting point."""
        r = Restraint.from_type(RestraintType.CUSTOM)
        assert r == FREE

    def test_from_type_with_string(self):
        """from_type() should accept string values."""
        r = Restraint.from_type("fixed")
        assert r == FIXED

        r = Restraint.from_type("pinned")
        assert r == PINNED


class TestRestraintGetType:
    """Tests for Restraint.get_type() detection method."""

    def test_get_type_free(self):
        """get_type() should detect FREE type."""
        assert FREE.get_type() == RestraintType.FREE

    def test_get_type_fixed(self):
        """get_type() should detect FIXED type."""
        assert FIXED.get_type() == RestraintType.FIXED

    def test_get_type_pinned(self):
        """get_type() should detect PINNED type."""
        assert PINNED.get_type() == RestraintType.PINNED

    def test_get_type_roller_x(self):
        """get_type() should detect ROLLER_X type."""
        assert ROLLER_X.get_type() == RestraintType.ROLLER_X

    def test_get_type_roller_y(self):
        """get_type() should detect ROLLER_Y type."""
        assert ROLLER_Y.get_type() == RestraintType.ROLLER_Y

    def test_get_type_roller_z(self):
        """get_type() should detect ROLLER_Z type."""
        assert ROLLER_Z.get_type() == RestraintType.ROLLER_Z

    def test_get_type_vertical_only(self):
        """get_type() should detect VERTICAL_ONLY type."""
        assert VERTICAL_ONLY.get_type() == RestraintType.VERTICAL_ONLY

    def test_get_type_custom(self):
        """get_type() should return CUSTOM for non-standard configurations."""
        # Only Ux and Rz restrained - not a standard type
        custom = Restraint(ux=True, uy=False, uz=False, rx=False, ry=False, rz=True)
        assert custom.get_type() == RestraintType.CUSTOM

        # Only rotations restrained
        rotations_only = Restraint(
            ux=False, uy=False, uz=False, rx=True, ry=True, rz=True
        )
        assert rotations_only.get_type() == RestraintType.CUSTOM


class TestRestraintRoundtrip:
    """Tests for from_type -> get_type roundtrip."""

    @pytest.mark.parametrize(
        "restraint_type",
        [
            RestraintType.FREE,
            RestraintType.FIXED,
            RestraintType.PINNED,
            RestraintType.ROLLER_X,
            RestraintType.ROLLER_Y,
            RestraintType.ROLLER_Z,
            RestraintType.VERTICAL_ONLY,
        ],
    )
    def test_roundtrip(self, restraint_type):
        """from_type() and get_type() should be inverses for standard types."""
        restraint = Restraint.from_type(restraint_type)
        detected = restraint.get_type()
        assert detected == restraint_type


class TestRestraintSerialization:
    """Tests for restraint serialization with types."""

    def test_to_dict_includes_type(self):
        """to_dict() should work for all preset types."""
        for preset in [FREE, FIXED, PINNED, ROLLER_X, ROLLER_Y, ROLLER_Z, VERTICAL_ONLY]:
            d = preset.to_dict()
            assert "ux" in d
            assert "uy" in d
            assert "uz" in d
            assert "rx" in d
            assert "ry" in d
            assert "rz" in d

    def test_from_dict_roundtrip(self):
        """from_dict() should preserve all DOF values."""
        for preset in [FREE, FIXED, PINNED, ROLLER_X, ROLLER_Y, ROLLER_Z, VERTICAL_ONLY]:
            d = preset.to_dict()
            restored = Restraint.from_dict(d)
            assert restored == preset

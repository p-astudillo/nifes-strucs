"""Tests for DXF importer."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from paz.domain.model import StructuralModel
from paz.infrastructure.importers.dxf_importer import (
    DXFImporter,
    DXFImportSettings,
    import_model_from_dxf,
)


class TestDXFImportSettings:
    """Tests for DXFImportSettings."""

    def test_default_settings(self) -> None:
        """Default settings have sensible values."""
        settings = DXFImportSettings()

        assert settings.default_material == "Steel"
        assert settings.default_section == "W14x22"
        assert settings.scale == 1.0
        assert settings.layers is None
        assert settings.axis_map == ("x", "y", "z")

    def test_custom_settings(self) -> None:
        """Custom settings are applied."""
        settings = DXFImportSettings(
            default_material="Concrete",
            default_section="300x300",
            scale=0.001,
            layers=["BEAMS", "COLUMNS"],
        )

        assert settings.default_material == "Concrete"
        assert settings.default_section == "300x300"
        assert settings.scale == 0.001
        assert settings.layers == ["BEAMS", "COLUMNS"]


class TestDXFImporter:
    """Tests for DXFImporter class."""

    def test_init_creates_new_model(self) -> None:
        """Importer creates new model if none provided."""
        importer = DXFImporter()

        assert importer.model is not None
        assert isinstance(importer.model, StructuralModel)

    def test_init_uses_provided_model(self) -> None:
        """Importer uses provided model."""
        model = StructuralModel()
        model.add_node(0, 0, 0)

        importer = DXFImporter(model=model)

        assert importer.model is model
        assert importer.model.node_count == 1

    def test_file_not_found(self) -> None:
        """Import raises error for missing file."""
        importer = DXFImporter()

        with pytest.raises(Exception):  # ValidationError
            importer.import_file("/nonexistent/file.dxf")

    def test_layer_filter_none_allows_all(self) -> None:
        """None layers filter allows all layers."""
        settings = DXFImportSettings(layers=None)
        importer = DXFImporter(settings=settings)

        assert importer._layer_allowed("ANY_LAYER") is True
        assert importer._layer_allowed("ANOTHER") is True

    def test_layer_filter_restricts(self) -> None:
        """Layer filter restricts to specified layers."""
        settings = DXFImportSettings(layers=["BEAMS", "COLUMNS"])
        importer = DXFImporter(settings=settings)

        assert importer._layer_allowed("BEAMS") is True
        assert importer._layer_allowed("COLUMNS") is True
        assert importer._layer_allowed("OTHER") is False

    def test_transform_point_no_scale(self) -> None:
        """Transform point without scale."""
        settings = DXFImportSettings(scale=1.0)
        importer = DXFImporter(settings=settings)

        result = importer._transform_point((1.0, 2.0, 3.0))

        assert result == (1.0, 2.0, 3.0)

    def test_transform_point_with_scale(self) -> None:
        """Transform point with scale (mm to m)."""
        settings = DXFImportSettings(scale=0.001)
        importer = DXFImporter(settings=settings)

        result = importer._transform_point((1000.0, 2000.0, 3000.0))

        assert result == (1.0, 2.0, 3.0)

    def test_transform_point_with_axis_map(self) -> None:
        """Transform point with axis mapping."""
        settings = DXFImportSettings(axis_map=("y", "z", "x"))
        importer = DXFImporter(settings=settings)

        # Input: x=1, y=2, z=3
        # Output: (y, z, x) = (2, 3, 1)
        result = importer._transform_point((1.0, 2.0, 3.0))

        assert result == (2.0, 3.0, 1.0)

    def test_create_frame_from_line_new_nodes(self) -> None:
        """Create frame from line creates new nodes."""
        importer = DXFImporter()

        result = importer._create_frame_from_line((0, 0, 0), (5, 0, 0))

        assert result is not None
        new_nodes, new_frames = result
        assert new_nodes == 2
        assert new_frames == 1
        assert importer.model.node_count == 2
        assert importer.model.frame_count == 1

    def test_create_frame_from_line_reuses_nodes(self) -> None:
        """Create frame reuses existing coincident nodes."""
        importer = DXFImporter()

        # Create first line
        importer._create_frame_from_line((0, 0, 0), (5, 0, 0))

        # Create second line sharing endpoint
        result = importer._create_frame_from_line((5, 0, 0), (5, 5, 0))

        assert result is not None
        new_nodes, new_frames = result
        assert new_nodes == 1  # Only one new node
        assert new_frames == 1
        assert importer.model.node_count == 3  # Total nodes

    def test_create_frame_from_line_zero_length(self) -> None:
        """Zero-length line returns None."""
        importer = DXFImporter()

        result = importer._create_frame_from_line((0, 0, 0), (0, 0, 0))

        assert result is None

    def test_create_frame_from_line_duplicate_frame(self) -> None:
        """Duplicate frame is not created."""
        importer = DXFImporter()

        # Create first frame
        importer._create_frame_from_line((0, 0, 0), (5, 0, 0))

        # Try to create same frame again
        result = importer._create_frame_from_line((0, 0, 0), (5, 0, 0))

        assert result is not None
        new_nodes, new_frames = result
        assert new_frames == 0  # No new frame
        assert importer.model.frame_count == 1


class TestDXFImporterWithMockedEzdxf:
    """Tests using mocked ezdxf library."""

    @pytest.fixture
    def mock_ezdxf(self) -> MagicMock:
        """Create mock ezdxf module."""
        import sys
        mock_module = MagicMock()
        sys.modules["ezdxf"] = mock_module
        yield mock_module
        # Cleanup
        if "ezdxf" in sys.modules:
            del sys.modules["ezdxf"]

    def test_import_lines(self, tmp_path: Path) -> None:
        """Import LINE entities from DXF."""
        import ezdxf

        # Create actual DXF document
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_line((0, 0, 0), (5, 0, 0))
        msp.add_line((5, 0, 0), (5, 5, 0))

        dxf_file = tmp_path / "test.dxf"
        doc.saveas(str(dxf_file))

        importer = DXFImporter()
        counts = importer.import_file(dxf_file)

        assert counts["nodes"] == 3  # 3 unique endpoints
        assert counts["frames"] == 2

    def test_import_with_layer_filter(self, tmp_path: Path) -> None:
        """Import only from specified layers."""
        import ezdxf

        doc = ezdxf.new()
        msp = doc.modelspace()

        # Add line on BEAMS layer
        msp.add_line((0, 0, 0), (5, 0, 0), dxfattribs={"layer": "BEAMS"})
        # Add line on FURNITURE layer (should be filtered)
        msp.add_line((10, 0, 0), (15, 0, 0), dxfattribs={"layer": "FURNITURE"})

        dxf_file = tmp_path / "test.dxf"
        doc.saveas(str(dxf_file))

        settings = DXFImportSettings(layers=["BEAMS"])
        importer = DXFImporter(settings=settings)
        counts = importer.import_file(dxf_file)

        assert counts["frames"] == 1  # Only BEAMS layer

    def test_import_with_scale(self, tmp_path: Path) -> None:
        """Import with scale factor (mm to m)."""
        import ezdxf

        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_line((0, 0, 0), (5000, 0, 0))  # 5000 mm

        dxf_file = tmp_path / "test.dxf"
        doc.saveas(str(dxf_file))

        settings = DXFImportSettings(scale=0.001)  # mm to m
        importer = DXFImporter(settings=settings)
        importer.import_file(dxf_file)

        # Check that coordinates are scaled
        node = importer.model.get_node(2)  # End node
        assert node.x == 5.0  # 5000 * 0.001 = 5 m


class TestImportModelFromDXF:
    """Tests for convenience function."""

    def test_convenience_function(self, tmp_path: Path) -> None:
        """Test import_model_from_dxf convenience function."""
        import ezdxf

        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_line((0, 0, 0), (5, 0, 0))

        dxf_file = tmp_path / "test.dxf"
        doc.saveas(str(dxf_file))

        model = import_model_from_dxf(
            dxf_file,
            material="Concrete",
            section="300x300",
            scale=1.0,
        )

        assert model.node_count == 2
        assert model.frame_count == 1

        frame = model.get_frame(1)
        assert frame.material_name == "Concrete"
        assert frame.section_name == "300x300"

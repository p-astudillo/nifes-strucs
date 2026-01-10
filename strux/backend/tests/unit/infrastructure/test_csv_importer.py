"""Tests for CSV importer."""

from pathlib import Path

import pytest

from paz.domain.model import StructuralModel
from paz.infrastructure.importers.csv_importer import CSVImporter, import_model_from_csv


class TestCSVImporter:
    """Tests for CSVImporter class."""

    def test_import_nodes_basic(self, tmp_path: Path) -> None:
        """Import nodes from CSV file."""
        csv_content = """id,x,y,z,ux,uy,uz,rx,ry,rz
1,0,0,0,1,1,1,1,1,1
2,5,0,0,0,0,0,0,0,0
3,5,5,0,0,0,1,0,0,0
"""
        filepath = tmp_path / "nodes.csv"
        filepath.write_text(csv_content)

        importer = CSVImporter()
        count = importer.import_nodes(filepath)

        assert count == 3
        assert importer.model.node_count == 3

        # Check node 1 (FIXED)
        node1 = importer.model.get_node(1)
        assert node1.x == 0
        assert node1.y == 0
        assert node1.z == 0
        assert node1.restraint.ux is True
        assert node1.restraint.uy is True

        # Check node 2 (FREE)
        node2 = importer.model.get_node(2)
        assert node2.restraint.ux is False
        assert node2.restraint.uy is False

    def test_import_nodes_minimal_columns(self, tmp_path: Path) -> None:
        """Import nodes with minimal columns (id, x, y, z only)."""
        csv_content = """id,x,y,z
1,0,0,0
2,10,0,0
"""
        filepath = tmp_path / "nodes.csv"
        filepath.write_text(csv_content)

        importer = CSVImporter()
        count = importer.import_nodes(filepath)

        assert count == 2
        # Default restraint should be FREE
        node = importer.model.get_node(1)
        assert node.restraint.ux is False

    def test_import_nodes_skips_invalid_rows(self, tmp_path: Path) -> None:
        """Import skips invalid rows."""
        csv_content = """id,x,y,z
1,0,0,0
invalid,not,a,number
3,5,5,5
"""
        filepath = tmp_path / "nodes.csv"
        filepath.write_text(csv_content)

        importer = CSVImporter()
        count = importer.import_nodes(filepath)

        assert count == 2  # Only valid rows
        assert importer.model.node_count == 2

    def test_import_nodes_file_not_found(self) -> None:
        """Import raises error for missing file."""
        importer = CSVImporter()

        with pytest.raises(Exception):  # ValidationError
            importer.import_nodes("/nonexistent/path.csv")

    def test_import_frames_basic(self, tmp_path: Path) -> None:
        """Import frames from CSV file."""
        # First create nodes
        nodes_csv = """id,x,y,z
1,0,0,0
2,5,0,0
3,5,5,0
"""
        frames_csv = """id,node_i,node_j,material,section,rotation,label
1,1,2,Steel,W14x22,0,Beam1
2,2,3,Steel,W14x30,0.5,Column1
"""
        nodes_file = tmp_path / "nodes.csv"
        frames_file = tmp_path / "frames.csv"
        nodes_file.write_text(nodes_csv)
        frames_file.write_text(frames_csv)

        importer = CSVImporter()
        importer.import_nodes(nodes_file)
        count = importer.import_frames(frames_file)

        assert count == 2
        assert importer.model.frame_count == 2

        frame1 = importer.model.get_frame(1)
        assert frame1.node_i_id == 1
        assert frame1.node_j_id == 2
        assert frame1.material_name == "Steel"
        assert frame1.section_name == "W14x22"
        assert frame1.label == "Beam1"

    def test_import_frames_minimal_columns(self, tmp_path: Path) -> None:
        """Import frames with minimal columns."""
        nodes_csv = """id,x,y,z
1,0,0,0
2,5,0,0
"""
        frames_csv = """id,node_i,node_j,material,section
1,1,2,Steel,W14x22
"""
        nodes_file = tmp_path / "nodes.csv"
        frames_file = tmp_path / "frames.csv"
        nodes_file.write_text(nodes_csv)
        frames_file.write_text(frames_csv)

        importer = CSVImporter()
        importer.import_nodes(nodes_file)
        count = importer.import_frames(frames_file)

        assert count == 1
        frame = importer.model.get_frame(1)
        assert frame.rotation == 0.0
        assert frame.label == ""

    def test_import_from_directory(self, tmp_path: Path) -> None:
        """Import all files from directory."""
        nodes_csv = """id,x,y,z
1,0,0,0
2,5,0,0
"""
        frames_csv = """id,node_i,node_j,material,section
1,1,2,Steel,W14x22
"""
        (tmp_path / "nodes.csv").write_text(nodes_csv)
        (tmp_path / "frames.csv").write_text(frames_csv)

        importer = CSVImporter()
        counts = importer.import_from_directory(tmp_path)

        assert counts["nodes"] == 2
        assert counts["frames"] == 1

    def test_import_into_existing_model(self, tmp_path: Path) -> None:
        """Import into existing model."""
        model = StructuralModel()
        model.add_node(0, 0, 0)  # Pre-existing node

        csv_content = """id,x,y,z
10,10,0,0
11,10,10,0
"""
        filepath = tmp_path / "nodes.csv"
        filepath.write_text(csv_content)

        importer = CSVImporter(model)
        count = importer.import_nodes(filepath)

        assert count == 2
        assert model.node_count == 3  # 1 pre-existing + 2 imported


class TestImportModelFromCSV:
    """Tests for convenience function."""

    def test_import_model_from_csv(self, tmp_path: Path) -> None:
        """Import model using convenience function."""
        nodes_csv = """id,x,y,z
1,0,0,0
2,5,0,0
"""
        frames_csv = """id,node_i,node_j,material,section
1,1,2,Steel,W14x22
"""
        nodes_file = tmp_path / "nodes.csv"
        frames_file = tmp_path / "frames.csv"
        nodes_file.write_text(nodes_csv)
        frames_file.write_text(frames_csv)

        model = import_model_from_csv(nodes_file, frames_file)

        assert model.node_count == 2
        assert model.frame_count == 1

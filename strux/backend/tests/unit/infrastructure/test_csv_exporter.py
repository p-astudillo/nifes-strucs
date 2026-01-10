"""Tests for CSV exporter."""

import csv
from io import StringIO
from pathlib import Path

import pytest

from paz.domain.model import StructuralModel
from paz.domain.model.restraint import FIXED, FREE, PINNED
from paz.infrastructure.exporters.csv_exporter import CSVExporter


class TestCSVExporter:
    """Tests for CSVExporter class."""

    def test_export_nodes_empty_model(self) -> None:
        """Export nodes from empty model."""
        model = StructuralModel()
        exporter = CSVExporter(model)

        content = exporter.export_nodes()

        # Should have header only
        lines = content.strip().split("\n")
        assert len(lines) == 1
        assert "id" in lines[0]

    def test_export_nodes_with_data(self) -> None:
        """Export nodes with coordinates and restraints."""
        model = StructuralModel()
        model.add_node(0, 0, 0, restraint=FIXED)
        model.add_node(5, 0, 0, restraint=FREE)
        model.add_node(5, 5, 0, restraint=PINNED)

        exporter = CSVExporter(model)
        content = exporter.export_nodes()

        # Parse CSV
        reader = csv.DictReader(StringIO(content))
        rows = list(reader)

        assert len(rows) == 3

        # Check first node (FIXED)
        assert rows[0]["id"] == "1"
        assert rows[0]["x"] == "0"
        assert rows[0]["y"] == "0"
        assert rows[0]["z"] == "0"
        assert rows[0]["ux"] == "1"
        assert rows[0]["uy"] == "1"
        assert rows[0]["uz"] == "1"

        # Check second node (FREE)
        assert rows[1]["ux"] == "0"
        assert rows[1]["uy"] == "0"

    def test_export_nodes_to_file(self, tmp_path: Path) -> None:
        """Export nodes to file."""
        model = StructuralModel()
        model.add_node(1, 2, 3)
        model.add_node(4, 5, 6)

        exporter = CSVExporter(model)
        filepath = tmp_path / "nodes.csv"
        exporter.export_nodes(filepath)

        assert filepath.exists()
        content = filepath.read_text()
        assert "1,2,3" in content or "1.0,2.0,3.0" in content

    def test_export_frames_empty_model(self) -> None:
        """Export frames from empty model."""
        model = StructuralModel()
        exporter = CSVExporter(model)

        content = exporter.export_frames()

        lines = content.strip().split("\n")
        assert len(lines) == 1  # Header only

    def test_export_frames_with_data(self) -> None:
        """Export frames with properties."""
        model = StructuralModel()
        model.add_node(0, 0, 0)
        model.add_node(5, 0, 0)
        model.add_node(5, 5, 0)
        model.add_frame(1, 2, "Steel", "W14x22", label="Beam1")
        model.add_frame(2, 3, "Steel", "W14x22", rotation=0.5)

        exporter = CSVExporter(model)
        content = exporter.export_frames()

        reader = csv.DictReader(StringIO(content))
        rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["node_i"] == "1"
        assert rows[0]["node_j"] == "2"
        assert rows[0]["material"] == "Steel"
        assert rows[0]["section"] == "W14x22"
        assert rows[0]["label"] == "Beam1"

    def test_export_all(self, tmp_path: Path) -> None:
        """Export all model data to directory."""
        model = StructuralModel()
        model.add_node(0, 0, 0)
        model.add_node(5, 0, 0)
        model.add_frame(1, 2, "Steel", "W14x22")

        exporter = CSVExporter(model)
        files = exporter.export_all(tmp_path)

        assert "nodes" in files
        assert "frames" in files
        assert files["nodes"].exists()
        assert files["frames"].exists()

    def test_export_nodes_precision(self) -> None:
        """Export preserves coordinate precision."""
        model = StructuralModel()
        model.add_node(1.123456, 2.654321, 3.999999)

        exporter = CSVExporter(model)
        content = exporter.export_nodes()

        # Should preserve reasonable precision
        assert "1.1234" in content or "1.123456" in content

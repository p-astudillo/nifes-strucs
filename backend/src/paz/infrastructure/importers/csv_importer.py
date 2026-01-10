"""
CSV Importer for structural model data.

Imports nodes and frames from CSV files into a structural model.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

from paz.core.exceptions import ValidationError
from paz.core.logging_config import get_logger
from paz.domain.model import StructuralModel
from paz.domain.model.restraint import Restraint


if TYPE_CHECKING:
    pass


logger = get_logger("csv_importer")


class CSVImporter:
    """
    Import structural model data from CSV files.

    Supports importing:
    - Nodes with coordinates and restraints
    - Frames with connectivity and properties
    """

    def __init__(self, model: StructuralModel | None = None) -> None:
        """
        Initialize the importer.

        Args:
            model: Target model (creates new if None)
        """
        self._model = model if model is not None else StructuralModel()

    @property
    def model(self) -> StructuralModel:
        """Get the structural model."""
        return self._model

    def import_nodes(self, filepath: str | Path) -> int:
        """
        Import nodes from CSV file.

        Args:
            filepath: Path to CSV file

        Returns:
            Number of nodes imported

        Expected CSV columns: id, x, y, z, [ux, uy, uz, rx, ry, rz]
        Restraint columns are optional (default: all free)
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise ValidationError(f"File not found: {filepath}", field="filepath")

        count = 0

        with filepath.open(newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    node_id = int(row["id"])
                    x = float(row["x"])
                    y = float(row["y"])
                    z = float(row["z"])

                    # Parse restraints if present
                    restraint = Restraint(
                        ux=self._parse_bool(row.get("ux", "0")),
                        uy=self._parse_bool(row.get("uy", "0")),
                        uz=self._parse_bool(row.get("uz", "0")),
                        rx=self._parse_bool(row.get("rx", "0")),
                        ry=self._parse_bool(row.get("ry", "0")),
                        rz=self._parse_bool(row.get("rz", "0")),
                    )

                    self._model.add_node(
                        x=x,
                        y=y,
                        z=z,
                        restraint=restraint,
                        node_id=node_id,
                        check_duplicate=True,
                    )
                    count += 1

                except (KeyError, ValueError) as e:
                    logger.warning(f"Skipping invalid row: {row} - {e}")
                    continue

        logger.info(f"Imported {count} nodes from {filepath}")
        return count

    def import_frames(self, filepath: str | Path) -> int:
        """
        Import frames from CSV file.

        Args:
            filepath: Path to CSV file

        Returns:
            Number of frames imported

        Expected CSV columns: id, node_i, node_j, material, section, [rotation, label]
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise ValidationError(f"File not found: {filepath}", field="filepath")

        count = 0

        with filepath.open(newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    frame_id = int(row["id"])
                    node_i_id = int(row["node_i"])
                    node_j_id = int(row["node_j"])
                    material = row["material"]
                    section = row["section"]
                    rotation = float(row.get("rotation", "0"))
                    label = row.get("label", "")

                    self._model.add_frame(
                        node_i_id=node_i_id,
                        node_j_id=node_j_id,
                        material_name=material,
                        section_name=section,
                        rotation=rotation,
                        frame_id=frame_id,
                        label=label,
                    )
                    count += 1

                except (KeyError, ValueError) as e:
                    logger.warning(f"Skipping invalid row: {row} - {e}")
                    continue

        logger.info(f"Imported {count} frames from {filepath}")
        return count

    def import_from_directory(self, directory: str | Path) -> dict[str, int]:
        """
        Import all data from a directory.

        Looks for nodes.csv and frames.csv files.

        Args:
            directory: Directory containing CSV files

        Returns:
            Dictionary with counts of imported items
        """
        directory = Path(directory)
        counts: dict[str, int] = {}

        # Import nodes first (frames depend on nodes)
        nodes_file = directory / "nodes.csv"
        if nodes_file.exists():
            counts["nodes"] = self.import_nodes(nodes_file)

        # Import frames
        frames_file = directory / "frames.csv"
        if frames_file.exists():
            counts["frames"] = self.import_frames(frames_file)

        return counts

    @staticmethod
    def _parse_bool(value: str) -> bool:
        """Parse boolean from string (1/0, true/false, yes/no)."""
        return value.lower() in ("1", "true", "yes", "t", "y")


def import_model_from_csv(
    nodes_file: str | Path | None = None,
    frames_file: str | Path | None = None,
) -> StructuralModel:
    """
    Convenience function to import a model from CSV files.

    Args:
        nodes_file: Path to nodes CSV
        frames_file: Path to frames CSV

    Returns:
        New StructuralModel with imported data
    """
    importer = CSVImporter()

    if nodes_file:
        importer.import_nodes(nodes_file)

    if frames_file:
        importer.import_frames(frames_file)

    return importer.model

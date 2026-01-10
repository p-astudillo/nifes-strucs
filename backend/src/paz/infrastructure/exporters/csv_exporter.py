"""
CSV Exporter for structural model data.

Exports nodes, frames, materials, sections, and analysis results to CSV format.
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from paz.core.logging_config import get_logger


if TYPE_CHECKING:
    from paz.domain.model import StructuralModel
    from paz.domain.results import AnalysisResults


logger = get_logger("csv_exporter")


class CSVExporter:
    """
    Export structural model data to CSV files.

    Supports exporting:
    - Nodes with coordinates and restraints
    - Frames with connectivity and properties
    - Analysis results (displacements, forces)
    """

    def __init__(self, model: StructuralModel) -> None:
        """
        Initialize the exporter.

        Args:
            model: Structural model to export
        """
        self._model = model

    def export_nodes(self, filepath: str | Path | None = None) -> str:
        """
        Export nodes to CSV.

        Args:
            filepath: Output file path (None returns string)

        Returns:
            CSV content as string

        CSV columns: id, x, y, z, ux, uy, uz, rx, ry, rz
        (restraints: 1=fixed, 0=free)
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["id", "x", "y", "z", "ux", "uy", "uz", "rx", "ry", "rz"])

        # Data
        for node in self._model.nodes:
            r = node.restraint
            writer.writerow([
                node.id,
                node.x,
                node.y,
                node.z,
                1 if r.ux else 0,
                1 if r.uy else 0,
                1 if r.uz else 0,
                1 if r.rx else 0,
                1 if r.ry else 0,
                1 if r.rz else 0,
            ])

        content = output.getvalue()

        if filepath:
            Path(filepath).write_text(content)
            logger.info(f"Exported {self._model.node_count} nodes to {filepath}")

        return content

    def export_frames(self, filepath: str | Path | None = None) -> str:
        """
        Export frames to CSV.

        Args:
            filepath: Output file path (None returns string)

        Returns:
            CSV content as string

        CSV columns: id, node_i, node_j, material, section, rotation, label
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "id", "node_i", "node_j", "material", "section", "rotation", "label"
        ])

        # Data
        for frame in self._model.frames:
            writer.writerow([
                frame.id,
                frame.node_i_id,
                frame.node_j_id,
                frame.material_name,
                frame.section_name,
                frame.rotation,
                frame.label,
            ])

        content = output.getvalue()

        if filepath:
            Path(filepath).write_text(content)
            logger.info(f"Exported {self._model.frame_count} frames to {filepath}")

        return content

    def export_all(self, output_dir: str | Path) -> dict[str, Path]:
        """
        Export all model data to separate CSV files.

        Args:
            output_dir: Directory for output files

        Returns:
            Dictionary mapping data type to file path
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        files: dict[str, Path] = {}

        # Export nodes
        nodes_file = output_dir / "nodes.csv"
        self.export_nodes(nodes_file)
        files["nodes"] = nodes_file

        # Export frames
        frames_file = output_dir / "frames.csv"
        self.export_frames(frames_file)
        files["frames"] = frames_file

        logger.info(f"Exported model to {output_dir}")

        return files


class ResultsExporter:
    """
    Export analysis results to CSV files.
    """

    def __init__(self, results: AnalysisResults) -> None:
        """
        Initialize the results exporter.

        Args:
            results: Analysis results to export
        """
        self._results = results

    def export_displacements(self, filepath: str | Path | None = None) -> str:
        """
        Export nodal displacements to CSV.

        Args:
            filepath: Output file path (None returns string)

        Returns:
            CSV content as string

        CSV columns: node_id, Ux, Uy, Uz, Rx, Ry, Rz
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["node_id", "Ux", "Uy", "Uz", "Rx", "Ry", "Rz"])

        # Data
        for disp in self._results.displacements:
            writer.writerow([
                disp.node_id,
                disp.Ux,
                disp.Uy,
                disp.Uz,
                disp.Rx,
                disp.Ry,
                disp.Rz,
            ])

        content = output.getvalue()

        if filepath:
            Path(filepath).write_text(content)
            logger.info(f"Exported displacements to {filepath}")

        return content

    def export_reactions(self, filepath: str | Path | None = None) -> str:
        """
        Export support reactions to CSV.

        Args:
            filepath: Output file path (None returns string)

        Returns:
            CSV content as string

        CSV columns: node_id, Fx, Fy, Fz, Mx, My, Mz
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["node_id", "Fx", "Fy", "Fz", "Mx", "My", "Mz"])

        # Data
        for reaction in self._results.reactions:
            writer.writerow([
                reaction.node_id,
                reaction.Fx,
                reaction.Fy,
                reaction.Fz,
                reaction.Mx,
                reaction.My,
                reaction.Mz,
            ])

        content = output.getvalue()

        if filepath:
            Path(filepath).write_text(content)
            logger.info(f"Exported reactions to {filepath}")

        return content

    def export_frame_forces(self, filepath: str | Path | None = None) -> str:
        """
        Export frame internal forces to CSV.

        Args:
            filepath: Output file path (None returns string)

        Returns:
            CSV content as string

        CSV columns: frame_id, station, P, V2, V3, T, M2, M3
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["frame_id", "station", "P", "V2", "V3", "T", "M2", "M3"])

        # Data
        for frame_result in self._results.frame_results:
            for forces in frame_result.forces:
                writer.writerow([
                    frame_result.frame_id,
                    forces.station,
                    forces.P,
                    forces.V2,
                    forces.V3,
                    forces.T,
                    forces.M2,
                    forces.M3,
                ])

        content = output.getvalue()

        if filepath:
            Path(filepath).write_text(content)
            logger.info(f"Exported frame forces to {filepath}")

        return content

    def export_all(self, output_dir: str | Path) -> dict[str, Path]:
        """
        Export all results to separate CSV files.

        Args:
            output_dir: Directory for output files

        Returns:
            Dictionary mapping result type to file path
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        files: dict[str, Path] = {}

        # Displacements
        disp_file = output_dir / "displacements.csv"
        self.export_displacements(disp_file)
        files["displacements"] = disp_file

        # Reactions
        reactions_file = output_dir / "reactions.csv"
        self.export_reactions(reactions_file)
        files["reactions"] = reactions_file

        # Frame forces
        forces_file = output_dir / "frame_forces.csv"
        self.export_frame_forces(forces_file)
        files["frame_forces"] = forces_file

        logger.info(f"Exported results to {output_dir}")

        return files

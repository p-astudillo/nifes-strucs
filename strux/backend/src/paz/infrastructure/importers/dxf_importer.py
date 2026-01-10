"""
DXF/AutoCAD Importer for structural geometry.

Converts LINE entities from DXF files into nodes and frames.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from paz.core.constants import NODE_DUPLICATE_TOLERANCE
from paz.core.exceptions import ValidationError
from paz.core.logging_config import get_logger
from paz.domain.model import StructuralModel


if TYPE_CHECKING:
    pass


logger = get_logger("dxf_importer")


@dataclass
class DXFImportSettings:
    """Settings for DXF import."""

    # Default material and section for imported frames
    default_material: str = "Steel"
    default_section: str = "W14x22"

    # Tolerance for merging coincident nodes
    node_tolerance: float = NODE_DUPLICATE_TOLERANCE

    # Layer filter (None = all layers)
    layers: list[str] | None = None

    # Scale factor (e.g., 0.001 to convert mm to m)
    scale: float = 1.0

    # Coordinate mapping (DXF axes to model axes)
    # Default: DXF X->X, Y->Y, Z->Z
    axis_map: tuple[str, str, str] = ("x", "y", "z")


class DXFImporter:
    """
    Import structural geometry from DXF files.

    Converts LINE entities to nodes and frames. Polylines are
    decomposed into individual line segments.

    Features:
    - Automatic node merging at coincident endpoints
    - Layer filtering
    - Scale factor for unit conversion
    - Configurable default material/section
    """

    def __init__(
        self,
        model: StructuralModel | None = None,
        settings: DXFImportSettings | None = None,
    ) -> None:
        """
        Initialize the importer.

        Args:
            model: Target model (creates new if None)
            settings: Import settings (uses defaults if None)
        """
        self._model = model if model is not None else StructuralModel()
        self._settings = settings if settings is not None else DXFImportSettings()

    @property
    def model(self) -> StructuralModel:
        """Get the structural model."""
        return self._model

    @property
    def settings(self) -> DXFImportSettings:
        """Get import settings."""
        return self._settings

    def import_file(self, filepath: str | Path) -> dict[str, int]:
        """
        Import geometry from a DXF file.

        Args:
            filepath: Path to DXF file

        Returns:
            Dictionary with counts: {"nodes": n, "frames": m}

        Raises:
            ValidationError: If file not found or invalid
        """
        try:
            import ezdxf
        except ImportError as e:
            raise ValidationError(
                "ezdxf library required for DXF import. "
                "Install with: pip install ezdxf",
                field="dependency",
            ) from e

        filepath = Path(filepath)
        if not filepath.exists():
            raise ValidationError(f"File not found: {filepath}", field="filepath")

        try:
            doc = ezdxf.readfile(str(filepath))
        except Exception as e:
            raise ValidationError(f"Failed to read DXF file: {e}", field="filepath") from e

        # Get modelspace entities
        msp = doc.modelspace()

        nodes_created = 0
        frames_created = 0

        # Process LINE entities
        for entity in msp.query("LINE"):
            if not self._layer_allowed(entity.dxf.layer):
                continue

            start = self._transform_point(entity.dxf.start)
            end = self._transform_point(entity.dxf.end)

            result = self._create_frame_from_line(start, end)
            if result:
                nodes_created += result[0]
                frames_created += result[1]

        # Process LWPOLYLINE entities (2D polylines)
        for entity in msp.query("LWPOLYLINE"):
            if not self._layer_allowed(entity.dxf.layer):
                continue

            points = list(entity.get_points(format="xyz"))
            for i in range(len(points) - 1):
                start = self._transform_point(points[i])
                end = self._transform_point(points[i + 1])

                result = self._create_frame_from_line(start, end)
                if result:
                    nodes_created += result[0]
                    frames_created += result[1]

            # Handle closed polylines
            if entity.closed and len(points) > 2:
                start = self._transform_point(points[-1])
                end = self._transform_point(points[0])

                result = self._create_frame_from_line(start, end)
                if result:
                    nodes_created += result[0]
                    frames_created += result[1]

        # Process POLYLINE entities (3D polylines)
        for entity in msp.query("POLYLINE"):
            if not self._layer_allowed(entity.dxf.layer):
                continue

            points = [v.dxf.location for v in entity.vertices]
            for i in range(len(points) - 1):
                start = self._transform_point(points[i])
                end = self._transform_point(points[i + 1])

                result = self._create_frame_from_line(start, end)
                if result:
                    nodes_created += result[0]
                    frames_created += result[1]

            # Handle closed polylines
            if entity.is_closed and len(points) > 2:
                start = self._transform_point(points[-1])
                end = self._transform_point(points[0])

                result = self._create_frame_from_line(start, end)
                if result:
                    nodes_created += result[0]
                    frames_created += result[1]

        logger.info(
            f"Imported from {filepath}: {nodes_created} nodes, {frames_created} frames"
        )

        return {"nodes": nodes_created, "frames": frames_created}

    def _layer_allowed(self, layer: str) -> bool:
        """Check if layer should be imported."""
        if self._settings.layers is None:
            return True
        return layer in self._settings.layers

    def _transform_point(
        self, point: tuple[float, float, float] | object
    ) -> tuple[float, float, float]:
        """Apply scale and axis mapping to a point."""
        # Handle ezdxf Vec3 objects
        if hasattr(point, "x"):
            px, py, pz = point.x, point.y, point.z
        else:
            px, py, pz = point[0], point[1], point[2] if len(point) > 2 else 0.0

        # Apply scale
        px *= self._settings.scale
        py *= self._settings.scale
        pz *= self._settings.scale

        # Apply axis mapping
        coords = {"x": px, "y": py, "z": pz}
        return (
            coords[self._settings.axis_map[0]],
            coords[self._settings.axis_map[1]],
            coords[self._settings.axis_map[2]],
        )

    def _create_frame_from_line(
        self,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
    ) -> tuple[int, int] | None:
        """
        Create a frame from line endpoints.

        Returns:
            Tuple of (new_nodes_count, new_frames_count) or None if failed
        """
        new_nodes = 0

        # Get or create start node
        node_i = self._model.find_node_at(
            start[0], start[1], start[2], self._settings.node_tolerance
        )
        if node_i is None:
            node_i = self._model.add_node(start[0], start[1], start[2])
            new_nodes += 1

        # Get or create end node
        node_j = self._model.find_node_at(
            end[0], end[1], end[2], self._settings.node_tolerance
        )
        if node_j is None:
            node_j = self._model.add_node(end[0], end[1], end[2])
            new_nodes += 1

        # Skip if same node (zero-length line)
        if node_i.id == node_j.id:
            return None

        # Check if frame already exists
        existing = self._model.find_frame_between(node_i.id, node_j.id)
        if existing is not None:
            return (new_nodes, 0)

        # Create frame
        try:
            self._model.add_frame(
                node_i_id=node_i.id,
                node_j_id=node_j.id,
                material_name=self._settings.default_material,
                section_name=self._settings.default_section,
            )
            return (new_nodes, 1)
        except Exception as e:
            logger.warning(f"Failed to create frame: {e}")
            return (new_nodes, 0)


def import_model_from_dxf(
    filepath: str | Path,
    material: str = "Steel",
    section: str = "W14x22",
    scale: float = 1.0,
    layers: list[str] | None = None,
) -> StructuralModel:
    """
    Convenience function to import a model from DXF.

    Args:
        filepath: Path to DXF file
        material: Default material for frames
        section: Default section for frames
        scale: Scale factor (e.g., 0.001 for mm to m)
        layers: Layer filter (None = all)

    Returns:
        New StructuralModel with imported geometry
    """
    settings = DXFImportSettings(
        default_material=material,
        default_section=section,
        scale=scale,
        layers=layers,
    )

    importer = DXFImporter(settings=settings)
    importer.import_file(filepath)

    return importer.model

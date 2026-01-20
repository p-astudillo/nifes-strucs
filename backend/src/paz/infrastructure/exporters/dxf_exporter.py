"""
DXF Exporter for structural model data.

Exports nodes and frames to DXF format using ezdxf library.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import ezdxf
from ezdxf.enums import TextEntityAlignment

from paz.core.logging_config import get_logger


if TYPE_CHECKING:
    from paz.domain.model import StructuralModel


logger = get_logger("dxf_exporter")


class DXFExporter:
    """
    Export structural model data to DXF format.

    Exports:
    - Nodes as points with labels
    - Frames as lines connecting nodes
    - Supports (fixed nodes) as special markers
    """

    # Layer names
    LAYER_NODES = "NODES"
    LAYER_FRAMES = "FRAMES"
    LAYER_SUPPORTS = "SUPPORTS"
    LAYER_LABELS = "LABELS"

    def __init__(self, model: StructuralModel) -> None:
        """
        Initialize the exporter.

        Args:
            model: Structural model to export
        """
        self._model = model
        self._node_coords: dict[int, tuple[float, float, float]] = {}

    def export(self, filepath: str | Path | None = None) -> bytes:
        """
        Export model to DXF format.

        Args:
            filepath: Output file path (None returns bytes)

        Returns:
            DXF content as bytes
        """
        # Create new DXF document
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        # Create layers
        doc.layers.add(self.LAYER_NODES, color=3)  # Green
        doc.layers.add(self.LAYER_FRAMES, color=7)  # White
        doc.layers.add(self.LAYER_SUPPORTS, color=1)  # Red
        doc.layers.add(self.LAYER_LABELS, color=5)  # Blue

        # Build node coordinate map
        for node in self._model.nodes:
            self._node_coords[node.id] = (node.x, node.y, node.z)

        # Export nodes
        self._export_nodes(msp)

        # Export frames
        self._export_frames(msp)

        # Export supports
        self._export_supports(msp)

        # Save to file or return bytes
        if filepath:
            doc.saveas(str(filepath))
            logger.info(f"Exported model to DXF: {filepath}")
            return Path(filepath).read_bytes()
        else:
            # Return as bytes
            stream = BytesIO()
            doc.write(stream)
            return stream.getvalue()

    def _export_nodes(self, msp) -> None:
        """Export nodes as points with labels."""
        for node in self._model.nodes:
            coords = (node.x, node.y, node.z)

            # Add point
            msp.add_point(coords, dxfattribs={"layer": self.LAYER_NODES})

            # Add label
            label_offset = 0.1  # Offset for label
            msp.add_text(
                f"N{node.id}",
                height=0.15,
                dxfattribs={
                    "layer": self.LAYER_LABELS,
                    "insert": (coords[0] + label_offset, coords[1] + label_offset, coords[2]),
                },
            )

    def _export_frames(self, msp) -> None:
        """Export frames as lines."""
        for frame in self._model.frames:
            start = self._node_coords.get(frame.node_i_id)
            end = self._node_coords.get(frame.node_j_id)

            if start and end:
                msp.add_line(start, end, dxfattribs={"layer": self.LAYER_FRAMES})

                # Add frame label at midpoint
                mid = (
                    (start[0] + end[0]) / 2,
                    (start[1] + end[1]) / 2,
                    (start[2] + end[2]) / 2,
                )
                msp.add_text(
                    f"F{frame.id}",
                    height=0.12,
                    dxfattribs={
                        "layer": self.LAYER_LABELS,
                        "insert": mid,
                    },
                )

    def _export_supports(self, msp) -> None:
        """Export supports as triangular markers."""
        support_size = 0.2

        for node in self._model.nodes:
            if node.is_supported:
                x, y, z = node.x, node.y, node.z

                # Draw triangle marker for support
                points = [
                    (x, y, z),
                    (x - support_size, y - support_size, z),
                    (x + support_size, y - support_size, z),
                    (x, y, z),  # Close the triangle
                ]
                msp.add_lwpolyline(
                    [(p[0], p[1]) for p in points],
                    dxfattribs={"layer": self.LAYER_SUPPORTS},
                    close=True,
                )

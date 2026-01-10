"""
Rendering configuration for the 3D viewport.

Defines enums and settings for controlling visualization appearance.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class RenderMode(Enum):
    """Visual rendering modes for the structural model."""

    WIREFRAME = auto()
    SOLID = auto()
    WIREFRAME_SOLID = auto()


class DisplacementComponent(Enum):
    """Which displacement component to visualize."""

    UX = "Ux"
    UY = "Uy"
    UZ = "Uz"
    TOTAL = "Total"


class ColorMapType(Enum):
    """Available color maps for scalar visualization."""

    VIRIDIS = "viridis"
    RAINBOW = "rainbow"
    COOLWARM = "coolwarm"
    JET = "jet"


@dataclass
class ViewportSettings:
    """
    Configuration for viewport display.

    Controls rendering options, colors, and interaction settings.
    """

    # Rendering mode
    render_mode: RenderMode = RenderMode.WIREFRAME

    # Displacement visualization
    displacement_component: DisplacementComponent = DisplacementComponent.TOTAL
    color_map: ColorMapType = ColorMapType.VIRIDIS
    deformation_scale: float = 100.0

    # Visibility toggles
    show_original: bool = True
    show_deformed: bool = True
    show_nodes: bool = True
    show_supports: bool = True
    show_node_labels: bool = False
    show_frame_labels: bool = False

    # Appearance
    node_size: float = 10.0
    line_width: float = 2.0
    original_color: str = "gray"
    original_opacity: float = 0.3
    node_color: str = "blue"
    support_color: str = "green"
    background_color: str = "white"

    def validate(self) -> None:
        """
        Validate settings values.

        Raises:
            ValueError: If any setting is invalid
        """
        if not 1.0 <= self.deformation_scale <= 10000.0:
            msg = f"Deformation scale must be between 1 and 10000, got {self.deformation_scale}"
            raise ValueError(msg)

        if not 0.0 <= self.original_opacity <= 1.0:
            msg = f"Opacity must be between 0 and 1, got {self.original_opacity}"
            raise ValueError(msg)

        if self.node_size <= 0:
            msg = f"Node size must be positive, got {self.node_size}"
            raise ValueError(msg)

        if self.line_width <= 0:
            msg = f"Line width must be positive, got {self.line_width}"
            raise ValueError(msg)

    def copy(self) -> ViewportSettings:
        """Create a copy of the settings."""
        return ViewportSettings(
            render_mode=self.render_mode,
            displacement_component=self.displacement_component,
            color_map=self.color_map,
            deformation_scale=self.deformation_scale,
            show_original=self.show_original,
            show_deformed=self.show_deformed,
            show_nodes=self.show_nodes,
            show_supports=self.show_supports,
            show_node_labels=self.show_node_labels,
            show_frame_labels=self.show_frame_labels,
            node_size=self.node_size,
            line_width=self.line_width,
            original_color=self.original_color,
            original_opacity=self.original_opacity,
            node_color=self.node_color,
            support_color=self.support_color,
            background_color=self.background_color,
        )

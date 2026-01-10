"""
3D Viewport module for structural visualization.

Provides PyVista-Qt integration for rendering structural models and results.
"""

from paz.presentation.viewport.deformed_renderer import DeformedRenderer
from paz.presentation.viewport.extruded_renderer import (
    ExtrudedRenderer,
    ExtrudedSettings,
    get_color_for_material,
)
from paz.presentation.viewport.force_diagrams import (
    DiagramSettings,
    ForceDiagramRenderer,
    ForceType,
)
from paz.presentation.viewport.mesh_builder import MeshBuilder
from paz.presentation.viewport.render_modes import (
    ColorMapType,
    DisplacementComponent,
    RenderMode,
    ViewportSettings,
)
from paz.presentation.viewport.viewport_widget import ViewportWidget
from paz.presentation.widgets.color_scale import ColorScaleWidget


__all__ = [
    "ColorMapType",
    "ColorScaleWidget",
    "DeformedRenderer",
    "DiagramSettings",
    "DisplacementComponent",
    "ExtrudedRenderer",
    "ExtrudedSettings",
    "ForceDiagramRenderer",
    "ForceType",
    "MeshBuilder",
    "RenderMode",
    "ViewportSettings",
    "ViewportWidget",
    "get_color_for_material",
]

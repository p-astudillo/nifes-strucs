"""
Main 3D viewport widget with PyVista-Qt integration.

Provides interactive structural model visualization with deformed shape
rendering and displacement color mapping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from pyvistaqt import QtInteractor  # type: ignore[import-untyped]

from paz.core.grid_config import GridConfig
from paz.presentation.viewport.deformed_renderer import DeformedRenderer
from paz.presentation.viewport.extruded_renderer import (
    ExtrudedRenderer,
    get_color_for_material,
)
from paz.presentation.viewport.force_diagrams import (
    DiagramSettings,
    ForceDiagramRenderer,
    ForceType,
)
from paz.presentation.viewport.grid_layer import GridLayer
from paz.presentation.viewport.mesh_builder import MeshBuilder
from paz.presentation.viewport.render_modes import (
    DisplacementComponent,
    ViewportSettings,
)
from paz.presentation.widgets.color_scale import ColorScaleWidget


if TYPE_CHECKING:

    from paz.domain.model import StructuralModel
    from paz.domain.results import AnalysisResults
    from paz.domain.sections import Section


class ViewportWidget(QWidget):
    """
    Main 3D viewport widget with PyVista integration.

    Provides:
    - Original structure display
    - Deformed shape overlay with color mapping
    - Interactive controls (scale, component, load case)
    - Node picking with value tooltips
    - Screenshot export

    Signals:
        node_clicked(int): Emitted when a node is clicked, with node_id
        scale_changed(float): Emitted when deformation scale changes
        component_changed(str): Emitted when displacement component changes
        load_case_changed(str): Emitted when load case selection changes
    """

    node_clicked = Signal(int)
    scale_changed = Signal(float)
    component_changed = Signal(str)
    load_case_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the viewport widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self._settings = ViewportSettings()
        self._model: StructuralModel | None = None
        self._results: dict[str, AnalysisResults] = {}
        self._current_load_case_id: str | None = None

        # Renderers
        self._mesh_builder = MeshBuilder()
        self._deformed_renderer = DeformedRenderer()
        self._extruded_renderer = ExtrudedRenderer()
        self._diagram_renderer = ForceDiagramRenderer()
        self._diagram_settings = DiagramSettings()
        self._grid_layer = GridLayer()
        self._grid_config = GridConfig()

        # Section data for extruded rendering
        self._sections: dict[str, Section] = {}

        # Display mode flags
        self._show_force_diagrams = False
        self._show_extruded = False  # Toggle for solid/wireframe view
        self._show_grid = True  # Toggle for grid display
        self._current_force_type = ForceType.M3
        self._highlighted_frame_id: int | None = None

        # Force filtering range (None = no filter)
        self._force_filter_min: float | None = None
        self._force_filter_max: float | None = None

        # Actor tracking for cleanup
        self._original_actors: list[Any] = []
        self._deformed_actors: list[Any] = []
        self._extruded_actors: list[Any] = []
        self._grid_actors: list[Any] = []
        self._node_actors: list[Any] = []
        self._support_actors: list[Any] = []
        self._diagram_actors: list[Any] = []
        self._label_actors: list[Any] = []
        self._highlight_actors: list[Any] = []
        self._text_actor: Any = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create the UI layout with controls."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Control panel
        controls = QHBoxLayout()
        controls.setContentsMargins(5, 5, 5, 5)

        # Scale slider
        controls.addWidget(QLabel("Scale:"))
        self._scale_label = QLabel("100x")
        self._scale_label.setMinimumWidth(50)

        self._scale_slider = QSlider(Qt.Orientation.Horizontal)
        self._scale_slider.setRange(1, 1000)
        self._scale_slider.setValue(100)
        self._scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._scale_slider.setTickInterval(100)
        self._scale_slider.valueChanged.connect(self._on_scale_changed)
        controls.addWidget(self._scale_slider)
        controls.addWidget(self._scale_label)

        controls.addSpacing(20)

        # Component selector
        controls.addWidget(QLabel("Component:"))
        self._component_combo = QComboBox()
        self._component_combo.addItems(["Total", "Ux", "Uy", "Uz"])
        self._component_combo.setMinimumWidth(80)
        self._component_combo.currentTextChanged.connect(self._on_component_changed)
        controls.addWidget(self._component_combo)

        controls.addSpacing(20)

        # Load case selector
        controls.addWidget(QLabel("Load Case:"))
        self._load_case_combo = QComboBox()
        self._load_case_combo.setMinimumWidth(120)
        self._load_case_combo.currentTextChanged.connect(self._on_load_case_changed)
        controls.addWidget(self._load_case_combo)

        controls.addStretch()

        # Export button
        self._export_btn = QPushButton("Export PNG")
        self._export_btn.clicked.connect(self._on_export_clicked)
        controls.addWidget(self._export_btn)

        # Reset view button
        self._reset_btn = QPushButton("Reset View")
        self._reset_btn.clicked.connect(self.reset_camera)
        controls.addWidget(self._reset_btn)

        controls.addSpacing(10)

        # Solid view checkbox
        self._solid_checkbox = QCheckBox("Solid")
        self._solid_checkbox.setToolTip("Show extruded section profiles")
        self._solid_checkbox.stateChanged.connect(self._on_solid_toggled)
        controls.addWidget(self._solid_checkbox)

        # Grid checkbox
        self._grid_checkbox = QCheckBox("Grid")
        self._grid_checkbox.setToolTip("Show reference grid")
        self._grid_checkbox.setChecked(True)
        self._grid_checkbox.stateChanged.connect(self._on_grid_toggled)
        controls.addWidget(self._grid_checkbox)

        layout.addLayout(controls)

        # PyVista plotter
        self._plotter = QtInteractor(self, auto_update=False)
        self._plotter.set_background("white")
        # Skip anti-aliasing on macOS ARM due to rendering issues
        import platform
        if platform.machine() != "arm64":
            self._plotter.enable_anti_aliasing("ssaa")
        layout.addWidget(self._plotter.interactor, stretch=1)

        # Color scale
        self._color_scale = ColorScaleWidget()
        layout.addWidget(self._color_scale)

        # Enable point picking
        self._plotter.enable_point_picking(
            callback=self._on_point_picked,
            show_message=False,
            use_picker=True,
            pickable_window=False,
            show_point=False,
        )

    def set_model(self, model: StructuralModel) -> None:
        """
        Set the structural model to display.

        Args:
            model: Structural model with nodes and frames
        """
        self._model = model
        self._refresh_display()

    def set_results(self, results: dict[str, AnalysisResults]) -> None:
        """
        Set analysis results.

        Args:
            results: Dictionary mapping load_case_id to AnalysisResults
        """
        self._results = results
        self._update_load_case_combo()

        if results:
            first_key = next(iter(results.keys()))
            self._current_load_case_id = first_key
            self._load_case_combo.setCurrentText(first_key)

        self._refresh_display()

    def clear_results(self) -> None:
        """Clear all results and show only original structure."""
        self._results = {}
        self._current_load_case_id = None
        self._load_case_combo.clear()
        self._refresh_display()

    def set_sections(self, sections: dict[str, Section]) -> None:
        """
        Set section data for extruded rendering.

        Args:
            sections: Dictionary mapping section_id to Section objects
        """
        self._sections = sections
        self._extruded_renderer.clear_cache()
        if self._show_extruded:
            self._refresh_display()

    def set_extruded_view(self, enabled: bool) -> None:
        """
        Enable or disable extruded (solid) view.

        Args:
            enabled: Whether to show extruded sections
        """
        if self._show_extruded != enabled:
            self._show_extruded = enabled
            self._solid_checkbox.setChecked(enabled)
            self._refresh_display()

    def is_extruded_view(self) -> bool:
        """Check if extruded view is enabled."""
        return self._show_extruded

    def _on_solid_toggled(self, state: int) -> None:
        """Handle solid view checkbox toggle."""
        self._show_extruded = state != 0
        self._refresh_display()

    def _on_grid_toggled(self, state: int) -> None:
        """Handle grid checkbox toggle."""
        self._show_grid = state != 0
        self._refresh_display()

    def set_grid_config(self, config: GridConfig) -> None:
        """Set grid configuration."""
        self._grid_config = config
        self._grid_layer.config = config
        if self._show_grid:
            self._refresh_display()

    def get_grid_config(self) -> GridConfig:
        """Get current grid configuration."""
        return self._grid_config.copy()

    def set_grid_visible(self, visible: bool) -> None:
        """Set grid visibility."""
        if self._show_grid != visible:
            self._show_grid = visible
            self._grid_checkbox.setChecked(visible)
            self._refresh_display()

    def get_settings(self) -> ViewportSettings:
        """Get current viewport settings."""
        return self._settings.copy()

    def set_settings(self, settings: ViewportSettings) -> None:
        """
        Apply viewport settings.

        Args:
            settings: New settings to apply
        """
        self._settings = settings

        # Update UI to match settings
        self._scale_slider.setValue(int(settings.deformation_scale))
        self._component_combo.setCurrentText(settings.displacement_component.value)

        self._refresh_display()

    def reset_camera(self) -> None:
        """Reset camera to fit all geometry."""
        self._plotter.reset_camera()
        self._plotter.view_isometric()

    def export_screenshot(self, filename: str | None = None) -> str | None:
        """
        Export current view as PNG image.

        Args:
            filename: Output filename (will prompt if None)

        Returns:
            Filename if saved, None if cancelled
        """
        if filename is None:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Screenshot",
                "viewport.png",
                "PNG Files (*.png);;All Files (*)",
            )

        if filename:
            self._plotter.screenshot(filename)
            return filename

        return None

    def _update_load_case_combo(self) -> None:
        """Update load case dropdown options."""
        self._load_case_combo.blockSignals(True)
        self._load_case_combo.clear()

        for case_id in self._results:
            self._load_case_combo.addItem(str(case_id))

        self._load_case_combo.blockSignals(False)

    def _refresh_display(self) -> None:
        """Rebuild and render all geometry."""
        self._clear_actors()

        if self._model is None:
            self._plotter.render()
            return

        # Build and display original structure
        if self._settings.show_original:
            self._render_original()

        # Build and display deformed structure
        results = self._get_current_results()
        if self._settings.show_deformed and results and results.success:
            self._render_deformed(results)

        # Add nodes
        if self._settings.show_nodes:
            self._render_nodes()

        # Add supports
        if self._settings.show_supports:
            self._render_supports()

        # Add force diagrams
        results = self._get_current_results()
        if self._show_force_diagrams and results and results.success:
            self._render_force_diagrams(results)

        # Add frame highlight
        if self._highlighted_frame_id is not None:
            self._render_frame_highlight()

        # Render grid
        if self._show_grid:
            self._render_grid()

        self._plotter.reset_camera()
        self._plotter.render()

    def _clear_actors(self) -> None:
        """Remove all actors from the plotter."""
        for actor in self._original_actors:
            self._plotter.remove_actor(actor, render=False)
        self._original_actors.clear()

        for actor in self._deformed_actors:
            self._plotter.remove_actor(actor, render=False)
        self._deformed_actors.clear()

        for actor in self._extruded_actors:
            self._plotter.remove_actor(actor, render=False)
        self._extruded_actors.clear()

        for actor in self._grid_actors:
            self._plotter.remove_actor(actor, render=False)
        self._grid_actors.clear()

        for actor in self._node_actors:
            self._plotter.remove_actor(actor, render=False)
        self._node_actors.clear()

        for actor in self._support_actors:
            self._plotter.remove_actor(actor, render=False)
        self._support_actors.clear()

        for actor in self._diagram_actors:
            self._plotter.remove_actor(actor, render=False)
        self._diagram_actors.clear()

        for actor in self._label_actors:
            self._plotter.remove_actor(actor, render=False)
        self._label_actors.clear()

        for actor in self._highlight_actors:
            self._plotter.remove_actor(actor, render=False)
        self._highlight_actors.clear()

        if self._text_actor is not None:
            self._plotter.remove_actor(self._text_actor, render=False)
            self._text_actor = None

    def _render_original(self) -> None:
        """Render the original (undeformed) structure."""
        if self._model is None:
            return

        if self._show_extruded and self._sections:
            self._render_extruded()
        else:
            self._render_wireframe()

    def _render_wireframe(self) -> None:
        """Render structure as wireframe lines."""
        if self._model is None:
            return

        mesh = self._mesh_builder.build_frame_mesh(self._model)
        if mesh.n_points == 0:
            return

        actor = self._plotter.add_mesh(
            mesh,
            color=self._settings.original_color,
            opacity=self._settings.original_opacity,
            line_width=self._settings.line_width,
            render_lines_as_tubes=False,
            name="original_structure",
        )
        self._original_actors.append(actor)

    def _render_extruded(self) -> None:
        """Render structure with extruded section profiles."""
        if self._model is None or not self._sections:
            return

        # Build meshes by material for color coding
        material_meshes = self._extruded_renderer.build_extruded_mesh_by_material(
            self._model, self._sections
        )

        for material_id, mesh in material_meshes.items():
            if mesh.n_points == 0:
                continue

            color = get_color_for_material(material_id)
            actor = self._plotter.add_mesh(
                mesh,
                color=color,
                opacity=self._settings.original_opacity,
                smooth_shading=True,
                name=f"extruded_{material_id}",
            )
            self._extruded_actors.append(actor)

    def _render_grid(self) -> None:
        """Render the reference grid."""
        self._grid_layer.config = self._grid_config

        meshes = self._grid_layer.build_meshes()

        # Render minor grid lines first (underneath major)
        if meshes.minor is not None and meshes.minor.n_points > 0:
            actor = self._plotter.add_mesh(
                meshes.minor,
                color=self._grid_layer.get_minor_color(),
                line_width=self._grid_config.minor_line_width,
                opacity=self._grid_config.opacity * 0.5,
                render_lines_as_tubes=False,
                name="grid_minor",
            )
            self._grid_actors.append(actor)

        # Render major grid lines
        if meshes.major is not None and meshes.major.n_points > 0:
            actor = self._plotter.add_mesh(
                meshes.major,
                color=self._grid_layer.get_major_color(),
                line_width=self._grid_config.major_line_width,
                opacity=self._grid_config.opacity,
                render_lines_as_tubes=False,
                name="grid_major",
            )
            self._grid_actors.append(actor)

    def _render_deformed(self, results: AnalysisResults) -> None:
        """Render the deformed structure with color mapping."""
        if self._model is None:
            return

        mesh, scalars = self._deformed_renderer.build_deformed_mesh(
            model=self._model,
            results=results,
            scale=self._settings.deformation_scale,
            component=self._settings.displacement_component,
        )

        if mesh.n_points == 0:
            return

        # Add scalars to mesh
        mesh["displacement"] = scalars

        actor = self._plotter.add_mesh(
            mesh,
            scalars="displacement",
            cmap=self._settings.color_map.value,
            line_width=self._settings.line_width + 1,
            render_lines_as_tubes=False,
            show_scalar_bar=False,
            name="deformed_structure",
        )
        self._deformed_actors.append(actor)

        # Update color scale
        if len(scalars) > 0:
            self._color_scale.set_range(float(scalars.min()), float(scalars.max()))
            self._color_scale.set_colormap(self._settings.color_map.value)
            self._color_scale.set_title(self._settings.displacement_component.value)

    def _render_nodes(self) -> None:
        """Render node point markers."""
        if self._model is None:
            return

        results = self._get_current_results()

        if results and results.success and self._settings.show_deformed:
            # Show deformed node positions
            point_cloud, scalars = self._deformed_renderer.build_deformed_nodes(
                model=self._model,
                results=results,
                scale=self._settings.deformation_scale,
                component=self._settings.displacement_component,
            )
        else:
            # Show original node positions
            point_cloud = self._mesh_builder.build_node_points(self._model)
            scalars = None

        if point_cloud.n_points == 0:
            return

        if scalars is not None and len(scalars) > 0:
            point_cloud["displacement"] = scalars
            actor = self._plotter.add_mesh(
                point_cloud,
                scalars="displacement",
                cmap=self._settings.color_map.value,
                point_size=self._settings.node_size,
                render_points_as_spheres=True,
                show_scalar_bar=False,
                name="nodes",
            )
        else:
            actor = self._plotter.add_mesh(
                point_cloud,
                color=self._settings.node_color,
                point_size=self._settings.node_size,
                render_points_as_spheres=True,
                name="nodes",
            )

        self._node_actors.append(actor)

    def _render_supports(self) -> None:
        """Render support symbol glyphs."""
        if self._model is None:
            return

        support_mesh = self._mesh_builder.build_support_glyphs(self._model)
        if support_mesh is None:
            return

        actor = self._plotter.add_mesh(
            support_mesh,
            color=self._settings.support_color,
            opacity=0.8,
            name="supports",
        )
        self._support_actors.append(actor)

    def _get_current_results(self) -> AnalysisResults | None:
        """Get results for current load case."""
        if self._current_load_case_id and self._current_load_case_id in self._results:
            return self._results[self._current_load_case_id]
        return None

    def _on_scale_changed(self, value: int) -> None:
        """Handle scale slider change."""
        self._settings.deformation_scale = float(value)
        self._scale_label.setText(f"{value}x")
        self.scale_changed.emit(float(value))
        self._refresh_display()

    def _on_component_changed(self, component: str) -> None:
        """Handle component selection change."""
        component_map = {
            "Total": DisplacementComponent.TOTAL,
            "Ux": DisplacementComponent.UX,
            "Uy": DisplacementComponent.UY,
            "Uz": DisplacementComponent.UZ,
        }
        self._settings.displacement_component = component_map.get(
            component, DisplacementComponent.TOTAL
        )
        self.component_changed.emit(component)
        self._refresh_display()

    def _on_load_case_changed(self, case_name: str) -> None:
        """Handle load case selection change."""
        if case_name:
            self._current_load_case_id = case_name
            self.load_case_changed.emit(case_name)
            self._refresh_display()

    def _on_export_clicked(self) -> None:
        """Handle export button click."""
        self.export_screenshot()

    def _on_point_picked(self, point: np.ndarray) -> None:
        """Handle point picking for node selection."""
        if self._model is None or point is None:
            return

        # Find nearest node to picked point
        min_dist = float("inf")
        nearest_node_id: int | None = None

        for node in self._model.nodes:
            dist = np.sqrt(
                (node.x - point[0]) ** 2
                + (node.y - point[1]) ** 2
                + (node.z - point[2]) ** 2
            )
            if dist < min_dist:
                min_dist = dist
                nearest_node_id = node.id

        # Only select if close enough (within 10% of model size)
        if nearest_node_id is not None and min_dist < self._get_model_size() * 0.1:
            self.node_clicked.emit(nearest_node_id)
            self._show_node_tooltip(nearest_node_id)

    def _show_node_tooltip(self, node_id: int) -> None:
        """Display displacement values for clicked node."""
        if self._model is None:
            return

        results = self._get_current_results()
        node = self._model.get_node(node_id)

        if results and results.success:
            disp = results.get_displacement(node_id)
            if disp:
                text = (
                    f"Node {node_id}\n"
                    f"Ux: {disp.Ux * 1000:.4f} mm\n"
                    f"Uy: {disp.Uy * 1000:.4f} mm\n"
                    f"Uz: {disp.Uz * 1000:.4f} mm\n"
                    f"Total: {disp.translation_magnitude * 1000:.4f} mm"
                )
            else:
                text = f"Node {node_id}\n(No displacement data)"
        else:
            text = (
                f"Node {node_id}\n"
                f"X: {node.x:.3f} m\n"
                f"Y: {node.y:.3f} m\n"
                f"Z: {node.z:.3f} m"
            )

        # Remove old text actor
        if self._text_actor is not None:
            self._plotter.remove_actor(self._text_actor, render=False)

        # Add new text
        self._text_actor = self._plotter.add_text(
            text,
            position="upper_left",
            font_size=10,
            color="black",
            name="node_info",
        )

        self._plotter.render()

    def _get_model_size(self) -> float:
        """Get approximate model size for picking tolerance."""
        if self._model is None or not self._model.nodes:
            return 1.0

        xs = [n.x for n in self._model.nodes]
        ys = [n.y for n in self._model.nodes]
        zs = [n.z for n in self._model.nodes]

        dx = max(xs) - min(xs) if xs else 0
        dy = max(ys) - min(ys) if ys else 0
        dz = max(zs) - min(zs) if zs else 0

        return max(dx, dy, dz, 1.0)

    # Force diagram methods

    def show_force_diagrams(self, show: bool = True) -> None:
        """
        Enable or disable force diagram display.

        Args:
            show: True to show diagrams, False to hide
        """
        self._show_force_diagrams = show
        self._refresh_display()

    def set_force_type(self, force_type: ForceType) -> None:
        """
        Set the type of force to display in diagrams.

        Args:
            force_type: Force type (P, V2, V3, T, M2, M3)
        """
        self._current_force_type = force_type
        self._diagram_settings.force_type = force_type
        if self._show_force_diagrams:
            self._refresh_display()

    def get_force_type(self) -> ForceType:
        """Get current force type for diagrams."""
        return self._current_force_type

    def set_diagram_scale(self, scale: float) -> None:
        """
        Set the scale factor for force diagrams.

        Args:
            scale: Scale factor (typically 0.01 to 1.0)
        """
        self._diagram_settings.scale = scale
        if self._show_force_diagrams:
            self._refresh_display()

    def set_force_filter_range(
        self, min_val: float | None, max_val: float | None
    ) -> None:
        """
        Set the force range filter for diagram display.

        Only frames with forces in this range will be displayed.

        Args:
            min_val: Minimum absolute force value (None = no minimum)
            max_val: Maximum absolute force value (None = no maximum)
        """
        self._force_filter_min = min_val
        self._force_filter_max = max_val
        if self._show_force_diagrams:
            self._refresh_display()

    def clear_force_filter(self) -> None:
        """Clear force range filter to show all frames."""
        self._force_filter_min = None
        self._force_filter_max = None
        if self._show_force_diagrams:
            self._refresh_display()

    def get_force_filter_range(self) -> tuple[float | None, float | None]:
        """Get current force filter range."""
        return (self._force_filter_min, self._force_filter_max)

    def _frame_passes_filter(self, frame_id: int, results: AnalysisResults) -> bool:
        """Check if frame passes the current force filter."""
        if self._force_filter_min is None and self._force_filter_max is None:
            return True

        frame_result = results.get_frame_result(frame_id)
        if frame_result is None:
            return False

        # Find max absolute value for this frame
        max_abs = 0.0
        for forces in frame_result.forces:
            val = self._get_force_value_for_filter(forces)
            max_abs = max(max_abs, abs(val))

        # Check against filter range
        if self._force_filter_min is not None and max_abs < self._force_filter_min:
            return False
        if self._force_filter_max is not None and max_abs > self._force_filter_max:
            return False

        return True

    def _get_force_value_for_filter(self, forces: object) -> float:
        """Extract force value based on current force type."""
        if self._current_force_type == ForceType.P:
            return float(getattr(forces, "P", 0.0))
        if self._current_force_type == ForceType.V2:
            return float(getattr(forces, "V2", 0.0))
        if self._current_force_type == ForceType.V3:
            return float(getattr(forces, "V3", 0.0))
        if self._current_force_type == ForceType.T:
            return float(getattr(forces, "T", 0.0))
        if self._current_force_type == ForceType.M2:
            return float(getattr(forces, "M2", 0.0))
        if self._current_force_type == ForceType.M3:
            return float(getattr(forces, "M3", 0.0))
        return 0.0

    def highlight_frame(self, frame_id: int | None) -> None:
        """
        Highlight a specific frame.

        Args:
            frame_id: Frame ID to highlight, or None to clear
        """
        self._highlighted_frame_id = frame_id
        self._refresh_display()

    def clear_highlight(self) -> None:
        """Clear frame highlighting."""
        self._highlighted_frame_id = None
        self._refresh_display()

    def _render_force_diagrams(self, results: AnalysisResults) -> None:
        """Render force diagrams for all frames."""
        if self._model is None:
            return

        self._diagram_settings.force_type = self._current_force_type

        # Calculate filtered frame IDs
        filtered_frame_ids = self._get_filtered_frame_ids(results)

        # Build filled diagram mesh
        mesh, scalars = self._diagram_renderer.build_filled_diagram_mesh(
            model=self._model,
            results=results,
            force_type=self._current_force_type,
            frame_ids=filtered_frame_ids,
        )

        if mesh.n_points == 0:
            return

        # Add scalars for coloring
        mesh["force"] = scalars

        # Use diverging colormap for positive/negative
        actor = self._plotter.add_mesh(
            mesh,
            scalars="force",
            cmap="coolwarm",
            opacity=self._diagram_settings.fill_opacity,
            show_scalar_bar=False,
            name="force_diagrams",
        )
        self._diagram_actors.append(actor)

        # Also add outline
        outline_mesh, outline_scalars = self._diagram_renderer.build_diagram_mesh(
            model=self._model,
            results=results,
            force_type=self._current_force_type,
            frame_ids=filtered_frame_ids,
        )

        if outline_mesh.n_points > 0:
            outline_mesh["force"] = outline_scalars
            outline_actor = self._plotter.add_mesh(
                outline_mesh,
                scalars="force",
                cmap="coolwarm",
                line_width=self._diagram_settings.line_width,
                show_scalar_bar=False,
                name="force_diagram_outline",
            )
            self._diagram_actors.append(outline_actor)

        # Update color scale for force diagrams
        extremes = self._diagram_renderer.get_global_extremes(
            results, self._current_force_type
        )
        if extremes["abs_max"] > 0:
            self._color_scale.set_range(extremes["min"], extremes["max"])
            self._color_scale.set_colormap("coolwarm")
            self._color_scale.set_title(self._current_force_type.value)
            self._color_scale.set_unit("kN" if self._current_force_type == ForceType.P else "kN-m")

        # Add value labels if enabled
        if self._diagram_settings.show_values:
            self._render_force_labels(results, filtered_frame_ids)

    def _get_filtered_frame_ids(self, results: AnalysisResults) -> set[int] | None:
        """Get set of frame IDs that pass the current filter."""
        if self._force_filter_min is None and self._force_filter_max is None:
            return None  # No filter, include all frames

        if self._model is None:
            return None

        filtered_ids: set[int] = set()
        for frame in self._model.frames:
            if self._frame_passes_filter(frame.id, results):
                filtered_ids.add(frame.id)

        return filtered_ids if filtered_ids else None

    def _render_force_labels(
        self,
        results: AnalysisResults,
        frame_ids: set[int] | None = None,
    ) -> None:
        """Render value labels on force diagrams."""
        if self._model is None:
            return

        import pyvista as pv

        positions, labels = self._diagram_renderer.get_value_labels(
            model=self._model,
            results=results,
            force_type=self._current_force_type,
            frame_ids=frame_ids,
        )

        if len(positions) == 0:
            return

        # Create point cloud for labels
        point_cloud = pv.PolyData(positions)

        # Add point labels
        actor = self._plotter.add_point_labels(
            point_cloud,
            labels,
            font_size=10,
            text_color="black",
            font_family="arial",
            bold=False,
            show_points=False,
            always_visible=True,
            name="force_labels",
        )
        self._label_actors.append(actor)

    def _render_frame_highlight(self) -> None:
        """Render highlight for selected frame."""
        if self._model is None or self._highlighted_frame_id is None:
            return

        try:
            frame = self._model.get_frame(self._highlighted_frame_id)
        except Exception:
            return

        node_i = self._model.get_node(frame.node_i_id)
        node_j = self._model.get_node(frame.node_j_id)

        # Create highlighted line
        points = np.array([
            [node_i.x, node_i.y, node_i.z],
            [node_j.x, node_j.y, node_j.z],
        ], dtype=np.float64)

        import pyvista as pv
        mesh = pv.PolyData(points)
        mesh.lines = np.array([2, 0, 1], dtype=np.int64)  # type: ignore[assignment]

        actor = self._plotter.add_mesh(
            mesh,
            color="yellow",
            line_width=self._settings.line_width * 3,
            render_lines_as_tubes=True,
            name="highlighted_frame",
        )
        self._highlight_actors.append(actor)

    def closeEvent(self, event: object) -> None:
        """Clean up plotter on close."""
        self._plotter.close()
        super().closeEvent(event)  # type: ignore[arg-type]

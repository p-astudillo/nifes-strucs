"""
Analysis service for running structural analysis.

Orchestrates the analysis workflow:
1. Validate model
2. Build engine model
3. Apply loads
4. Run analysis
5. Return results
6. Enrich results with analytical diagrams
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field

from paz.domain.loads import DistributedLoad, LoadCase, NodalLoad, PointLoadOnFrame
from paz.domain.materials import Material
from paz.domain.model import StructuralModel
from paz.domain.results import AnalysisResults, FrameForces, FrameResult, create_failed_result
from paz.domain.sections import Section
from paz.domain.validation import ValidationResult, validate_model_for_analysis
from paz.infrastructure.engines import AnalysisEngine, OpenSeesAdapter


def _compute_frame_length(model: StructuralModel, frame_id: int) -> float:
    """Compute length of a frame element."""
    frame = model.get_frame(frame_id)
    if frame is None:
        return 0.0
    node_i = model.get_node(frame.node_i_id)
    node_j = model.get_node(frame.node_j_id)
    if node_i is None or node_j is None:
        return 0.0
    dx = node_j.x - node_i.x
    dy = node_j.y - node_i.y
    dz = node_j.z - node_i.z
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _enrich_frame_results_with_diagrams(
    results: AnalysisResults,
    model: StructuralModel,
    distributed_loads: list[DistributedLoad],
    point_loads: list[PointLoadOnFrame],
    num_points: int = 21,
) -> None:
    """
    Enrich frame results with intermediate points computed from endpoint values.

    Uses the fundamental relationship: dM/dx = V
    - If V is constant (no distributed load): M varies linearly
    - If V varies linearly (uniform distributed load): M varies parabolically

    This derives the diagram shape purely from OpenSees endpoint values,
    without needing to know the actual loads.

    This modifies results in place.
    """
    # Process each frame result
    new_frame_results: dict[int, FrameResult] = {}

    for frame_id, fr in results.frame_results.items():
        if len(fr.forces) < 2:
            new_frame_results[frame_id] = fr
            continue

        # Get endpoint forces from OpenSees
        forces_i = fr.forces[0]  # location = 0
        forces_j = fr.forces[-1]  # location = 1

        # Get frame length
        L = _compute_frame_length(model, frame_id)
        if L < 1e-10:
            new_frame_results[frame_id] = fr
            continue

        # Generate intermediate points using integration of shear to get moment
        # Fundamental relationship: dM/dx = V
        #
        # If shear varies linearly: V(x) = V_i + (V_j - V_i) * x / L
        # Then moment: M(x) = M_i + integral_0^x V(s) ds
        #            = M_i + V_i * x + (V_j - V_i) * x² / (2L)
        #
        # In normalized coordinates (t = x/L):
        # M(t) = M_i + V_i * L * t + (V_j - V_i) * L * t² / 2

        new_forces: list[FrameForces] = []

        for i in range(num_points):
            t = i / (num_points - 1)  # 0 to 1
            x = t * L  # Actual distance along frame

            # Axial and torsion: always linear interpolation
            P = forces_i.P + t * (forces_j.P - forces_i.P)
            T = forces_i.T + t * (forces_j.T - forces_i.T)

            # Shear: linear interpolation (exact for uniform distributed loads)
            V2 = forces_i.V2 + t * (forces_j.V2 - forces_i.V2)
            V3 = forces_i.V3 + t * (forces_j.V3 - forces_i.V3)

            # Moment: derived from integration of shear
            # M(x) = M_i + V_i * x + (V_j - V_i) * x² / (2L)
            # Using x = t*L:
            # M(t) = M_i + V_i * t * L + (V_j - V_i) * t² * L / 2
            dV2 = forces_j.V2 - forces_i.V2
            dV3 = forces_j.V3 - forces_i.V3

            # M3 is affected by V2, M2 is affected by V3
            M3 = forces_i.M3 + forces_i.V2 * x + dV2 * x * t / 2
            M2 = forces_i.M2 + forces_i.V3 * x + dV3 * x * t / 2

            new_forces.append(FrameForces(
                location=t,
                P=P,
                V2=V2,
                V3=V3,
                T=T,
                M2=M2,
                M3=M3,
            ))

        new_frame_results[frame_id] = FrameResult(
            frame_id=frame_id,
            forces=new_forces,
        )

    # Update results
    results.frame_results = new_frame_results


# Progress callback type: (step, total, message)
ProgressCallback = Callable[[int, int, str], None]


@dataclass
class AnalysisService:
    """
    Service for running structural analysis.

    Handles model validation, engine setup, and result extraction.
    """

    # Analysis engine (defaults to OpenSees)
    engine: AnalysisEngine = field(default_factory=OpenSeesAdapter)

    # Whether to skip validation (for testing only)
    skip_validation: bool = False

    def analyze(
        self,
        model: StructuralModel,
        materials: dict[str, Material],
        sections: dict[str, Section],
        load_case: LoadCase,
        nodal_loads: list[NodalLoad] | None = None,
        distributed_loads: list[DistributedLoad] | None = None,
        point_loads: list[PointLoadOnFrame] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> AnalysisResults:
        """
        Run structural analysis on a model.

        Args:
            model: The structural model to analyze
            materials: Available materials by name
            sections: Available sections by name
            load_case: The load case to analyze
            nodal_loads: Nodal loads for this case
            distributed_loads: Distributed loads for this case
            point_loads: Point loads on frames for this case
            progress_callback: Optional callback for progress updates

        Returns:
            AnalysisResults with displacements, reactions, and frame forces
        """
        nodal_loads = nodal_loads or []
        distributed_loads = distributed_loads or []
        point_loads = point_loads or []

        # Step 1: Validate model
        if progress_callback:
            progress_callback(1, 5, "Validating model...")

        if not self.skip_validation:
            validation = self.validate_model(model, materials, sections)
            if not validation.is_valid:
                error_msg = "; ".join(validation.errors)
                return create_failed_result(load_case.id, f"Validation failed: {error_msg}")

        # Step 2: Build engine model
        if progress_callback:
            progress_callback(2, 5, "Building analysis model...")

        try:
            self.engine.clear()
            self.engine.build_model(model, materials, sections)
        except Exception as e:
            return create_failed_result(load_case.id, f"Failed to build model: {e}")

        # Step 3: Apply loads
        if progress_callback:
            progress_callback(3, 5, "Applying loads...")

        try:
            self.engine.apply_loads(load_case, nodal_loads, distributed_loads, point_loads)
        except Exception as e:
            return create_failed_result(load_case.id, f"Failed to apply loads: {e}")

        # Step 4: Run analysis
        if progress_callback:
            progress_callback(4, 5, "Running analysis...")

        try:
            success = self.engine.run_analysis()
        except Exception as e:
            return create_failed_result(load_case.id, f"Analysis failed: {e}")

        # Step 5: Get results
        if progress_callback:
            progress_callback(5, 5, "Extracting results...")

        try:
            results = self.engine.get_results(load_case)
            results.success = success
            if not success:
                results.error_message = "Analysis did not converge"
        except Exception as e:
            return create_failed_result(load_case.id, f"Failed to extract results: {e}")

        # Step 6: Enrich frame results with analytical diagrams
        if results.success:
            try:
                _enrich_frame_results_with_diagrams(
                    results=results,
                    model=model,
                    distributed_loads=distributed_loads,
                    point_loads=point_loads,
                )
            except Exception:
                # If enrichment fails, keep the original results
                pass

        return results

    def validate_model(
        self,
        model: StructuralModel,
        materials: dict[str, Material],
        sections: dict[str, Section],
    ) -> ValidationResult:
        """
        Validate a model for analysis.

        Args:
            model: The structural model
            materials: Available materials
            sections: Available sections

        Returns:
            ValidationResult with errors and warnings
        """
        return validate_model_for_analysis(model, materials, sections)

    def analyze_multiple_cases(
        self,
        model: StructuralModel,
        materials: dict[str, Material],
        sections: dict[str, Section],
        load_cases: list[tuple[LoadCase, list[NodalLoad], list[DistributedLoad]]],
        progress_callback: ProgressCallback | None = None,
    ) -> list[AnalysisResults]:
        """
        Analyze multiple load cases.

        Args:
            model: The structural model
            materials: Available materials
            sections: Available sections
            load_cases: List of (load_case, nodal_loads, distributed_loads) tuples
            progress_callback: Optional callback for progress

        Returns:
            List of AnalysisResults, one per load case
        """
        results: list[AnalysisResults] = []
        total_cases = len(load_cases)

        for i, (load_case, nodal_loads, distributed_loads) in enumerate(load_cases):
            if progress_callback:
                progress_callback(i + 1, total_cases, f"Analyzing {load_case.name}...")

            result = self.analyze(
                model=model,
                materials=materials,
                sections=sections,
                load_case=load_case,
                nodal_loads=nodal_loads,
                distributed_loads=distributed_loads,
            )
            results.append(result)

        return results

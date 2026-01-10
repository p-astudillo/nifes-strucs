"""
Analysis service for running structural analysis.

Orchestrates the analysis workflow:
1. Validate model
2. Build engine model
3. Apply loads
4. Run analysis
5. Return results
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from paz.domain.loads import DistributedLoad, LoadCase, NodalLoad
from paz.domain.materials import Material
from paz.domain.model import StructuralModel
from paz.domain.results import AnalysisResults, create_failed_result
from paz.domain.sections import Section
from paz.domain.validation import ValidationResult, validate_model_for_analysis
from paz.infrastructure.engines import AnalysisEngine, OpenSeesAdapter


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
            progress_callback: Optional callback for progress updates

        Returns:
            AnalysisResults with displacements, reactions, and frame forces
        """
        nodal_loads = nodal_loads or []
        distributed_loads = distributed_loads or []

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
            self.engine.apply_loads(load_case, nodal_loads, distributed_loads)
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

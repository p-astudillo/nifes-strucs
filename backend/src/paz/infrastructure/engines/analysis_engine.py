"""
Abstract interface for structural analysis engines.

Defines the contract that all analysis engines must implement,
allowing for interchangeable engines (OpenSees, Kratos, etc.).
"""

from abc import ABC, abstractmethod
from collections.abc import Callable

from paz.domain.loads import DistributedLoad, LoadCase, NodalLoad, PointLoadOnFrame
from paz.domain.materials import Material
from paz.domain.model import StructuralModel
from paz.domain.results import AnalysisResults
from paz.domain.sections import Section


# Progress callback type: receives (current_step, total_steps, message)
ProgressCallback = Callable[[int, int, str], None]


class AnalysisEngine(ABC):
    """
    Abstract base class for structural analysis engines.

    Implementations must provide methods to:
    - Build the analysis model from domain objects
    - Apply loads
    - Run analysis
    - Extract results
    """

    @abstractmethod
    def build_model(
        self,
        model: StructuralModel,
        materials: dict[str, Material],
        sections: dict[str, Section],
    ) -> None:
        """
        Build the analysis model from structural model data.

        Args:
            model: The structural model with nodes and frames
            materials: Dictionary of materials by name
            sections: Dictionary of sections by name
        """
        ...

    @abstractmethod
    def apply_loads(
        self,
        load_case: LoadCase,
        nodal_loads: list[NodalLoad],
        distributed_loads: list[DistributedLoad],
        point_loads: list[PointLoadOnFrame] | None = None,
    ) -> None:
        """
        Apply loads to the analysis model.

        Args:
            load_case: The load case being analyzed
            nodal_loads: List of nodal loads for this case
            distributed_loads: List of distributed loads for this case
            point_loads: List of point loads on frames for this case
        """
        ...

    @abstractmethod
    def run_analysis(
        self,
        progress_callback: ProgressCallback | None = None,
    ) -> bool:
        """
        Run the structural analysis.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            True if analysis converged successfully, False otherwise
        """
        ...

    @abstractmethod
    def get_results(self, load_case: LoadCase) -> AnalysisResults:
        """
        Extract analysis results.

        Args:
            load_case: The load case these results are for

        Returns:
            AnalysisResults containing displacements, reactions, and frame forces
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear the analysis model and reset state."""
        ...

    def analyze(
        self,
        model: StructuralModel,
        materials: dict[str, Material],
        sections: dict[str, Section],
        load_case: LoadCase,
        nodal_loads: list[NodalLoad],
        distributed_loads: list[DistributedLoad],
        point_loads: list[PointLoadOnFrame] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> AnalysisResults:
        """
        Convenience method to perform full analysis workflow.

        Args:
            model: The structural model
            materials: Dictionary of materials by name
            sections: Dictionary of sections by name
            load_case: The load case to analyze
            nodal_loads: Nodal loads for this case
            distributed_loads: Distributed loads for this case
            point_loads: Point loads on frames for this case
            progress_callback: Optional progress callback

        Returns:
            AnalysisResults with all output data
        """
        self.clear()
        self.build_model(model, materials, sections)
        self.apply_loads(load_case, nodal_loads, distributed_loads, point_loads)

        success = self.run_analysis(progress_callback)

        results = self.get_results(load_case)
        results.success = success

        return results

"""
OpenSees adapter for structural analysis.

Uses the OpenSees binary (not openseespy) to perform static linear analysis.
This approach works natively on all platforms including Mac ARM.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from paz.domain.loads import DistributedLoad, LoadCase, NodalLoad
from paz.domain.materials import Material
from paz.domain.model import StructuralModel
from paz.domain.results import AnalysisResults
from paz.domain.sections import Section
from paz.infrastructure.engines.analysis_engine import AnalysisEngine, ProgressCallback
from paz.infrastructure.engines.results_parser import ResultsParser
from paz.infrastructure.engines.tcl_writer import TclWriter


def _find_opensees_executable() -> str:
    """
    Find the OpenSees executable.

    Checks:
    1. OPENSEES_EXE environment variable
    2. 'OpenSees' in PATH
    3. Common installation locations

    Returns:
        Path to OpenSees executable

    Raises:
        RuntimeError: If OpenSees is not found
    """
    # Check environment variable
    exe = os.environ.get("OPENSEES_EXE")
    if exe and (Path(exe).exists() or shutil.which(exe)):
        return exe

    # Check PATH
    if shutil.which("OpenSees"):
        return "OpenSees"

    # Check common locations
    common_paths = [
        "/usr/local/bin/OpenSees",
        "/opt/homebrew/bin/OpenSees",
        Path.home() / "OpenSees" / "bin" / "OpenSees",
    ]

    for path in common_paths:
        path_obj = Path(path) if isinstance(path, str) else path
        if path_obj.exists():
            return str(path_obj)

    raise RuntimeError(
        "OpenSees executable not found. "
        "Set OPENSEES_EXE environment variable or add OpenSees to PATH."
    )


@dataclass
class OpenSeesAdapter(AnalysisEngine):
    """
    OpenSees implementation using the binary executable.

    Generates TCL scripts, executes OpenSees binary, and parses results.
    All units are SI: meters, kN, kPa.
    """

    # Working directory for TCL files and results
    work_dir: Path | None = field(default=None, repr=False)
    _temp_dir: tempfile.TemporaryDirectory[str] | None = field(
        default=None, repr=False
    )

    # Internal state
    _model_built: bool = field(default=False, repr=False)
    _tcl_path: Path | None = field(default=None, repr=False)
    _start_time: float = field(default=0.0, repr=False)
    _stdout: str = field(default="", repr=False)
    _stderr: str = field(default="", repr=False)
    _analysis_complete: bool = field(default=False, repr=False)

    # Stored model data for result extraction
    _model: StructuralModel | None = field(default=None, repr=False)
    _load_case: LoadCase | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize working directory."""
        if self.work_dir is None:
            self._temp_dir = tempfile.TemporaryDirectory(prefix="paz_opensees_")
            self.work_dir = Path(self._temp_dir.name)

    def _get_work_dir(self) -> Path:
        """Get working directory, creating if needed."""
        if self.work_dir is None:
            self._temp_dir = tempfile.TemporaryDirectory(prefix="paz_opensees_")
            self.work_dir = Path(self._temp_dir.name)
        return self.work_dir

    def build_model(
        self,
        model: StructuralModel,
        materials: dict[str, Material],
        sections: dict[str, Section],
    ) -> None:
        """
        Build the model by storing references.

        The actual TCL file is written in apply_loads() when we have all data.
        """
        self._start_time = time.time()
        self._model = model
        self._materials = materials
        self._sections = sections
        self._model_built = True

    def apply_loads(
        self,
        load_case: LoadCase,
        nodal_loads: list[NodalLoad],
        distributed_loads: list[DistributedLoad],
    ) -> None:
        """
        Apply loads and write the complete TCL file.

        Args:
            load_case: Load case being analyzed
            nodal_loads: Nodal loads for this case
            distributed_loads: Distributed loads for this case
        """
        if not self._model_built or self._model is None:
            raise RuntimeError("Model must be built before applying loads")

        self._load_case = load_case

        # Write TCL file
        work_dir = self._get_work_dir()
        writer = TclWriter(work_dir)

        self._tcl_path = writer.write_model(
            model=self._model,
            materials=self._materials,
            sections=self._sections,
            load_case=load_case,
            nodal_loads=nodal_loads,
            distributed_loads=distributed_loads,
        )

    def run_analysis(
        self,
        progress_callback: ProgressCallback | None = None,
    ) -> bool:
        """
        Run the OpenSees binary.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            True if analysis converged successfully
        """
        if self._tcl_path is None:
            raise RuntimeError("Loads must be applied before running analysis")

        if progress_callback:
            progress_callback(1, 3, "Finding OpenSees executable...")

        try:
            exe = _find_opensees_executable()
        except RuntimeError as e:
            self._stderr = str(e)
            self._analysis_complete = False
            return False

        if progress_callback:
            progress_callback(2, 3, "Running OpenSees analysis...")

        # Execute OpenSees
        cmd = [exe, str(self._tcl_path)]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            self._stdout = proc.stdout or ""
            self._stderr = proc.stderr or ""

            # Save output for debugging
            work_dir = self._get_work_dir()
            (work_dir / "opensees_stdout.txt").write_text(self._stdout)
            (work_dir / "opensees_stderr.txt").write_text(self._stderr)

            if proc.returncode != 0:
                self._analysis_complete = False
                return False

        except subprocess.TimeoutExpired:
            self._stderr = "Analysis timed out after 5 minutes"
            self._analysis_complete = False
            return False
        except FileNotFoundError:
            self._stderr = f"OpenSees executable not found: {exe}"
            self._analysis_complete = False
            return False

        if progress_callback:
            progress_callback(3, 3, "Analysis complete")

        # Check if analysis succeeded
        parser = ResultsParser(self._get_work_dir())
        self._analysis_complete = parser.check_analysis_success(self._stdout)

        return self._analysis_complete

    def get_results(self, load_case: LoadCase) -> AnalysisResults:
        """
        Parse and return analysis results.

        Args:
            load_case: Load case these results are for

        Returns:
            AnalysisResults with displacements, reactions, and frame forces
        """
        elapsed = time.time() - self._start_time

        results = AnalysisResults(
            load_case_id=load_case.id,
            success=self._analysis_complete,
            analysis_time_seconds=elapsed,
        )

        if not self._analysis_complete:
            results.error_message = self._stderr or "Analysis did not converge"
            return results

        # Parse results files
        parser = ResultsParser(self._get_work_dir())

        # Displacements
        for _node_id, disp in parser.parse_displacements().items():
            results.add_displacement(disp)

        # Reactions
        for _node_id, reaction in parser.parse_reactions().items():
            results.add_reaction(reaction)

        # Frame forces
        for _frame_id, frame_result in parser.parse_element_forces().items():
            results.add_frame_result(frame_result)

        return results

    def clear(self) -> None:
        """Clear the adapter state."""
        self._model_built = False
        self._tcl_path = None
        self._stdout = ""
        self._stderr = ""
        self._analysis_complete = False
        self._model = None
        self._load_case = None

        # Clean up temp directory if we created one
        if self._temp_dir is not None:
            import contextlib

            with contextlib.suppress(Exception):
                self._temp_dir.cleanup()
            self._temp_dir = None
            self.work_dir = None

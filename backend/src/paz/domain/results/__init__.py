"""Analysis results from structural analysis."""

from paz.domain.results.analysis_results import (
    AnalysisResults,
    create_failed_result,
)
from paz.domain.results.frame_results import FrameForces, FrameResult
from paz.domain.results.nodal_results import NodalDisplacement, NodalReaction


__all__ = [
    "AnalysisResults",
    "FrameForces",
    "FrameResult",
    "NodalDisplacement",
    "NodalReaction",
    "create_failed_result",
]

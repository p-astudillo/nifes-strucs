"""
Analysis results container.

Holds all results from a structural analysis for a specific load case.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from paz.domain.results.frame_results import FrameResult
from paz.domain.results.nodal_results import NodalDisplacement, NodalReaction


@dataclass
class AnalysisResults:
    """
    Complete results from a structural analysis.

    Contains nodal displacements, reactions, and frame forces
    for a specific load case or combination.
    """

    load_case_id: UUID
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: str = ""

    # Nodal results
    displacements: dict[int, NodalDisplacement] = field(default_factory=dict)
    reactions: dict[int, NodalReaction] = field(default_factory=dict)

    # Frame results
    frame_results: dict[int, FrameResult] = field(default_factory=dict)

    # Analysis metadata
    analysis_time_seconds: float = 0.0
    iterations: int = 0

    def get_displacement(self, node_id: int) -> NodalDisplacement | None:
        """Get displacement for a specific node."""
        return self.displacements.get(node_id)

    def get_reaction(self, node_id: int) -> NodalReaction | None:
        """Get reaction for a specific node."""
        return self.reactions.get(node_id)

    def get_frame_result(self, frame_id: int) -> FrameResult | None:
        """Get results for a specific frame."""
        return self.frame_results.get(frame_id)

    @property
    def max_displacement(self) -> float:
        """Maximum translational displacement magnitude across all nodes."""
        if not self.displacements:
            return 0.0
        return max(d.translation_magnitude for d in self.displacements.values())

    @property
    def max_rotation(self) -> float:
        """Maximum rotational displacement magnitude across all nodes."""
        if not self.displacements:
            return 0.0
        return max(d.rotation_magnitude for d in self.displacements.values())

    def add_displacement(self, disp: NodalDisplacement) -> None:
        """Add a nodal displacement result."""
        self.displacements[disp.node_id] = disp

    def add_reaction(self, reaction: NodalReaction) -> None:
        """Add a nodal reaction result."""
        self.reactions[reaction.node_id] = reaction

    def add_frame_result(self, result: FrameResult) -> None:
        """Add a frame result."""
        self.frame_results[result.frame_id] = result

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "load_case_id": str(self.load_case_id),
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_message": self.error_message,
            "displacements": {
                str(k): v.to_dict() for k, v in self.displacements.items()
            },
            "reactions": {str(k): v.to_dict() for k, v in self.reactions.items()},
            "frame_results": {
                str(k): v.to_dict() for k, v in self.frame_results.items()
            },
            "analysis_time_seconds": self.analysis_time_seconds,
            "iterations": self.iterations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisResults":
        """Create from dictionary."""
        displacements = {
            int(k): NodalDisplacement.from_dict(v)
            for k, v in data.get("displacements", {}).items()
        }
        reactions = {
            int(k): NodalReaction.from_dict(v)
            for k, v in data.get("reactions", {}).items()
        }
        frame_results = {
            int(k): FrameResult.from_dict(v)
            for k, v in data.get("frame_results", {}).items()
        }

        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            load_case_id=UUID(data["load_case_id"]),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.now(),
            success=data.get("success", True),
            error_message=data.get("error_message", ""),
            displacements=displacements,
            reactions=reactions,
            frame_results=frame_results,
            analysis_time_seconds=data.get("analysis_time_seconds", 0.0),
            iterations=data.get("iterations", 0),
        )


def create_failed_result(load_case_id: UUID, error: str) -> AnalysisResults:
    """Create a failed analysis result with error message."""
    return AnalysisResults(
        load_case_id=load_case_id,
        success=False,
        error_message=error,
    )

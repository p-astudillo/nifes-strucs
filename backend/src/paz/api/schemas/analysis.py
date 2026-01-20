"""
Analysis schemas for API.
"""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class LoadCaseSchema(BaseModel):
    """Schema for load case."""

    name: str = Field(default="Dead", description="Load case name")
    load_type: str = Field(default="Dead", description="Type: Dead, Live, Wind, etc.")
    self_weight_multiplier: float = Field(default=1.0, description="Self-weight factor")


class NodalLoadSchema(BaseModel):
    """Schema for nodal load."""

    node_id: int
    Fx: float = Field(default=0.0, description="Force X (kN)")
    Fy: float = Field(default=0.0, description="Force Y (kN)")
    Fz: float = Field(default=0.0, description="Force Z (kN)")
    Mx: float = Field(default=0.0, description="Moment X (kN-m)")
    My: float = Field(default=0.0, description="Moment Y (kN-m)")
    Mz: float = Field(default=0.0, description="Moment Z (kN-m)")


class LoadDirectionEnum(str, Enum):
    """Load direction for distributed/point loads."""

    GRAVITY = "Gravity"
    LOCAL_X = "Local X"
    LOCAL_Y = "Local Y"
    LOCAL_Z = "Local Z"
    GLOBAL_X = "Global X"
    GLOBAL_Y = "Global Y"
    GLOBAL_Z = "Global Z"


class DistributedLoadSchema(BaseModel):
    """Schema for distributed load on frame."""

    frame_id: int = Field(..., description="ID of the frame element")
    direction: LoadDirectionEnum = Field(
        default=LoadDirectionEnum.GRAVITY, description="Load direction"
    )
    w_start: float = Field(..., description="Load intensity at start (kN/m)")
    w_end: float | None = Field(
        default=None,
        description="Load intensity at end (kN/m). If None, uniform load.",
    )
    start_loc: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Start location (0-1)"
    )
    end_loc: float = Field(
        default=1.0, ge=0.0, le=1.0, description="End location (0-1)"
    )


class PointLoadOnFrameSchema(BaseModel):
    """Schema for point load on frame."""

    frame_id: int = Field(..., description="ID of the frame element")
    location: float = Field(
        ..., ge=0.0, le=1.0, description="Location as fraction of length (0-1)"
    )
    P: float = Field(..., description="Force magnitude (kN)")
    direction: LoadDirectionEnum = Field(
        default=LoadDirectionEnum.GRAVITY, description="Load direction"
    )
    M: float = Field(default=0.0, description="Optional moment (kN-m)")


class AnalysisRequest(BaseModel):
    """Schema for analysis request."""

    load_case: LoadCaseSchema = Field(default_factory=LoadCaseSchema)
    nodal_loads: list[NodalLoadSchema] = Field(default_factory=list)
    distributed_loads: list[DistributedLoadSchema] = Field(default_factory=list)
    point_loads: list[PointLoadOnFrameSchema] = Field(default_factory=list)


class DisplacementResult(BaseModel):
    """Displacement result for a node."""

    node_id: int
    Ux: float
    Uy: float
    Uz: float
    Rx: float
    Ry: float
    Rz: float


class ReactionResult(BaseModel):
    """Reaction result for a node."""

    node_id: int
    Fx: float
    Fy: float
    Fz: float
    Mx: float
    My: float
    Mz: float


class FrameForceResult(BaseModel):
    """Frame forces at a location."""

    location: float  # 0 to 1
    P: float
    V2: float
    V3: float
    T: float
    M2: float
    M3: float


class FrameResultSchema(BaseModel):
    """Result for a single frame."""

    frame_id: int
    forces: list[FrameForceResult]
    P_max: float
    P_min: float
    V2_max: float
    V3_max: float
    M2_max: float
    M3_max: float
    V_max: float  # Max of V2 and V3
    M_max: float  # Max of M2 and M3


class AnalysisResponse(BaseModel):
    """Schema for analysis response."""

    success: bool
    error_message: str | None = None
    load_case_id: UUID
    load_case_name: str
    displacements: list[DisplacementResult] = Field(default_factory=list)
    reactions: list[ReactionResult] = Field(default_factory=list)
    frame_results: list[FrameResultSchema] = Field(default_factory=list)
    max_displacement: float = 0.0

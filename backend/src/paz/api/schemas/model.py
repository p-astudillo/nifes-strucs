"""
Model schemas for API (nodes, frames).
"""

from enum import Enum

from pydantic import BaseModel, Field


class RestraintTypeEnum(str, Enum):
    """Predefined restraint types for API."""

    FREE = "free"
    FIXED = "fixed"
    PINNED = "pinned"
    ROLLER_X = "roller_x"
    ROLLER_Y = "roller_y"
    ROLLER_Z = "roller_z"
    VERTICAL_ONLY = "vertical_only"
    CUSTOM = "custom"


class RestraintSchema(BaseModel):
    """Schema for node restraints."""

    ux: bool = False
    uy: bool = False
    uz: bool = False
    rx: bool = False
    ry: bool = False
    rz: bool = False
    restraint_type: RestraintTypeEnum | None = None


class NodeCreate(BaseModel):
    """Schema for creating a node."""

    x: float = Field(..., description="X coordinate (m)")
    y: float = Field(..., description="Y coordinate (m)")
    z: float = Field(default=0.0, description="Z coordinate (m)")
    restraint: RestraintSchema = Field(default_factory=RestraintSchema)
    restraint_type: RestraintTypeEnum | None = Field(
        default=None,
        description="Predefined restraint type. If provided, overrides individual DOF settings.",
    )


class NodeUpdate(BaseModel):
    """Schema for updating a node."""

    x: float | None = None
    y: float | None = None
    z: float | None = None
    restraint: RestraintSchema | None = None
    restraint_type: RestraintTypeEnum | None = Field(
        default=None,
        description="Predefined restraint type. If provided, overrides individual DOF settings.",
    )


class NodeResponse(BaseModel):
    """Schema for node response."""

    id: int
    x: float
    y: float
    z: float
    restraint: RestraintSchema
    restraint_type: RestraintTypeEnum
    is_supported: bool

    model_config = {"from_attributes": True}


class FrameReleasesSchema(BaseModel):
    """Schema for frame end releases."""

    # End i
    P_i: bool = False
    V2_i: bool = False
    V3_i: bool = False
    T_i: bool = False
    M2_i: bool = False
    M3_i: bool = False
    # End j
    P_j: bool = False
    V2_j: bool = False
    V3_j: bool = False
    T_j: bool = False
    M2_j: bool = False
    M3_j: bool = False


class FrameCreate(BaseModel):
    """Schema for creating a frame."""

    node_i_id: int = Field(..., description="Start node ID")
    node_j_id: int = Field(..., description="End node ID")
    material_name: str = Field(default="A36")
    section_name: str = Field(default="W14X22")
    rotation: float = Field(default=0.0, description="Rotation in radians")
    releases: FrameReleasesSchema = Field(default_factory=FrameReleasesSchema)
    label: str = Field(default="")


class FrameUpdate(BaseModel):
    """Schema for updating a frame."""

    material_name: str | None = None
    section_name: str | None = None
    rotation: float | None = None
    releases: FrameReleasesSchema | None = None
    label: str | None = None


class FrameResponse(BaseModel):
    """Schema for frame response."""

    id: int
    node_i_id: int
    node_j_id: int
    material_name: str
    section_name: str
    rotation: float
    releases: FrameReleasesSchema
    label: str

    model_config = {"from_attributes": True}


# --- Shell Schemas ---


class ShellTypeEnum(str, Enum):
    """Shell element formulation types for API."""

    PLATE = "plate"
    MEMBRANE = "membrane"
    SHELL = "shell"


class ShellCreate(BaseModel):
    """Schema for creating a shell."""

    node_ids: list[int] = Field(
        ...,
        min_length=3,
        max_length=4,
        description="List of 3 or 4 node IDs defining the shell corners",
    )
    material_name: str = Field(default="H25", description="Material name")
    thickness: float = Field(..., gt=0, description="Shell thickness in meters")
    shell_type: ShellTypeEnum = Field(
        default=ShellTypeEnum.SHELL, description="Shell formulation type"
    )
    label: str = Field(default="", description="Optional user label")


class ShellUpdate(BaseModel):
    """Schema for updating a shell."""

    material_name: str | None = None
    thickness: float | None = Field(default=None, gt=0)
    shell_type: ShellTypeEnum | None = None
    label: str | None = None


class ShellResponse(BaseModel):
    """Schema for shell response."""

    id: int
    node_ids: list[int]
    material_name: str
    thickness: float
    shell_type: ShellTypeEnum
    label: str

    model_config = {"from_attributes": True}


# --- Group Schemas ---


class GroupCreate(BaseModel):
    """Schema for creating an element group."""

    name: str = Field(..., min_length=1, description="Group name")
    node_ids: list[int] = Field(default_factory=list, description="Node IDs to include")
    frame_ids: list[int] = Field(default_factory=list, description="Frame IDs to include")
    shell_ids: list[int] = Field(default_factory=list, description="Shell IDs to include")
    color: str = Field(default="#808080", description="Color for visualization (hex)")
    parent_id: int | None = Field(default=None, description="Parent group ID")
    description: str = Field(default="", description="Optional description")


class GroupUpdate(BaseModel):
    """Schema for updating a group."""

    name: str | None = Field(default=None, min_length=1)
    node_ids: list[int] | None = None
    frame_ids: list[int] | None = None
    shell_ids: list[int] | None = None
    color: str | None = None
    parent_id: int | None = ...  # Use ... to allow setting to None
    description: str | None = None


class GroupResponse(BaseModel):
    """Schema for group response."""

    id: int
    name: str
    node_ids: list[int]
    frame_ids: list[int]
    shell_ids: list[int]
    color: str
    parent_id: int | None
    description: str
    element_count: int

    model_config = {"from_attributes": True}

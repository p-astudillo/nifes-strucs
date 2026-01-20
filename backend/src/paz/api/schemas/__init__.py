"""
Pydantic schemas for API request/response models.
"""

from paz.api.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    DistributedLoadSchema,
    LoadCaseSchema,
    LoadDirectionEnum,
    NodalLoadSchema,
    PointLoadOnFrameSchema,
)
from paz.api.schemas.library import MaterialSchema, ParametricSectionCreate, SectionSchema
from paz.api.schemas.model import (
    FrameCreate,
    FrameResponse,
    FrameUpdate,
    GroupCreate,
    GroupResponse,
    GroupUpdate,
    NodeCreate,
    NodeResponse,
    NodeUpdate,
    RestraintSchema,
    ShellCreate,
    ShellResponse,
    ShellTypeEnum,
    ShellUpdate,
)
from paz.api.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)

__all__ = [
    # Project
    "ProjectCreate",
    "ProjectResponse",
    "ProjectUpdate",
    # Model - Nodes
    "NodeCreate",
    "NodeResponse",
    "NodeUpdate",
    "RestraintSchema",
    # Model - Frames
    "FrameCreate",
    "FrameResponse",
    "FrameUpdate",
    # Model - Shells
    "ShellCreate",
    "ShellResponse",
    "ShellUpdate",
    "ShellTypeEnum",
    # Model - Groups
    "GroupCreate",
    "GroupResponse",
    "GroupUpdate",
    # Analysis
    "AnalysisRequest",
    "AnalysisResponse",
    "DistributedLoadSchema",
    "LoadCaseSchema",
    "LoadDirectionEnum",
    "NodalLoadSchema",
    "PointLoadOnFrameSchema",
    # Library
    "MaterialSchema",
    "SectionSchema",
    "ParametricSectionCreate",
]

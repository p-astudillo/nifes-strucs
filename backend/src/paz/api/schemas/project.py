"""
Project schemas for API.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    node_count: int = 0
    frame_count: int = 0

    model_config = {"from_attributes": True}

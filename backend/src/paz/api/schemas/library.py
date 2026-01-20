"""
Library schemas for API (materials, sections).
"""

from pydantic import BaseModel, Field


class MaterialSchema(BaseModel):
    """Schema for material."""

    name: str
    material_type: str = Field(description="Type: Steel, Concrete, etc.")
    E: float = Field(description="Elastic modulus (kPa)")
    nu: float = Field(description="Poisson's ratio")
    rho: float = Field(description="Density (kg/m3)")
    fy: float | None = Field(default=None, description="Yield strength (kPa)")
    fu: float | None = Field(default=None, description="Ultimate strength (kPa)")

    model_config = {"from_attributes": True}


class SectionSchema(BaseModel):
    """Schema for section."""

    name: str
    shape: str = Field(description="Shape: W, HSS, Pipe, etc.")
    A: float = Field(description="Area (m2)")
    Ix: float = Field(description="Moment of inertia X (m4)")
    Iy: float = Field(description="Moment of inertia Y (m4)")
    J: float = Field(description="Torsional constant (m4)")
    d: float | None = Field(default=None, description="Depth (m)")
    bf: float | None = Field(default=None, description="Flange width (m)")
    tf: float | None = Field(default=None, description="Flange thickness (m)")
    tw: float | None = Field(default=None, description="Web thickness (m)")

    model_config = {"from_attributes": True}


class ParametricSectionCreate(BaseModel):
    """Schema for creating parametric sections."""

    name: str = Field(description="Section name")
    shape: str = Field(description="Shape type: Rectangular, Circular, IShape")
    # Rectangular params
    width: float | None = Field(default=None, description="Width (m)")
    height: float | None = Field(default=None, description="Height (m)")
    # Circular params
    radius: float | None = Field(default=None, description="Outer radius (m)")
    inner_radius: float | None = Field(default=None, description="Inner radius for hollow (m)")
    # I-Shape params
    d: float | None = Field(default=None, description="Total depth (m)")
    bf: float | None = Field(default=None, description="Flange width (m)")
    tf: float | None = Field(default=None, description="Flange thickness (m)")
    tw: float | None = Field(default=None, description="Web thickness (m)")

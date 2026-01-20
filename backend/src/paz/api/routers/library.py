"""
Library router - materials and sections.
"""

import math

from fastapi import APIRouter, HTTPException, Query

from paz.api.schemas import MaterialSchema, ParametricSectionCreate, SectionSchema
from paz.domain.sections.section import Section, SectionShape
from paz.infrastructure.repositories.materials_repository import MaterialsRepository
from paz.infrastructure.repositories.sections_repository import SectionsRepository

router = APIRouter()

# Shared repositories
_materials_repo = MaterialsRepository()
_sections_repo = SectionsRepository()


# --- Materials ---


@router.get("/materials", response_model=list[MaterialSchema])
async def list_materials():
    """List all available materials."""
    materials = _materials_repo.all()
    return [
        MaterialSchema(
            name=m.name,
            material_type=m.material_type.value,
            E=m.E,
            nu=m.nu,
            rho=m.rho,
            fy=getattr(m, "fy", None),
            fu=getattr(m, "fu", None),
        )
        for m in materials
    ]


@router.get("/materials/{name}", response_model=MaterialSchema)
async def get_material(name: str):
    """Get a material by name."""
    material = _materials_repo.get(name)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    return MaterialSchema(
        name=material.name,
        material_type=material.material_type.value,
        E=material.E,
        nu=material.nu,
        rho=material.rho,
        fy=getattr(material, "fy", None),
        fu=getattr(material, "fu", None),
    )


# --- Sections ---


@router.get("/sections", response_model=list[SectionSchema])
async def list_sections(
    shape: str | None = Query(default=None, description="Filter by shape (W, HSS, etc.)"),
    limit: int = Query(default=100, le=500),
):
    """List available sections."""
    sections = _sections_repo.all()

    if shape:
        sections = [s for s in sections if s.shape.value.upper() == shape.upper()]

    sections = sections[:limit]

    return [
        SectionSchema(
            name=s.name,
            shape=s.shape.value,
            A=s.A,
            Ix=s.Ix,
            Iy=s.Iy,
            J=s.J,
            d=getattr(s, "d", None),
            bf=getattr(s, "bf", None),
            tf=getattr(s, "tf", None),
            tw=getattr(s, "tw", None),
        )
        for s in sections
    ]


@router.get("/sections/{name}", response_model=SectionSchema)
async def get_section(name: str):
    """Get a section by name."""
    section = _sections_repo.get(name)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    return SectionSchema(
        name=section.name,
        shape=section.shape.value,
        A=section.A,
        Ix=section.Ix,
        Iy=section.Iy,
        J=section.J,
        d=getattr(section, "d", None),
        bf=getattr(section, "bf", None),
        tf=getattr(section, "tf", None),
        tw=getattr(section, "tw", None),
    )


@router.get("/sections/shapes", response_model=list[str])
async def list_shapes():
    """List available section shapes."""
    sections = _sections_repo.all()
    shapes = set(s.shape.value for s in sections)
    return sorted(shapes)


@router.post("/sections/parametric", response_model=SectionSchema, status_code=201)
async def create_parametric_section(data: ParametricSectionCreate):
    """
    Create a parametric section.

    Supported shapes:
    - Rectangular: requires width, height
    - Circular: requires radius, optional inner_radius
    - IShape: requires d, bf, tf, tw
    """
    shape_lower = data.shape.lower()

    if shape_lower == "rectangular":
        if not data.width or not data.height:
            raise HTTPException(400, "Rectangular requires width and height")
        b, h = data.width, data.height
        A = b * h
        Ix = (b * h**3) / 12
        Iy = (h * b**3) / 12
        J = (b * h * (b**2 + h**2)) / 12  # Approximate
        section = Section(
            name=data.name,
            shape=SectionShape.RECTANGULAR,
            A=A,
            Ix=Ix,
            Iy=Iy,
            J=J,
            d=h,
            bf=b,
        )

    elif shape_lower == "circular":
        if not data.radius:
            raise HTTPException(400, "Circular requires radius")
        r_out = data.radius
        r_in = data.inner_radius or 0
        A = math.pi * (r_out**2 - r_in**2)
        Ix = Iy = (math.pi / 4) * (r_out**4 - r_in**4)
        J = (math.pi / 2) * (r_out**4 - r_in**4)
        section = Section(
            name=data.name,
            shape=SectionShape.CIRCULAR,
            A=A,
            Ix=Ix,
            Iy=Iy,
            J=J,
            d=2 * r_out,
            bf=2 * r_out,
        )

    elif shape_lower == "ishape":
        if not all([data.d, data.bf, data.tf, data.tw]):
            raise HTTPException(400, "IShape requires d, bf, tf, tw")
        d, bf, tf, tw = data.d, data.bf, data.tf, data.tw
        # I-shape properties
        hw = d - 2 * tf  # Web height
        A = 2 * bf * tf + hw * tw
        Ix = (bf * d**3 - (bf - tw) * hw**3) / 12
        Iy = (2 * tf * bf**3 + hw * tw**3) / 12
        # Approximate torsional constant for I-shape
        J = (2 * bf * tf**3 + hw * tw**3) / 3
        section = Section(
            name=data.name,
            shape=SectionShape.W,
            A=A,
            Ix=Ix,
            Iy=Iy,
            J=J,
            d=d,
            bf=bf,
            tf=tf,
            tw=tw,
        )

    else:
        raise HTTPException(400, f"Unsupported shape: {data.shape}. Use Rectangular, Circular, or IShape")

    # Add to repository
    _sections_repo.add_custom(section)

    return SectionSchema(
        name=section.name,
        shape=section.shape.value,
        A=section.A,
        Ix=section.Ix,
        Iy=section.Iy,
        J=section.J,
        d=getattr(section, "d", None),
        bf=getattr(section, "bf", None),
        tf=getattr(section, "tf", None),
        tw=getattr(section, "tw", None),
    )

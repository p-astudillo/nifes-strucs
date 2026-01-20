"""
Analysis router - run structural analysis.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from paz.api.routers.projects import get_model
from paz.api.schemas import AnalysisRequest, AnalysisResponse
from paz.api.schemas.analysis import (
    DisplacementResult,
    FrameForceResult,
    FrameResultSchema,
    ReactionResult,
)
from paz.application.services import AnalysisService
from paz.domain.loads import (
    DistributedLoad,
    LoadCase,
    LoadCaseType,
    LoadDirection,
    NodalLoad,
    PointLoadDirection,
    PointLoadOnFrame,
)
from paz.infrastructure.repositories.materials_repository import MaterialsRepository
from paz.infrastructure.repositories.sections_repository import SectionsRepository

router = APIRouter()


# Schema for mass response
from pydantic import BaseModel


class FrameMassResult(BaseModel):
    """Mass of a single frame."""

    frame_id: int
    mass_kg: float
    weight_kN: float


class MassResponse(BaseModel):
    """Total mass response."""

    total_mass_kg: float
    total_weight_kN: float
    frame_masses: list[FrameMassResult]

# Shared repositories
_materials_repo = MaterialsRepository()
_sections_repo = SectionsRepository()
_analysis_service = AnalysisService()


@router.post("/{project_id}/run", response_model=AnalysisResponse)
async def run_analysis(project_id: UUID, request: AnalysisRequest):
    """
    Run structural analysis on the project model.

    Returns displacements, reactions, and frame forces.
    """
    model = get_model(project_id)

    # Validate model has content
    if model.node_count < 2:
        raise HTTPException(
            status_code=400,
            detail="Model must have at least 2 nodes",
        )
    if model.frame_count < 1:
        raise HTTPException(
            status_code=400,
            detail="Model must have at least 1 frame",
        )

    # Check for supports
    has_support = any(node.is_supported for node in model.nodes)
    if not has_support:
        raise HTTPException(
            status_code=400,
            detail="Model must have at least one supported node",
        )

    # Prepare materials and sections
    materials = {m.name: m for m in _materials_repo.all()}
    sections = {s.name: s for s in _sections_repo.all()}

    # Create load case
    load_type_map = {
        "Dead": LoadCaseType.DEAD,
        "Live": LoadCaseType.LIVE,
        "Wind": LoadCaseType.WIND,
        "Seismic": LoadCaseType.SEISMIC,
    }
    load_case = LoadCase(
        name=request.load_case.name,
        load_type=load_type_map.get(request.load_case.load_type, LoadCaseType.OTHER),
        self_weight_multiplier=request.load_case.self_weight_multiplier,
    )

    # Create nodal loads
    nodal_loads = [
        NodalLoad(
            node_id=nl.node_id,
            load_case_id=load_case.id,
            Fx=nl.Fx,
            Fy=nl.Fy,
            Fz=nl.Fz,
            Mx=nl.Mx,
            My=nl.My,
            Mz=nl.Mz,
        )
        for nl in request.nodal_loads
    ]

    # Create distributed loads
    direction_map = {
        "Gravity": LoadDirection.GRAVITY,
        "Local X": LoadDirection.LOCAL_X,
        "Local Y": LoadDirection.LOCAL_Y,
        "Local Z": LoadDirection.LOCAL_Z,
        "Global X": LoadDirection.GLOBAL_X,
        "Global Y": LoadDirection.GLOBAL_Y,
        "Global Z": LoadDirection.GLOBAL_Z,
    }
    distributed_loads = [
        DistributedLoad(
            frame_id=dl.frame_id,
            load_case_id=load_case.id,
            direction=direction_map.get(dl.direction.value, LoadDirection.GRAVITY),
            w_start=dl.w_start,
            w_end=dl.w_end,
            start_loc=dl.start_loc,
            end_loc=dl.end_loc,
        )
        for dl in request.distributed_loads
    ]

    # Create point loads on frames
    point_direction_map = {
        "Gravity": PointLoadDirection.GRAVITY,
        "Local X": PointLoadDirection.LOCAL_X,
        "Local Y": PointLoadDirection.LOCAL_Y,
        "Local Z": PointLoadDirection.LOCAL_Z,
        "Global X": PointLoadDirection.GLOBAL_X,
        "Global Y": PointLoadDirection.GLOBAL_Y,
        "Global Z": PointLoadDirection.GLOBAL_Z,
    }
    point_loads = [
        PointLoadOnFrame(
            frame_id=pl.frame_id,
            load_case_id=load_case.id,
            location=pl.location,
            P=pl.P,
            direction=point_direction_map.get(pl.direction.value, PointLoadDirection.GRAVITY),
            M=pl.M,
        )
        for pl in request.point_loads
    ]

    # Run analysis
    try:
        results = _analysis_service.analyze(
            model=model,
            materials=materials,
            sections=sections,
            load_case=load_case,
            nodal_loads=nodal_loads,
            distributed_loads=distributed_loads,
            point_loads=point_loads,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {e}",
        )

    # Build response
    displacements = [
        DisplacementResult(
            node_id=node_id,
            Ux=disp.Ux,
            Uy=disp.Uy,
            Uz=disp.Uz,
            Rx=disp.Rx,
            Ry=disp.Ry,
            Rz=disp.Rz,
        )
        for node_id, disp in results.displacements.items()
    ]

    reactions = [
        ReactionResult(
            node_id=node_id,
            Fx=react.Fx,
            Fy=react.Fy,
            Fz=react.Fz,
            Mx=react.Mx,
            My=react.My,
            Mz=react.Mz,
        )
        for node_id, react in results.reactions.items()
    ]

    frame_results = []
    for frame_id, fr in results.frame_results.items():
        forces = [
            FrameForceResult(
                location=f.location,
                P=f.P,
                V2=f.V2,
                V3=f.V3,
                T=f.T,
                M2=f.M2,
                M3=f.M3,
            )
            for f in fr.forces
        ]
        frame_results.append(
            FrameResultSchema(
                frame_id=frame_id,
                forces=forces,
                P_max=fr.P_max,
                P_min=fr.P_min,
                V2_max=fr.V2_max,
                V3_max=fr.V3_max,
                M2_max=fr.M2_max,
                M3_max=fr.M3_max,
                V_max=fr.V_max,
                M_max=fr.M_max,
            )
        )

    return AnalysisResponse(
        success=results.success,
        error_message=results.error_message,
        load_case_id=load_case.id,
        load_case_name=load_case.name,
        displacements=displacements,
        reactions=reactions,
        frame_results=frame_results,
        max_displacement=results.max_displacement,
    )


@router.get("/{project_id}/mass", response_model=MassResponse)
async def get_mass(project_id: UUID):
    """
    Calculate total mass of the structural model.

    Returns mass of each frame and total mass in kg and weight in kN.
    """
    model = get_model(project_id)

    if model.frame_count < 1:
        return MassResponse(
            total_mass_kg=0.0,
            total_weight_kN=0.0,
            frame_masses=[],
        )

    # Get materials and sections
    materials = {m.name: m for m in _materials_repo.all()}
    sections = {s.name: s for s in _sections_repo.all()}

    # Get node positions for frame length calculation
    nodes_dict = {n.id: n for n in model.nodes}

    frame_masses = []
    total_mass = 0.0

    for frame in model.frames:
        # Get material and section
        material = materials.get(frame.material_name)
        section = sections.get(frame.section_name)

        if not material or not section:
            # Skip frames without valid material/section
            continue

        # Set nodes for length calculation
        node_i = nodes_dict.get(frame.node_i_id)
        node_j = nodes_dict.get(frame.node_j_id)

        if node_i and node_j:
            frame.set_nodes(node_i, node_j)
            mass_kg = frame.mass(material, section)
            weight_kN = frame.weight(material, section)

            frame_masses.append(
                FrameMassResult(
                    frame_id=frame.id,
                    mass_kg=mass_kg,
                    weight_kN=weight_kN,
                )
            )
            total_mass += mass_kg

    total_weight = total_mass * 9.81 / 1000  # Convert to kN

    return MassResponse(
        total_mass_kg=total_mass,
        total_weight_kN=total_weight,
        frame_masses=frame_masses,
    )

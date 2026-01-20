"""
Projects router - CRUD operations for structural projects.
"""

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from paz.api.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from paz.domain.model import StructuralModel
from paz.infrastructure.exporters import CSVExporter, DXFExporter

router = APIRouter()

# In-memory storage for MVP (replace with PostgreSQL later)
_projects: dict[UUID, dict] = {}
_models: dict[UUID, StructuralModel] = {}


def _get_project_response(project_id: UUID) -> ProjectResponse:
    """Build project response with model stats."""
    project = _projects[project_id]
    model = _models.get(project_id, StructuralModel())
    return ProjectResponse(
        id=project_id,
        name=project["name"],
        description=project["description"],
        created_at=project["created_at"],
        updated_at=project["updated_at"],
        node_count=model.node_count,
        frame_count=model.frame_count,
    )


@router.get("/", response_model=list[ProjectResponse])
async def list_projects():
    """List all projects."""
    return [_get_project_response(pid) for pid in _projects]


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate):
    """Create a new project."""
    project_id = uuid4()
    now = datetime.utcnow()

    _projects[project_id] = {
        "name": data.name,
        "description": data.description,
        "created_at": now,
        "updated_at": now,
    }
    _models[project_id] = StructuralModel()

    return _get_project_response(project_id)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID):
    """Get a project by ID."""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return _get_project_response(project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: UUID, data: ProjectUpdate):
    """Update a project."""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    project = _projects[project_id]

    if data.name is not None:
        project["name"] = data.name
    if data.description is not None:
        project["description"] = data.description

    project["updated_at"] = datetime.utcnow()

    return _get_project_response(project_id)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: UUID):
    """Delete a project."""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    del _projects[project_id]
    if project_id in _models:
        del _models[project_id]


def get_model(project_id: UUID) -> StructuralModel:
    """Get the structural model for a project (internal use)."""
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    if project_id not in _models:
        _models[project_id] = StructuralModel()
    return _models[project_id]


@router.get("/{project_id}/export/dxf")
async def export_project_dxf(project_id: UUID):
    """Export project model to DXF format."""
    model = get_model(project_id)
    project = _projects.get(project_id, {})

    exporter = DXFExporter(model)
    dxf_bytes = exporter.export()

    filename = f"{project.get('name', 'model')}.dxf"

    return Response(
        content=dxf_bytes,
        media_type="application/dxf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{project_id}/export/csv")
async def export_project_csv(project_id: UUID):
    """Export project model to CSV format (zip with nodes and frames)."""
    model = get_model(project_id)
    project = _projects.get(project_id, {})

    exporter = CSVExporter(model)
    nodes_csv = exporter.export_nodes()
    frames_csv = exporter.export_frames()

    # Return nodes CSV for now (could be improved to zip multiple files)
    filename = f"{project.get('name', 'model')}_nodes.csv"

    return Response(
        content=nodes_csv,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

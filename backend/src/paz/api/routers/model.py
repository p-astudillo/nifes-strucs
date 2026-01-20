"""
Model router - operations for nodes and frames.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from paz.api.routers.projects import get_model
from paz.api.schemas import (
    FrameCreate,
    FrameResponse,
    FrameUpdate,
    NodeCreate,
    NodeResponse,
    NodeUpdate,
    RestraintSchema,
    ShellCreate,
    ShellResponse,
    ShellTypeEnum,
    ShellUpdate,
)
from paz.api.schemas.model import GroupCreate, GroupResponse, GroupUpdate
from paz.api.schemas.model import FrameReleasesSchema, RestraintTypeEnum
from paz.domain.model.element_group import ElementGroup
from paz.domain.model.frame import FrameReleases
from paz.domain.model.node import Node
from paz.domain.model.restraint import Restraint, RestraintType
from paz.domain.model.shell import Shell, ShellType

router = APIRouter()


def _node_to_response(node: Node) -> NodeResponse:
    """Convert a Node domain object to NodeResponse schema."""
    restraint_type = node.restraint.get_type()
    return NodeResponse(
        id=node.id,
        x=node.x,
        y=node.y,
        z=node.z,
        restraint=RestraintSchema(
            ux=node.restraint.ux,
            uy=node.restraint.uy,
            uz=node.restraint.uz,
            rx=node.restraint.rx,
            ry=node.restraint.ry,
            rz=node.restraint.rz,
            restraint_type=RestraintTypeEnum(restraint_type.value),
        ),
        restraint_type=RestraintTypeEnum(restraint_type.value),
        is_supported=node.is_supported,
    )


# --- Nodes ---


@router.get("/{project_id}/nodes", response_model=list[NodeResponse])
async def list_nodes(project_id: UUID):
    """List all nodes in a project."""
    model = get_model(project_id)
    return [_node_to_response(node) for node in model.nodes]


@router.post("/{project_id}/nodes", response_model=NodeResponse, status_code=201)
async def create_node(project_id: UUID, data: NodeCreate):
    """Create a new node."""
    model = get_model(project_id)

    # If restraint_type is provided, use it to create the restraint
    if data.restraint_type is not None:
        restraint = Restraint.from_type(RestraintType(data.restraint_type.value))
    else:
        restraint = Restraint(
            ux=data.restraint.ux,
            uy=data.restraint.uy,
            uz=data.restraint.uz,
            rx=data.restraint.rx,
            ry=data.restraint.ry,
            rz=data.restraint.rz,
        )

    node = model.add_node(data.x, data.y, data.z, restraint=restraint)
    return _node_to_response(node)


@router.get("/{project_id}/nodes/{node_id}", response_model=NodeResponse)
async def get_node(project_id: UUID, node_id: int):
    """Get a node by ID."""
    model = get_model(project_id)

    try:
        node = model.get_node(node_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Node not found")

    return _node_to_response(node)


@router.patch("/{project_id}/nodes/{node_id}", response_model=NodeResponse)
async def update_node(project_id: UUID, node_id: int, data: NodeUpdate):
    """Update a node."""
    model = get_model(project_id)

    try:
        node = model.get_node(node_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Node not found")

    if data.x is not None or data.y is not None or data.z is not None:
        node.move_to(
            data.x if data.x is not None else node.x,
            data.y if data.y is not None else node.y,
            data.z if data.z is not None else node.z,
        )

    # If restraint_type is provided, use it to create the restraint
    if data.restraint_type is not None:
        node.restraint = Restraint.from_type(RestraintType(data.restraint_type.value))
    elif data.restraint is not None:
        node.restraint = Restraint(
            ux=data.restraint.ux,
            uy=data.restraint.uy,
            uz=data.restraint.uz,
            rx=data.restraint.rx,
            ry=data.restraint.ry,
            rz=data.restraint.rz,
        )

    return _node_to_response(node)


@router.delete("/{project_id}/nodes/{node_id}", status_code=204)
async def delete_node(project_id: UUID, node_id: int):
    """Delete a node."""
    model = get_model(project_id)

    try:
        model.remove_node(node_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Frames ---


@router.get("/{project_id}/frames", response_model=list[FrameResponse])
async def list_frames(project_id: UUID):
    """List all frames in a project."""
    model = get_model(project_id)
    return [
        FrameResponse(
            id=frame.id,
            node_i_id=frame.node_i_id,
            node_j_id=frame.node_j_id,
            material_name=frame.material_name,
            section_name=frame.section_name,
            rotation=frame.rotation,
            releases=FrameReleasesSchema(
                P_i=frame.releases.P_i,
                V2_i=frame.releases.V2_i,
                V3_i=frame.releases.V3_i,
                T_i=frame.releases.T_i,
                M2_i=frame.releases.M2_i,
                M3_i=frame.releases.M3_i,
                P_j=frame.releases.P_j,
                V2_j=frame.releases.V2_j,
                V3_j=frame.releases.V3_j,
                T_j=frame.releases.T_j,
                M2_j=frame.releases.M2_j,
                M3_j=frame.releases.M3_j,
            ),
            label=frame.label,
        )
        for frame in model.frames
    ]


@router.post("/{project_id}/frames", response_model=FrameResponse, status_code=201)
async def create_frame(project_id: UUID, data: FrameCreate):
    """Create a new frame."""
    model = get_model(project_id)

    releases = FrameReleases(
        P_i=data.releases.P_i,
        V2_i=data.releases.V2_i,
        V3_i=data.releases.V3_i,
        T_i=data.releases.T_i,
        M2_i=data.releases.M2_i,
        M3_i=data.releases.M3_i,
        P_j=data.releases.P_j,
        V2_j=data.releases.V2_j,
        V3_j=data.releases.V3_j,
        T_j=data.releases.T_j,
        M2_j=data.releases.M2_j,
        M3_j=data.releases.M3_j,
    )

    try:
        frame = model.add_frame(
            node_i_id=data.node_i_id,
            node_j_id=data.node_j_id,
            material_name=data.material_name,
            section_name=data.section_name,
            rotation=data.rotation,
            releases=releases,
            label=data.label,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return FrameResponse(
        id=frame.id,
        node_i_id=frame.node_i_id,
        node_j_id=frame.node_j_id,
        material_name=frame.material_name,
        section_name=frame.section_name,
        rotation=frame.rotation,
        releases=data.releases,
        label=frame.label,
    )


@router.get("/{project_id}/frames/{frame_id}", response_model=FrameResponse)
async def get_frame(project_id: UUID, frame_id: int):
    """Get a frame by ID."""
    model = get_model(project_id)

    try:
        frame = model.get_frame(frame_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Frame not found")

    return FrameResponse(
        id=frame.id,
        node_i_id=frame.node_i_id,
        node_j_id=frame.node_j_id,
        material_name=frame.material_name,
        section_name=frame.section_name,
        rotation=frame.rotation,
        releases=FrameReleasesSchema(
            P_i=frame.releases.P_i,
            V2_i=frame.releases.V2_i,
            V3_i=frame.releases.V3_i,
            T_i=frame.releases.T_i,
            M2_i=frame.releases.M2_i,
            M3_i=frame.releases.M3_i,
            P_j=frame.releases.P_j,
            V2_j=frame.releases.V2_j,
            V3_j=frame.releases.V3_j,
            T_j=frame.releases.T_j,
            M2_j=frame.releases.M2_j,
            M3_j=frame.releases.M3_j,
        ),
        label=frame.label,
    )


@router.patch("/{project_id}/frames/{frame_id}", response_model=FrameResponse)
async def update_frame(project_id: UUID, frame_id: int, data: FrameUpdate):
    """Update a frame."""
    model = get_model(project_id)

    try:
        frame = model.get_frame(frame_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Frame not found")

    if data.material_name is not None:
        frame.material_name = data.material_name
    if data.section_name is not None:
        frame.section_name = data.section_name
    if data.rotation is not None:
        frame.rotation = data.rotation
    if data.label is not None:
        frame.label = data.label
    if data.releases is not None:
        frame.releases = FrameReleases(
            P_i=data.releases.P_i,
            V2_i=data.releases.V2_i,
            V3_i=data.releases.V3_i,
            T_i=data.releases.T_i,
            M2_i=data.releases.M2_i,
            M3_i=data.releases.M3_i,
            P_j=data.releases.P_j,
            V2_j=data.releases.V2_j,
            V3_j=data.releases.V3_j,
            T_j=data.releases.T_j,
            M2_j=data.releases.M2_j,
            M3_j=data.releases.M3_j,
        )

    return FrameResponse(
        id=frame.id,
        node_i_id=frame.node_i_id,
        node_j_id=frame.node_j_id,
        material_name=frame.material_name,
        section_name=frame.section_name,
        rotation=frame.rotation,
        releases=FrameReleasesSchema(
            P_i=frame.releases.P_i,
            V2_i=frame.releases.V2_i,
            V3_i=frame.releases.V3_i,
            T_i=frame.releases.T_i,
            M2_i=frame.releases.M2_i,
            M3_i=frame.releases.M3_i,
            P_j=frame.releases.P_j,
            V2_j=frame.releases.V2_j,
            V3_j=frame.releases.V3_j,
            T_j=frame.releases.T_j,
            M2_j=frame.releases.M2_j,
            M3_j=frame.releases.M3_j,
        ),
        label=frame.label,
    )


@router.delete("/{project_id}/frames/{frame_id}", status_code=204)
async def delete_frame(project_id: UUID, frame_id: int):
    """Delete a frame."""
    model = get_model(project_id)

    try:
        model.remove_frame(frame_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Shells ---


def _shell_to_response(shell: Shell) -> ShellResponse:
    """Convert a Shell domain object to ShellResponse schema."""
    return ShellResponse(
        id=shell.id,
        node_ids=list(shell.node_ids),
        material_name=shell.material_name,
        thickness=shell.thickness,
        shell_type=ShellTypeEnum(shell.shell_type.value),
        label=shell.label,
    )


@router.get("/{project_id}/shells", response_model=list[ShellResponse])
async def list_shells(project_id: UUID):
    """List all shells in a project."""
    model = get_model(project_id)
    return [_shell_to_response(shell) for shell in model.shells]


@router.post("/{project_id}/shells", response_model=ShellResponse, status_code=201)
async def create_shell(project_id: UUID, data: ShellCreate):
    """Create a new shell."""
    model = get_model(project_id)

    try:
        shell_type = ShellType(data.shell_type.value)
        shell = model.add_shell(
            node_ids=data.node_ids,
            material_name=data.material_name,
            thickness=data.thickness,
            shell_type=shell_type,
            label=data.label,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _shell_to_response(shell)


@router.get("/{project_id}/shells/{shell_id}", response_model=ShellResponse)
async def get_shell(project_id: UUID, shell_id: int):
    """Get a shell by ID."""
    model = get_model(project_id)

    try:
        shell = model.get_shell(shell_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Shell not found")

    return _shell_to_response(shell)


@router.patch("/{project_id}/shells/{shell_id}", response_model=ShellResponse)
async def update_shell(project_id: UUID, shell_id: int, data: ShellUpdate):
    """Update a shell."""
    model = get_model(project_id)

    try:
        shell = model.get_shell(shell_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Shell not found")

    if data.material_name is not None:
        shell.material_name = data.material_name
    if data.thickness is not None:
        shell.thickness = data.thickness
    if data.shell_type is not None:
        shell.shell_type = ShellType(data.shell_type.value)
    if data.label is not None:
        shell.label = data.label

    return _shell_to_response(shell)


@router.delete("/{project_id}/shells/{shell_id}", status_code=204)
async def delete_shell(project_id: UUID, shell_id: int):
    """Delete a shell."""
    model = get_model(project_id)

    try:
        model.remove_shell(shell_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Groups ---


def _group_to_response(group: ElementGroup) -> GroupResponse:
    """Convert an ElementGroup domain object to GroupResponse schema."""
    return GroupResponse(
        id=group.id,
        name=group.name,
        node_ids=sorted(group.node_ids),
        frame_ids=sorted(group.frame_ids),
        shell_ids=sorted(group.shell_ids),
        color=group.color,
        parent_id=group.parent_id,
        description=group.description,
        element_count=group.element_count,
    )


@router.get("/{project_id}/groups", response_model=list[GroupResponse])
async def list_groups(project_id: UUID):
    """List all groups in a project."""
    model = get_model(project_id)
    return [_group_to_response(group) for group in model.groups]


@router.post("/{project_id}/groups", response_model=GroupResponse, status_code=201)
async def create_group(project_id: UUID, data: GroupCreate):
    """Create a new element group."""
    model = get_model(project_id)

    try:
        group = model.add_group(
            name=data.name,
            node_ids=data.node_ids,
            frame_ids=data.frame_ids,
            shell_ids=data.shell_ids,
            color=data.color,
            parent_id=data.parent_id,
            description=data.description,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _group_to_response(group)


@router.get("/{project_id}/groups/{group_id}", response_model=GroupResponse)
async def get_group(project_id: UUID, group_id: int):
    """Get a group by ID."""
    model = get_model(project_id)

    try:
        group = model.get_group(group_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Group not found")

    return _group_to_response(group)


@router.patch("/{project_id}/groups/{group_id}", response_model=GroupResponse)
async def update_group(project_id: UUID, group_id: int, data: GroupUpdate):
    """Update a group."""
    model = get_model(project_id)

    try:
        # Build update kwargs, handling the special case for parent_id
        update_kwargs = {}
        if data.name is not None:
            update_kwargs["name"] = data.name
        if data.node_ids is not None:
            update_kwargs["node_ids"] = data.node_ids
        if data.frame_ids is not None:
            update_kwargs["frame_ids"] = data.frame_ids
        if data.shell_ids is not None:
            update_kwargs["shell_ids"] = data.shell_ids
        if data.color is not None:
            update_kwargs["color"] = data.color
        if data.parent_id is not ...:
            update_kwargs["parent_id"] = data.parent_id
        if data.description is not None:
            update_kwargs["description"] = data.description

        group = model.update_group(group_id, **update_kwargs)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _group_to_response(group)


@router.delete("/{project_id}/groups/{group_id}", status_code=204)
async def delete_group(project_id: UUID, group_id: int):
    """Delete a group (does not delete contained elements)."""
    model = get_model(project_id)

    try:
        model.remove_group(group_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

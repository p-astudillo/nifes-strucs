"""
Commands for frame operations.

Implements reversible commands for creating, deleting, and modifying frames.
"""

from dataclasses import dataclass

from paz.application.commands.base_command import Command
from paz.domain.model.frame import Frame, FrameReleases
from paz.domain.model.structural_model import StructuralModel


@dataclass
class CreateFrameCommand(Command):
    """Command to create a new frame."""

    model: StructuralModel
    node_i_id: int
    node_j_id: int
    material_name: str
    section_name: str
    rotation: float = 0.0
    releases: FrameReleases | None = None
    frame_id: int | None = None
    label: str = ""
    _created_frame: Frame | None = None

    def execute(self) -> Frame:
        """Create the frame and return it."""
        self._created_frame = self.model.add_frame(
            node_i_id=self.node_i_id,
            node_j_id=self.node_j_id,
            material_name=self.material_name,
            section_name=self.section_name,
            rotation=self.rotation,
            releases=self.releases,
            frame_id=self.frame_id,
            label=self.label,
        )
        return self._created_frame

    def undo(self) -> None:
        """Remove the created frame."""
        if self._created_frame is not None:
            self.model.remove_frame(self._created_frame.id)
            self._created_frame = None

    @property
    def description(self) -> str:
        return f"Create frame from node {self.node_i_id} to {self.node_j_id}"


@dataclass
class DeleteFrameCommand(Command):
    """Command to delete a frame."""

    model: StructuralModel
    frame_id: int
    _deleted_frame: Frame | None = None

    def execute(self) -> None:
        """Delete the frame."""
        self._deleted_frame = self.model.remove_frame(self.frame_id)

    def undo(self) -> None:
        """Restore the deleted frame."""
        if self._deleted_frame is not None:
            self.model.add_frame(
                node_i_id=self._deleted_frame.node_i_id,
                node_j_id=self._deleted_frame.node_j_id,
                material_name=self._deleted_frame.material_name,
                section_name=self._deleted_frame.section_name,
                rotation=self._deleted_frame.rotation,
                releases=self._deleted_frame.releases,
                frame_id=self._deleted_frame.id,
                label=self._deleted_frame.label,
            )
            self._deleted_frame = None

    @property
    def description(self) -> str:
        return f"Delete frame {self.frame_id}"


@dataclass
class UpdateFrameMaterialCommand(Command):
    """Command to update frame material."""

    model: StructuralModel
    frame_id: int
    new_material_name: str
    _old_material_name: str | None = None

    def execute(self) -> Frame:
        """Update the material and return the frame."""
        frame = self.model.get_frame(self.frame_id)

        # Store old value for undo
        self._old_material_name = frame.material_name

        # Update
        self.model.update_frame(self.frame_id, material_name=self.new_material_name)

        return frame

    def undo(self) -> None:
        """Restore the original material."""
        if self._old_material_name is not None:
            self.model.update_frame(self.frame_id, material_name=self._old_material_name)

    @property
    def description(self) -> str:
        return f"Update material for frame {self.frame_id} to {self.new_material_name}"


@dataclass
class UpdateFrameSectionCommand(Command):
    """Command to update frame section."""

    model: StructuralModel
    frame_id: int
    new_section_name: str
    _old_section_name: str | None = None

    def execute(self) -> Frame:
        """Update the section and return the frame."""
        frame = self.model.get_frame(self.frame_id)

        # Store old value for undo
        self._old_section_name = frame.section_name

        # Update
        self.model.update_frame(self.frame_id, section_name=self.new_section_name)

        return frame

    def undo(self) -> None:
        """Restore the original section."""
        if self._old_section_name is not None:
            self.model.update_frame(self.frame_id, section_name=self._old_section_name)

    @property
    def description(self) -> str:
        return f"Update section for frame {self.frame_id} to {self.new_section_name}"


@dataclass
class UpdateFrameRotationCommand(Command):
    """Command to update frame rotation."""

    model: StructuralModel
    frame_id: int
    new_rotation: float
    _old_rotation: float | None = None

    def execute(self) -> Frame:
        """Update the rotation and return the frame."""
        frame = self.model.get_frame(self.frame_id)

        # Store old value for undo
        self._old_rotation = frame.rotation

        # Update
        self.model.update_frame(self.frame_id, rotation=self.new_rotation)

        return frame

    def undo(self) -> None:
        """Restore the original rotation."""
        if self._old_rotation is not None:
            self.model.update_frame(self.frame_id, rotation=self._old_rotation)

    @property
    def description(self) -> str:
        return f"Update rotation for frame {self.frame_id} to {self.new_rotation}"


@dataclass
class UpdateFrameReleasesCommand(Command):
    """Command to update frame end releases."""

    model: StructuralModel
    frame_id: int
    new_releases: FrameReleases
    _old_releases: FrameReleases | None = None

    def execute(self) -> Frame:
        """Update the releases and return the frame."""
        frame = self.model.get_frame(self.frame_id)

        # Store old value for undo
        self._old_releases = frame.releases

        # Update
        self.model.update_frame(self.frame_id, releases=self.new_releases)

        return frame

    def undo(self) -> None:
        """Restore the original releases."""
        if self._old_releases is not None:
            self.model.update_frame(self.frame_id, releases=self._old_releases)

    @property
    def description(self) -> str:
        return f"Update releases for frame {self.frame_id}"

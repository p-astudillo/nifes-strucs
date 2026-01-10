"""
Model validation for structural analysis.

Validates that a structural model is ready for analysis:
- Has nodes and frames
- Has proper boundary conditions (supports)
- All frames reference valid materials and sections
- Model is statically determinate or indeterminate (not a mechanism)
"""

from dataclasses import dataclass, field

from paz.domain.materials import Material
from paz.domain.model import StructuralModel
from paz.domain.sections import Section


@dataclass
class ValidationResult:
    """Result of model validation."""

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add an error and mark as invalid."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning (doesn't invalidate)."""
        self.warnings.append(message)


class ModelValidator:
    """Validates structural models for analysis."""

    def __init__(
        self,
        model: StructuralModel,
        materials: dict[str, Material],
        sections: dict[str, Section],
    ) -> None:
        """
        Initialize validator.

        Args:
            model: The structural model to validate
            materials: Available materials by name
            sections: Available sections by name
        """
        self.model = model
        self.materials = materials
        self.sections = sections

    def validate(self) -> ValidationResult:
        """
        Run all validations on the model.

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()

        self._check_has_nodes(result)
        self._check_has_frames(result)
        self._check_has_supports(result)
        self._check_material_references(result)
        self._check_section_references(result)
        self._check_stability(result)

        return result

    def _check_has_nodes(self, result: ValidationResult) -> None:
        """Check that model has at least 2 nodes."""
        if self.model.node_count == 0:
            result.add_error("Model has no nodes")
        elif self.model.node_count == 1:
            result.add_error("Model must have at least 2 nodes")

    def _check_has_frames(self, result: ValidationResult) -> None:
        """Check that model has at least 1 frame."""
        if self.model.frame_count == 0:
            result.add_error("Model has no frame elements")

    def _check_has_supports(self, result: ValidationResult) -> None:
        """Check that model has adequate support conditions."""
        supported_nodes = self.model.get_supported_nodes()

        if not supported_nodes:
            result.add_error("Model has no supported nodes (no boundary conditions)")
            return

        # Count total restrained DOFs
        total_restrained = 0
        for node in supported_nodes:
            total_restrained += sum(node.restraint.to_int_list())

        # For 3D, minimum 6 DOFs must be restrained for stability
        if total_restrained < 6:
            result.add_error(
                f"Insufficient restraints: only {total_restrained} DOFs restrained. "
                "Need at least 6 for 3D stability."
            )

        # Check for rigid body motion prevention
        # Simplified check: must have at least one translation restrained in each direction
        has_ux = any(n.restraint.ux for n in supported_nodes)
        has_uy = any(n.restraint.uy for n in supported_nodes)
        has_uz = any(n.restraint.uz for n in supported_nodes)

        if not (has_ux and has_uy and has_uz):
            missing = []
            if not has_ux:
                missing.append("X")
            if not has_uy:
                missing.append("Y")
            if not has_uz:
                missing.append("Z")
            result.add_warning(
                f"No translation restraint in {', '.join(missing)} direction(s). "
                "Model may have rigid body motion."
            )

    def _check_material_references(self, result: ValidationResult) -> None:
        """Check that all frames reference existing materials."""
        for frame in self.model.frames:
            if frame.material_name not in self.materials:
                result.add_error(
                    f"Frame {frame.id} references unknown material '{frame.material_name}'"
                )

    def _check_section_references(self, result: ValidationResult) -> None:
        """Check that all frames reference existing sections."""
        for frame in self.model.frames:
            if frame.section_name not in self.sections:
                result.add_error(
                    f"Frame {frame.id} references unknown section '{frame.section_name}'"
                )

    def _check_stability(self, result: ValidationResult) -> None:
        """
        Basic stability check.

        For a more rigorous check, would need to analyze the stiffness matrix.
        This simplified version checks connectivity.
        """
        if self.model.node_count == 0 or self.model.frame_count == 0:
            return  # Already reported errors

        # Check that all nodes are connected (no floating nodes)
        connected_nodes: set[int] = set()
        for frame in self.model.frames:
            connected_nodes.add(frame.node_i_id)
            connected_nodes.add(frame.node_j_id)

        all_node_ids = {node.id for node in self.model.nodes}
        unconnected = all_node_ids - connected_nodes

        if unconnected:
            result.add_warning(
                f"Nodes {sorted(unconnected)} are not connected to any frame elements"
            )

        # Check that at least one supported node is connected
        supported_and_connected = False
        for node in self.model.get_supported_nodes():
            if node.id in connected_nodes:
                supported_and_connected = True
                break

        if not supported_and_connected and self.model.get_supported_nodes():
            result.add_error(
                "No supported node is connected to frame elements. "
                "Model will be unstable."
            )


def validate_model_for_analysis(
    model: StructuralModel,
    materials: dict[str, Material],
    sections: dict[str, Section],
) -> ValidationResult:
    """
    Convenience function to validate a model for analysis.

    Args:
        model: The structural model
        materials: Available materials
        sections: Available sections

    Returns:
        ValidationResult with any errors/warnings found
    """
    validator = ModelValidator(model, materials, sections)
    return validator.validate()

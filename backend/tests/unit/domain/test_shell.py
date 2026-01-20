"""
Unit tests for Shell domain model.
"""

import pytest

from paz.domain.model.node import Node
from paz.domain.model.shell import Shell, ShellType, MIN_SHELL_AREA, validate_shell_area
from paz.domain.materials import Material
from paz.core.exceptions import ValidationError


class TestShellCreation:
    """Tests for Shell creation and validation."""

    def test_create_triangular_shell(self):
        """Test creating a 3-node shell."""
        shell = Shell(
            node_ids=[1, 2, 3],
            material_name="H25",
            thickness=0.2,
        )
        assert shell.num_nodes == 3
        assert shell.is_triangular
        assert not shell.is_quadrilateral

    def test_create_quadrilateral_shell(self):
        """Test creating a 4-node shell."""
        shell = Shell(
            node_ids=[1, 2, 3, 4],
            material_name="H25",
            thickness=0.2,
        )
        assert shell.num_nodes == 4
        assert shell.is_quadrilateral
        assert not shell.is_triangular

    def test_shell_with_all_properties(self):
        """Test shell with all properties set."""
        shell = Shell(
            id=10,
            node_ids=[1, 2, 3, 4],
            material_name="H25",
            thickness=0.15,
            shell_type=ShellType.PLATE,
            label="Losa Piso 1",
        )
        assert shell.id == 10
        assert shell.thickness == 0.15
        assert shell.shell_type == ShellType.PLATE
        assert shell.label == "Losa Piso 1"

    def test_default_shell_type_is_shell(self):
        """Test default shell type."""
        shell = Shell(
            node_ids=[1, 2, 3],
            material_name="H25",
            thickness=0.2,
        )
        assert shell.shell_type == ShellType.SHELL

    def test_reject_less_than_3_nodes(self):
        """Test rejection of shells with less than 3 nodes."""
        with pytest.raises(ValidationError) as exc_info:
            Shell(
                node_ids=[1, 2],
                material_name="H25",
                thickness=0.2,
            )
        assert "3 or 4 nodes" in str(exc_info.value)

    def test_reject_more_than_4_nodes(self):
        """Test rejection of shells with more than 4 nodes."""
        with pytest.raises(ValidationError) as exc_info:
            Shell(
                node_ids=[1, 2, 3, 4, 5],
                material_name="H25",
                thickness=0.2,
            )
        assert "3 or 4 nodes" in str(exc_info.value)

    def test_reject_duplicate_nodes(self):
        """Test rejection of duplicate node IDs."""
        with pytest.raises(ValidationError) as exc_info:
            Shell(
                node_ids=[1, 2, 2, 3],
                material_name="H25",
                thickness=0.2,
            )
        assert "duplicate" in str(exc_info.value).lower()

    def test_reject_empty_material(self):
        """Test rejection of empty material name."""
        with pytest.raises(ValidationError) as exc_info:
            Shell(
                node_ids=[1, 2, 3],
                material_name="",
                thickness=0.2,
            )
        assert "material" in str(exc_info.value).lower()

    def test_reject_zero_thickness(self):
        """Test rejection of zero thickness."""
        with pytest.raises(ValidationError) as exc_info:
            Shell(
                node_ids=[1, 2, 3],
                material_name="H25",
                thickness=0.0,
            )
        assert "positive" in str(exc_info.value).lower()

    def test_reject_negative_thickness(self):
        """Test rejection of negative thickness."""
        with pytest.raises(ValidationError) as exc_info:
            Shell(
                node_ids=[1, 2, 3],
                material_name="H25",
                thickness=-0.1,
            )
        assert "positive" in str(exc_info.value).lower()


class TestShellGeometry:
    """Tests for Shell geometric calculations."""

    @pytest.fixture
    def triangular_shell_with_nodes(self):
        """Create a triangular shell with nodes set."""
        shell = Shell(
            node_ids=[1, 2, 3],
            material_name="H25",
            thickness=0.2,
        )
        nodes = [
            Node(id=1, x=0.0, y=0.0, z=0.0),
            Node(id=2, x=2.0, y=0.0, z=0.0),
            Node(id=3, x=1.0, y=2.0, z=0.0),
        ]
        shell.set_nodes(nodes)
        return shell

    @pytest.fixture
    def quad_shell_with_nodes(self):
        """Create a quadrilateral shell with nodes set."""
        shell = Shell(
            node_ids=[1, 2, 3, 4],
            material_name="H25",
            thickness=0.2,
        )
        nodes = [
            Node(id=1, x=0.0, y=0.0, z=0.0),
            Node(id=2, x=3.0, y=0.0, z=0.0),
            Node(id=3, x=3.0, y=2.0, z=0.0),
            Node(id=4, x=0.0, y=2.0, z=0.0),
        ]
        shell.set_nodes(nodes)
        return shell

    def test_triangular_area(self, triangular_shell_with_nodes):
        """Test area calculation for triangular shell."""
        area = triangular_shell_with_nodes.area()
        # Area of triangle with base 2 and height 2 = 0.5 * 2 * 2 = 2.0
        assert abs(area - 2.0) < 1e-9

    def test_quad_area(self, quad_shell_with_nodes):
        """Test area calculation for quadrilateral shell."""
        area = quad_shell_with_nodes.area()
        # Area of 3x2 rectangle = 6.0
        assert abs(area - 6.0) < 1e-9

    def test_triangular_centroid(self, triangular_shell_with_nodes):
        """Test centroid calculation for triangular shell."""
        cx, cy, cz = triangular_shell_with_nodes.centroid()
        # Centroid of triangle (0,0), (2,0), (1,2) = (1, 2/3, 0)
        assert abs(cx - 1.0) < 1e-9
        assert abs(cy - 2.0/3.0) < 1e-9
        assert abs(cz - 0.0) < 1e-9

    def test_quad_centroid(self, quad_shell_with_nodes):
        """Test centroid calculation for quadrilateral shell."""
        cx, cy, cz = quad_shell_with_nodes.centroid()
        # Centroid of rectangle = (1.5, 1.0, 0)
        assert abs(cx - 1.5) < 1e-9
        assert abs(cy - 1.0) < 1e-9
        assert abs(cz - 0.0) < 1e-9

    def test_normal_for_horizontal_shell(self, quad_shell_with_nodes):
        """Test normal vector for horizontal shell."""
        nx, ny, nz = quad_shell_with_nodes.normal()
        # For shell in XY plane, normal should be +Z or -Z
        assert abs(nx) < 1e-9
        assert abs(ny) < 1e-9
        assert abs(abs(nz) - 1.0) < 1e-9

    def test_normal_for_vertical_shell(self):
        """Test normal vector for vertical shell (wall)."""
        shell = Shell(
            node_ids=[1, 2, 3, 4],
            material_name="H25",
            thickness=0.2,
        )
        # Vertical wall in XZ plane
        nodes = [
            Node(id=1, x=0.0, y=0.0, z=0.0),
            Node(id=2, x=3.0, y=0.0, z=0.0),
            Node(id=3, x=3.0, y=0.0, z=2.0),
            Node(id=4, x=0.0, y=0.0, z=2.0),
        ]
        shell.set_nodes(nodes)
        nx, ny, nz = shell.normal()
        # For wall in XZ plane, normal should be +Y or -Y
        assert abs(nx) < 1e-9
        assert abs(abs(ny) - 1.0) < 1e-9
        assert abs(nz) < 1e-9

    def test_area_without_nodes_raises_error(self):
        """Test that area() raises error if nodes not set."""
        shell = Shell(
            node_ids=[1, 2, 3],
            material_name="H25",
            thickness=0.2,
        )
        with pytest.raises(ValidationError) as exc_info:
            shell.area()
        assert "nodes" in str(exc_info.value).lower()


class TestShellMass:
    """Tests for Shell mass calculations."""

    @pytest.fixture
    def concrete_material(self):
        """Create a concrete material."""
        return Material(
            name="H25",
            material_type="Concrete",
            E=2.5e10,  # Pa
            nu=0.2,
            rho=2400,  # kg/m³
        )

    @pytest.fixture
    def slab_shell(self, concrete_material):
        """Create a 4m x 3m slab shell with nodes set."""
        shell = Shell(
            node_ids=[1, 2, 3, 4],
            material_name="H25",
            thickness=0.2,  # 20cm thick
        )
        nodes = [
            Node(id=1, x=0.0, y=0.0, z=0.0),
            Node(id=2, x=4.0, y=0.0, z=0.0),
            Node(id=3, x=4.0, y=3.0, z=0.0),
            Node(id=4, x=0.0, y=3.0, z=0.0),
        ]
        shell.set_nodes(nodes)
        return shell

    def test_shell_mass(self, slab_shell, concrete_material):
        """Test mass calculation."""
        mass = slab_shell.mass(concrete_material)
        # Mass = rho * t * A = 2400 * 0.2 * 12 = 5760 kg
        expected_mass = 2400 * 0.2 * 12.0
        assert abs(mass - expected_mass) < 1e-6

    def test_shell_weight(self, slab_shell, concrete_material):
        """Test weight calculation."""
        weight = slab_shell.weight(concrete_material)
        # Weight = mass * g / 1000 = 5760 * 9.81 / 1000 = 56.5 kN
        expected_weight = 2400 * 0.2 * 12.0 * 9.81 / 1000
        assert abs(weight - expected_weight) < 1e-6


class TestShellSerialization:
    """Tests for Shell serialization."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        shell = Shell(
            id=5,
            node_ids=[1, 2, 3, 4],
            material_name="H25",
            thickness=0.2,
            shell_type=ShellType.PLATE,
            label="Losa",
        )
        data = shell.to_dict()
        assert data["id"] == 5
        assert data["node_ids"] == [1, 2, 3, 4]
        assert data["material_name"] == "H25"
        assert data["thickness"] == 0.2
        assert data["shell_type"] == "plate"
        assert data["label"] == "Losa"

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "id": 5,
            "node_ids": [1, 2, 3, 4],
            "material_name": "H25",
            "thickness": 0.2,
            "shell_type": "plate",
            "label": "Losa",
        }
        shell = Shell.from_dict(data)
        assert shell.id == 5
        assert shell.node_ids == [1, 2, 3, 4]
        assert shell.material_name == "H25"
        assert shell.thickness == 0.2
        assert shell.shell_type == ShellType.PLATE
        assert shell.label == "Losa"

    def test_from_dict_with_defaults(self):
        """Test deserialization with missing optional fields."""
        data = {
            "node_ids": [1, 2, 3],
            "material_name": "H25",
            "thickness": 0.15,
        }
        shell = Shell.from_dict(data)
        assert shell.id == -1
        assert shell.shell_type == ShellType.SHELL
        assert shell.label == ""

    def test_roundtrip_serialization(self):
        """Test that to_dict -> from_dict produces equal shell."""
        original = Shell(
            id=7,
            node_ids=[1, 2, 3],
            material_name="H30",
            thickness=0.25,
            shell_type=ShellType.MEMBRANE,
            label="Muro",
        )
        data = original.to_dict()
        restored = Shell.from_dict(data)
        assert restored.id == original.id
        assert restored.node_ids == original.node_ids
        assert restored.material_name == original.material_name
        assert restored.thickness == original.thickness
        assert restored.shell_type == original.shell_type
        assert restored.label == original.label


class TestValidateShellArea:
    """Tests for validate_shell_area function."""

    def test_valid_triangle_area(self):
        """Test validation passes for valid triangle."""
        nodes = [
            Node(id=1, x=0.0, y=0.0, z=0.0),
            Node(id=2, x=1.0, y=0.0, z=0.0),
            Node(id=3, x=0.5, y=1.0, z=0.0),
        ]
        area = validate_shell_area(nodes)
        assert area > MIN_SHELL_AREA

    def test_valid_quad_area(self):
        """Test validation passes for valid quad."""
        nodes = [
            Node(id=1, x=0.0, y=0.0, z=0.0),
            Node(id=2, x=2.0, y=0.0, z=0.0),
            Node(id=3, x=2.0, y=2.0, z=0.0),
            Node(id=4, x=0.0, y=2.0, z=0.0),
        ]
        area = validate_shell_area(nodes)
        assert abs(area - 4.0) < 1e-9

    def test_degenerate_triangle_rejected(self):
        """Test that collinear nodes (zero area) are rejected."""
        nodes = [
            Node(id=1, x=0.0, y=0.0, z=0.0),
            Node(id=2, x=1.0, y=0.0, z=0.0),
            Node(id=3, x=2.0, y=0.0, z=0.0),  # Collinear
        ]
        with pytest.raises(ValidationError) as exc_info:
            validate_shell_area(nodes)
        assert "below minimum" in str(exc_info.value).lower()

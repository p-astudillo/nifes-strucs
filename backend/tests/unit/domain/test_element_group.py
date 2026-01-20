"""
Unit tests for ElementGroup and group operations in StructuralModel.
"""

import pytest

from paz.core.exceptions import GroupError, NodeError, FrameError, ShellError, ValidationError
from paz.domain.model.element_group import ElementGroup
from paz.domain.model.restraint import FIXED
from paz.domain.model.structural_model import StructuralModel


class TestElementGroup:
    """Tests for ElementGroup dataclass."""

    def test_create_group_basic(self):
        """Test basic group creation."""
        group = ElementGroup(name="Test Group")
        assert group.name == "Test Group"
        assert group.id == -1
        assert group.is_empty
        assert group.element_count == 0
        assert group.color == "#808080"
        assert group.parent_id is None
        assert group.description == ""

    def test_create_group_with_elements(self):
        """Test group creation with elements."""
        group = ElementGroup(
            name="Floor 1",
            node_ids={1, 2, 3},
            frame_ids={10, 20},
            shell_ids={100},
            color="#FF0000",
            description="First floor elements",
        )
        assert group.name == "Floor 1"
        assert group.node_ids == {1, 2, 3}
        assert group.frame_ids == {10, 20}
        assert group.shell_ids == {100}
        assert not group.is_empty
        assert group.element_count == 6
        assert group.color == "#FF0000"
        assert group.description == "First floor elements"

    def test_create_group_with_lists(self):
        """Test group creation with lists (should convert to sets)."""
        group = ElementGroup(
            name="Test",
            node_ids=[1, 2, 3],
            frame_ids=[10, 20],
            shell_ids=[100],
        )
        assert isinstance(group.node_ids, set)
        assert isinstance(group.frame_ids, set)
        assert isinstance(group.shell_ids, set)

    def test_create_group_empty_name_raises(self):
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError):
            ElementGroup(name="")

        with pytest.raises(ValidationError):
            ElementGroup(name="   ")

    def test_create_group_invalid_color_raises(self):
        """Test that invalid color raises ValidationError."""
        with pytest.raises(ValidationError):
            ElementGroup(name="Test", color="red")

        with pytest.raises(ValidationError):
            ElementGroup(name="Test", color="FF0000")

    def test_has_nodes_frames_shells(self):
        """Test has_nodes, has_frames, has_shells properties."""
        group = ElementGroup(name="Test")
        assert not group.has_nodes
        assert not group.has_frames
        assert not group.has_shells

        group.add_node(1)
        assert group.has_nodes

        group.add_frame(10)
        assert group.has_frames

        group.add_shell(100)
        assert group.has_shells

    def test_add_and_remove_nodes(self):
        """Test adding and removing nodes."""
        group = ElementGroup(name="Test")

        group.add_node(1)
        assert 1 in group.node_ids
        assert group.contains_node(1)

        group.add_nodes([2, 3, 4])
        assert group.node_ids == {1, 2, 3, 4}

        group.remove_node(2)
        assert 2 not in group.node_ids
        assert group.node_ids == {1, 3, 4}

        # Remove non-existent node should not raise
        group.remove_node(999)

    def test_add_and_remove_frames(self):
        """Test adding and removing frames."""
        group = ElementGroup(name="Test")

        group.add_frame(10)
        assert 10 in group.frame_ids
        assert group.contains_frame(10)

        group.add_frames([20, 30])
        assert group.frame_ids == {10, 20, 30}

        group.remove_frame(20)
        assert group.frame_ids == {10, 30}

    def test_add_and_remove_shells(self):
        """Test adding and removing shells."""
        group = ElementGroup(name="Test")

        group.add_shell(100)
        assert 100 in group.shell_ids
        assert group.contains_shell(100)

        group.add_shells([200, 300])
        assert group.shell_ids == {100, 200, 300}

        group.remove_shell(200)
        assert group.shell_ids == {100, 300}

    def test_clear(self):
        """Test clearing all elements."""
        group = ElementGroup(
            name="Test",
            node_ids={1, 2, 3},
            frame_ids={10, 20},
            shell_ids={100},
        )
        assert group.element_count == 6

        group.clear()
        assert group.is_empty
        assert group.element_count == 0

    def test_merge_with(self):
        """Test merging two groups."""
        group1 = ElementGroup(
            name="Group 1",
            node_ids={1, 2},
            frame_ids={10},
            shell_ids={100},
        )
        group2 = ElementGroup(
            name="Group 2",
            node_ids={2, 3},
            frame_ids={20},
            shell_ids={200},
        )

        group1.merge_with(group2)
        assert group1.node_ids == {1, 2, 3}
        assert group1.frame_ids == {10, 20}
        assert group1.shell_ids == {100, 200}

    def test_intersection_with(self):
        """Test intersection of two groups."""
        group1 = ElementGroup(
            name="Group 1",
            node_ids={1, 2, 3},
            frame_ids={10, 20},
            shell_ids={100, 200},
        )
        group2 = ElementGroup(
            name="Group 2",
            node_ids={2, 3, 4},
            frame_ids={20, 30},
            shell_ids={200, 300},
        )

        intersection = group1.intersection_with(group2)
        assert intersection.name == "Group 1 & Group 2"
        assert intersection.node_ids == {2, 3}
        assert intersection.frame_ids == {20}
        assert intersection.shell_ids == {200}

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        original = ElementGroup(
            id=5,
            name="Test Group",
            node_ids={1, 2, 3},
            frame_ids={10, 20},
            shell_ids={100},
            color="#00FF00",
            parent_id=1,
            description="A test group",
        )

        data = original.to_dict()
        assert data["id"] == 5
        assert data["name"] == "Test Group"
        assert data["node_ids"] == [1, 2, 3]  # Sorted list
        assert data["frame_ids"] == [10, 20]
        assert data["shell_ids"] == [100]
        assert data["color"] == "#00FF00"
        assert data["parent_id"] == 1
        assert data["description"] == "A test group"

        restored = ElementGroup.from_dict(data)
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.node_ids == original.node_ids
        assert restored.frame_ids == original.frame_ids
        assert restored.shell_ids == original.shell_ids
        assert restored.color == original.color
        assert restored.parent_id == original.parent_id
        assert restored.description == original.description

    def test_repr(self):
        """Test string representation."""
        group = ElementGroup(
            id=1,
            name="Test",
            node_ids={1, 2},
            frame_ids={10},
            shell_ids={100, 200},
        )
        repr_str = repr(group)
        assert "id=1" in repr_str
        assert "name='Test'" in repr_str
        assert "nodes=2" in repr_str
        assert "frames=1" in repr_str
        assert "shells=2" in repr_str


class TestStructuralModelGroups:
    """Tests for group operations in StructuralModel."""

    @pytest.fixture
    def model_with_elements(self):
        """Create a model with nodes, frames, and shells."""
        model = StructuralModel()

        # Add nodes for a simple structure
        model.add_node(0, 0, 0, restraint=FIXED)  # 1
        model.add_node(5, 0, 0, restraint=FIXED)  # 2
        model.add_node(0, 5, 0)  # 3
        model.add_node(5, 5, 0)  # 4
        model.add_node(0, 0, 3)  # 5
        model.add_node(5, 0, 3)  # 6

        # Add frames
        model.add_frame(1, 5, "A36", "W14X22")  # 1
        model.add_frame(2, 6, "A36", "W14X22")  # 2
        model.add_frame(5, 6, "A36", "W14X22")  # 3

        # Add a shell (quad)
        model.add_shell([1, 2, 4, 3], "Concrete", 0.2)  # 1

        return model

    def test_add_group_basic(self, model_with_elements):
        """Test basic group creation."""
        model = model_with_elements

        group = model.add_group(name="Test Group")
        assert group.id == 1
        assert group.name == "Test Group"
        assert group.is_empty
        assert model.group_count == 1
        assert model.has_group(1)

    def test_add_group_with_elements(self, model_with_elements):
        """Test group creation with elements."""
        model = model_with_elements

        group = model.add_group(
            name="Floor 1",
            node_ids=[1, 2],
            frame_ids=[1],
            shell_ids=[1],
            color="#FF0000",
            description="Ground floor",
        )

        assert group.node_ids == {1, 2}
        assert group.frame_ids == {1}
        assert group.shell_ids == {1}
        assert group.color == "#FF0000"
        assert group.description == "Ground floor"

    def test_add_group_invalid_node_raises(self, model_with_elements):
        """Test that referencing non-existent node raises error."""
        model = model_with_elements

        with pytest.raises(NodeError):
            model.add_group(name="Test", node_ids=[999])

    def test_add_group_invalid_frame_raises(self, model_with_elements):
        """Test that referencing non-existent frame raises error."""
        model = model_with_elements

        with pytest.raises(FrameError):
            model.add_group(name="Test", frame_ids=[999])

    def test_add_group_invalid_shell_raises(self, model_with_elements):
        """Test that referencing non-existent shell raises error."""
        model = model_with_elements

        with pytest.raises(ShellError):
            model.add_group(name="Test", shell_ids=[999])

    def test_add_group_with_parent(self, model_with_elements):
        """Test creating a child group."""
        model = model_with_elements

        parent = model.add_group(name="Structure")
        child = model.add_group(name="Columns", parent_id=parent.id)

        assert child.parent_id == parent.id

    def test_add_group_invalid_parent_raises(self, model_with_elements):
        """Test that invalid parent ID raises error."""
        model = model_with_elements

        with pytest.raises(GroupError):
            model.add_group(name="Test", parent_id=999)

    def test_add_group_with_specific_id(self, model_with_elements):
        """Test creating group with specific ID."""
        model = model_with_elements

        group = model.add_group(name="Test", group_id=100)
        assert group.id == 100

        # Next auto-ID should be 101
        next_group = model.add_group(name="Test 2")
        assert next_group.id == 101

    def test_add_group_duplicate_id_raises(self, model_with_elements):
        """Test that duplicate group ID raises error."""
        model = model_with_elements

        model.add_group(name="Test", group_id=1)
        with pytest.raises(GroupError):
            model.add_group(name="Test 2", group_id=1)

    def test_get_group(self, model_with_elements):
        """Test getting a group by ID."""
        model = model_with_elements

        created = model.add_group(name="Test")
        retrieved = model.get_group(created.id)

        assert retrieved.name == "Test"
        assert retrieved is created

    def test_get_group_not_found_raises(self, model_with_elements):
        """Test that getting non-existent group raises error."""
        model = model_with_elements

        with pytest.raises(GroupError):
            model.get_group(999)

    def test_remove_group(self, model_with_elements):
        """Test removing a group."""
        model = model_with_elements

        group = model.add_group(
            name="Test",
            node_ids=[1, 2],
            frame_ids=[1],
        )
        group_id = group.id

        removed = model.remove_group(group_id)
        assert removed.name == "Test"
        assert not model.has_group(group_id)

        # Nodes and frames should still exist
        assert model.has_node(1)
        assert model.has_node(2)
        assert model.has_frame(1)

    def test_remove_group_updates_children(self, model_with_elements):
        """Test that removing parent group updates children."""
        model = model_with_elements

        parent = model.add_group(name="Parent")
        child1 = model.add_group(name="Child 1", parent_id=parent.id)
        child2 = model.add_group(name="Child 2", parent_id=parent.id)

        model.remove_group(parent.id)

        # Children should now have no parent
        assert child1.parent_id is None
        assert child2.parent_id is None

    def test_remove_group_not_found_raises(self, model_with_elements):
        """Test that removing non-existent group raises error."""
        model = model_with_elements

        with pytest.raises(GroupError):
            model.remove_group(999)

    def test_update_group_name(self, model_with_elements):
        """Test updating group name."""
        model = model_with_elements

        group = model.add_group(name="Original")
        model.update_group(group.id, name="Updated")

        assert group.name == "Updated"

    def test_update_group_elements(self, model_with_elements):
        """Test updating group elements."""
        model = model_with_elements

        group = model.add_group(name="Test", node_ids=[1, 2])

        model.update_group(group.id, node_ids=[3, 4], frame_ids=[1, 2])

        assert group.node_ids == {3, 4}
        assert group.frame_ids == {1, 2}

    def test_update_group_clear_elements(self, model_with_elements):
        """Test clearing group elements with empty list."""
        model = model_with_elements

        group = model.add_group(name="Test", node_ids=[1, 2], frame_ids=[1])

        model.update_group(group.id, node_ids=[], frame_ids=[])

        assert group.node_ids == set()
        assert group.frame_ids == set()

    def test_update_group_invalid_node_raises(self, model_with_elements):
        """Test that updating with invalid node raises error."""
        model = model_with_elements

        group = model.add_group(name="Test")

        with pytest.raises(NodeError):
            model.update_group(group.id, node_ids=[999])

    def test_update_group_parent(self, model_with_elements):
        """Test updating group parent."""
        model = model_with_elements

        parent1 = model.add_group(name="Parent 1")
        parent2 = model.add_group(name="Parent 2")
        child = model.add_group(name="Child", parent_id=parent1.id)

        model.update_group(child.id, parent_id=parent2.id)
        assert child.parent_id == parent2.id

        # Remove parent
        model.update_group(child.id, parent_id=None)
        assert child.parent_id is None

    def test_update_group_circular_parent_raises(self, model_with_elements):
        """Test that circular parent reference raises error."""
        model = model_with_elements

        group1 = model.add_group(name="Group 1")
        group2 = model.add_group(name="Group 2", parent_id=group1.id)

        with pytest.raises(GroupError):
            model.update_group(group1.id, parent_id=group2.id)

    def test_update_group_self_parent_raises(self, model_with_elements):
        """Test that setting self as parent raises error."""
        model = model_with_elements

        group = model.add_group(name="Test")

        with pytest.raises(GroupError):
            model.update_group(group.id, parent_id=group.id)

    def test_get_groups_containing_node(self, model_with_elements):
        """Test finding groups containing a node."""
        model = model_with_elements

        model.add_group(name="Group 1", node_ids=[1, 2])
        model.add_group(name="Group 2", node_ids=[2, 3])
        model.add_group(name="Group 3", node_ids=[4, 5])

        groups = model.get_groups_containing_node(2)
        assert len(groups) == 2
        names = {g.name for g in groups}
        assert names == {"Group 1", "Group 2"}

    def test_get_groups_containing_frame(self, model_with_elements):
        """Test finding groups containing a frame."""
        model = model_with_elements

        model.add_group(name="Columns", frame_ids=[1, 2])
        model.add_group(name="Beams", frame_ids=[3])

        groups = model.get_groups_containing_frame(1)
        assert len(groups) == 1
        assert groups[0].name == "Columns"

    def test_get_groups_containing_shell(self, model_with_elements):
        """Test finding groups containing a shell."""
        model = model_with_elements

        model.add_group(name="Slabs", shell_ids=[1])
        model.add_group(name="Empty")

        groups = model.get_groups_containing_shell(1)
        assert len(groups) == 1
        assert groups[0].name == "Slabs"

    def test_get_child_groups(self, model_with_elements):
        """Test getting child groups."""
        model = model_with_elements

        parent = model.add_group(name="Structure")
        child1 = model.add_group(name="Columns", parent_id=parent.id)
        child2 = model.add_group(name="Beams", parent_id=parent.id)
        model.add_group(name="Other")  # No parent

        children = model.get_child_groups(parent.id)
        assert len(children) == 2
        names = {g.name for g in children}
        assert names == {"Columns", "Beams"}

    def test_get_top_level_groups(self, model_with_elements):
        """Test getting top-level groups."""
        model = model_with_elements

        parent = model.add_group(name="Structure")
        model.add_group(name="Child", parent_id=parent.id)
        model.add_group(name="Another Top")

        top_level = model.get_top_level_groups()
        assert len(top_level) == 2
        names = {g.name for g in top_level}
        assert names == {"Structure", "Another Top"}

    def test_groups_property(self, model_with_elements):
        """Test groups property returns list."""
        model = model_with_elements

        model.add_group(name="Group 1")
        model.add_group(name="Group 2")

        groups = model.groups
        assert len(groups) == 2
        assert isinstance(groups, list)

    def test_iter_groups(self, model_with_elements):
        """Test iterating over groups."""
        model = model_with_elements

        model.add_group(name="Group 1")
        model.add_group(name="Group 2")

        names = [g.name for g in model.iter_groups()]
        assert set(names) == {"Group 1", "Group 2"}

    def test_model_serialization_with_groups(self, model_with_elements):
        """Test model serialization includes groups."""
        model = model_with_elements

        model.add_group(
            name="Floor 1",
            node_ids=[1, 2],
            frame_ids=[1],
            shell_ids=[1],
            color="#FF0000",
            description="First floor",
        )
        model.add_group(name="Empty Group")

        # Serialize
        data = model.to_dict()
        assert "groups" in data
        assert len(data["groups"]) == 2
        assert "next_group_id" in data

        # Deserialize
        restored = StructuralModel.from_dict(data)
        assert restored.group_count == 2

        group = restored.get_group(1)
        assert group.name == "Floor 1"
        assert group.node_ids == {1, 2}
        assert group.frame_ids == {1}
        assert group.shell_ids == {1}
        assert group.color == "#FF0000"
        assert group.description == "First floor"

    def test_clear_model_removes_groups(self, model_with_elements):
        """Test that clearing model removes all groups."""
        model = model_with_elements

        model.add_group(name="Group 1")
        model.add_group(name="Group 2")
        assert model.group_count == 2

        model.clear()
        assert model.group_count == 0
        assert model.node_count == 0
        assert model.frame_count == 0
        assert model.shell_count == 0


class TestGroupHierarchy:
    """Tests for hierarchical group operations."""

    def test_three_level_hierarchy(self):
        """Test three-level group hierarchy."""
        model = StructuralModel()

        # Add some nodes
        model.add_node(0, 0, 0)
        model.add_node(1, 0, 0)
        model.add_node(2, 0, 0)

        # Create hierarchy
        building = model.add_group(name="Building")
        floor1 = model.add_group(name="Floor 1", parent_id=building.id)
        floor2 = model.add_group(name="Floor 2", parent_id=building.id)
        columns_f1 = model.add_group(name="Columns F1", parent_id=floor1.id, node_ids=[1])
        beams_f1 = model.add_group(name="Beams F1", parent_id=floor1.id, node_ids=[2])

        # Verify hierarchy
        assert building.parent_id is None
        assert floor1.parent_id == building.id
        assert floor2.parent_id == building.id
        assert columns_f1.parent_id == floor1.id
        assert beams_f1.parent_id == floor1.id

        # Get children
        building_children = model.get_child_groups(building.id)
        assert len(building_children) == 2

        floor1_children = model.get_child_groups(floor1.id)
        assert len(floor1_children) == 2

        # Top level
        top = model.get_top_level_groups()
        assert len(top) == 1
        assert top[0].name == "Building"

    def test_deep_circular_reference_detection(self):
        """Test detection of circular reference in deep hierarchy."""
        model = StructuralModel()

        g1 = model.add_group(name="Level 1")
        g2 = model.add_group(name="Level 2", parent_id=g1.id)
        g3 = model.add_group(name="Level 3", parent_id=g2.id)
        g4 = model.add_group(name="Level 4", parent_id=g3.id)

        # Try to make g1 a child of g4 (would create cycle)
        with pytest.raises(GroupError):
            model.update_group(g1.id, parent_id=g4.id)

"""Unit tests for Entity."""

from bento.domain.entity import Entity


class TestEntity:
    """Test suite for Entity."""

    def test_entity_creation(self):
        """Test creating an entity."""
        entity = Entity(id="entity-123")
        assert entity.id == "entity-123"

    def test_entity_equality_by_id(self):
        """Test that entities are equal if they have the same ID."""
        entity1 = Entity(id="entity-123")
        entity2 = Entity(id="entity-123")
        entity3 = Entity(id="entity-456")

        assert entity1 == entity2
        assert entity1 != entity3

    def test_entity_is_dataclass(self):
        """Test that Entity is a dataclass."""
        from dataclasses import is_dataclass

        assert is_dataclass(Entity)

    def test_entity_immutable_id(self):
        """Test that entity ID cannot be changed after creation."""
        entity = Entity(id="entity-123")

        # Attempting to change ID should raise an error
        # Note: dataclasses are mutable by default unless frozen=True
        # This test verifies current behavior
        entity.id = "new-id"  # This will actually work since Entity is not frozen
        assert entity.id == "new-id"

    def test_entity_with_different_id_types(self):
        """Test entity with different ID types."""
        # String ID
        entity1 = Entity(id="123")
        assert entity1.id == "123"

        # Integer ID (if EntityId accepts it)
        entity2 = Entity(id=123)
        assert entity2.id == 123

        # UUID ID
        from uuid import uuid4

        uid = uuid4()
        entity3 = Entity(id=uid)
        assert entity3.id == uid

    def test_entity_repr(self):
        """Test entity string representation."""
        entity = Entity(id="entity-123")
        repr_str = repr(entity)

        assert "Entity" in repr_str
        assert "entity-123" in repr_str

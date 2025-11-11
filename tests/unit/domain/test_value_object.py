"""Unit tests for ValueObject."""

import pytest

from bento.domain.value_object import ValueObject


class TestValueObject:
    """Test suite for ValueObject."""

    def test_value_object_creation(self):
        """Test creating a value object."""
        vo = ValueObject(value="test")
        assert vo.value == "test"

    def test_value_object_equality(self):
        """Test that value objects are equal if they have the same value."""
        vo1 = ValueObject(value="test")
        vo2 = ValueObject(value="test")
        vo3 = ValueObject(value="other")

        assert vo1 == vo2
        assert vo1 != vo3

    def test_value_object_not_equal_to_non_value_object(self):
        """Test that value object is not equal to non-value objects."""
        vo = ValueObject(value="test")

        assert vo != "test"
        assert vo != 123
        assert vo is not None
        assert vo != {"value": "test"}

    def test_value_object_hash(self):
        """Test that value objects can be hashed."""
        vo1 = ValueObject(value="test")
        vo2 = ValueObject(value="test")
        vo3 = ValueObject(value="other")

        # Same value should have same hash
        assert hash(vo1) == hash(vo2)

        # Different values should (usually) have different hashes
        assert hash(vo1) != hash(vo3)

    def test_value_object_in_set(self):
        """Test that value objects can be used in sets."""
        vo1 = ValueObject(value="test")
        vo2 = ValueObject(value="test")
        vo3 = ValueObject(value="other")

        value_set = {vo1, vo2, vo3}

        # vo1 and vo2 are equal, so set should contain only 2 items
        assert len(value_set) == 2

    def test_value_object_in_dict(self):
        """Test that value objects can be used as dictionary keys."""
        vo1 = ValueObject(value="test")
        vo2 = ValueObject(value="test")

        value_dict = {vo1: "first"}
        value_dict[vo2] = "second"

        # vo1 and vo2 are equal, so dict should have only 1 key
        assert len(value_dict) == 1
        assert value_dict[vo1] == "second"

    def test_value_object_str(self):
        """Test value object string representation."""
        vo = ValueObject(value="test")
        assert str(vo) == "test"

        vo_int = ValueObject(value=123)
        assert str(vo_int) == "123"

    def test_value_object_immutable(self):
        """Test that value objects are immutable."""
        vo = ValueObject(value="test")

        # Attempting to change value should raise an error
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            vo.value = "new_value"

    def test_value_object_with_complex_types(self):
        """Test value objects with complex value types."""
        # Tuple value
        vo_tuple = ValueObject(value=(1, 2, 3))
        assert vo_tuple.value == (1, 2, 3)

        # Frozen set value
        vo_frozenset = ValueObject(value=frozenset({1, 2, 3}))
        assert vo_frozenset.value == frozenset({1, 2, 3})

    def test_value_object_with_numeric_types(self):
        """Test value objects with different numeric types."""
        vo_int = ValueObject(value=42)
        vo_float = ValueObject(value=3.14)

        assert vo_int.value == 42
        assert vo_float.value == 3.14
        assert vo_int != vo_float  # Different types, different values

    def test_value_object_comparison_type_safety(self):
        """Test that value objects with different value types are not equal."""
        vo_str = ValueObject(value="123")
        vo_int = ValueObject(value=123)

        # String "123" != int 123
        assert vo_str != vo_int

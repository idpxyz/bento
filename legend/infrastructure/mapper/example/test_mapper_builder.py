from dataclasses import dataclass
from typing import Optional

from idp.framework.infrastructure.mapper import MapperBuilder


@dataclass
class SimpleSource:
    name: str
    value: int


@dataclass
class SimpleTarget:
    name: str = ""
    value: int = 0


def test_mapper_builder():
    """Test that the MapperBuilder alias works correctly"""
    print("Testing MapperBuilder alias...")

    # Create a source object
    source = SimpleSource(name="test", value=42)
    print(f"Source: {source}")

    # Create a mapper using MapperBuilder
    mapper = MapperBuilder.for_types(SimpleSource, SimpleTarget) \
        .map("name", "name") \
        .map("value", "value") \
        .build()

    # Map the source to a target
    target = mapper.map(source)
    print(f"Target: {target}")

    # Verify the mapping
    assert target.name == source.name
    assert target.value == source.value

    print("MapperBuilder alias test passed!")


if __name__ == "__main__":
    test_mapper_builder()

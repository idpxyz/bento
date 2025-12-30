"""Unit tests for runtime modules."""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from bento.runtime.module import BentoModule
from bento.runtime.container.base import BentoContainer
from bento.runtime.lifecycle.manager import LifecycleManager


class TestBentoModule:
    """Tests for BentoModule."""

    def test_module_init(self) -> None:
        """Test BentoModule initialization."""
        module = BentoModule()
        assert module is not None


class TestBentoContainer:
    """Tests for BentoContainer."""

    def test_container_init(self) -> None:
        """Test BentoContainer initialization."""
        container = BentoContainer()
        assert container is not None

    def test_container_set_get(self) -> None:
        """Test container set and get."""
        container = BentoContainer()
        container.set("test_key", "test_value")
        value = container.get("test_key")
        assert value == "test_value"

    def test_container_get_missing_key(self) -> None:
        """Test container get with missing key."""
        container = BentoContainer()
        with pytest.raises(KeyError):
            container.get("missing_key")

    def test_container_get_with_default(self) -> None:
        """Test container get with default value."""
        container = BentoContainer()
        value = container.get("missing_key", "default_value")
        assert value == "default_value"


class TestLifecycleManager:
    """Tests for LifecycleManager."""

    def test_lifecycle_manager_init(self) -> None:
        """Test LifecycleManager initialization."""
        runtime = Mock()
        manager = LifecycleManager(runtime)
        assert manager.runtime is runtime


class TestRuntimeIntegration:
    """Integration tests for runtime components."""

    def test_container_with_multiple_values(self) -> None:
        """Test container with multiple values."""
        container = BentoContainer()

        container.set("key1", "value1")
        container.set("key2", "value2")
        container.set("key3", "value3")

        assert container.get("key1") == "value1"
        assert container.get("key2") == "value2"
        assert container.get("key3") == "value3"

    def test_container_overwrite_value(self) -> None:
        """Test container overwrite value."""
        container = BentoContainer()

        container.set("key", "value1")
        assert container.get("key") == "value1"

        container.set("key", "value2")
        assert container.get("key") == "value2"

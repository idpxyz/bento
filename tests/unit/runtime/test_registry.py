"""Unit tests for runtime registries."""

from __future__ import annotations

import sys
from types import ModuleType

import pytest

from bento.runtime.module import BentoModule
from bento.runtime.registry import ModuleRegistry
from bento.runtime.repository.registry import RepositoryRegistry


class InfraModule(BentoModule):
    name = "infra"


class CatalogModule(BentoModule):
    name = "catalog"
    requires = ("infra",)


class PaymentsModule(BentoModule):
    name = "payments"
    requires = ("catalog",)


class CircularAModule(BentoModule):
    name = "a"
    requires = ("b",)


class CircularBModule(BentoModule):
    name = "b"
    requires = ("a",)


class DummyAggregate:
    pass


def test_module_registry_resolve_order_and_cache() -> None:
    registry = ModuleRegistry()
    registry.register(InfraModule()).register(CatalogModule()).register(PaymentsModule())

    first_order = [module.name for module in registry.resolve_order()]
    assert first_order == ["infra", "catalog", "payments"]

    # Cached order should be reused
    second_order = [module.name for module in registry.resolve_order()]
    assert second_order == first_order


def test_module_registry_duplicate_registration_raises() -> None:
    registry = ModuleRegistry()
    registry.register(InfraModule())
    with pytest.raises(ValueError):
        registry.register(InfraModule())


def test_module_registry_missing_dependency_raises() -> None:
    registry = ModuleRegistry()
    registry.register(CatalogModule())
    with pytest.raises(ValueError, match="requires 'infra'"):
        registry.resolve_order()


def test_module_registry_detects_circular_dependencies() -> None:
    registry = ModuleRegistry()
    registry.register(CircularAModule()).register(CircularBModule())
    with pytest.raises(ValueError, match="Circular dependency"):
        registry.resolve_order()


def test_repository_registry_register_and_get_factory() -> None:
    registry = RepositoryRegistry()

    def repo_factory(session):  # pragma: no cover - trivial lambda-like helper
        return {"session": session}

    registry.register(DummyAggregate, repo_factory)
    factory = registry.get_factory(DummyAggregate)
    assert factory("session") == {"session": "session"}


def test_repository_registry_missing_factory() -> None:
    registry = RepositoryRegistry()
    with pytest.raises(ValueError, match="No repository registered"):
        registry.get_factory(DummyAggregate)


def test_repository_registry_auto_discover(monkeypatch) -> None:
    registry = RepositoryRegistry()

    class AutoRepo:
        __aggregate_type__ = DummyAggregate

        def __init__(self, session):  # pragma: no cover - simple passthrough
            self.session = session

    module_name = "tests.fake_repositories"
    fake_module = ModuleType(module_name)
    fake_module.AutoRepo = AutoRepo  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, module_name, fake_module)

    registry.auto_discover([module_name])
    factory = registry.get_factory(DummyAggregate)
    repo_instance = factory("session-object")

    assert isinstance(repo_instance, AutoRepo)
    assert repo_instance.session == "session-object"

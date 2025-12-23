# src/loms/runtime/wiring.py
"""LOMS vNext - Runtime Wiring (Composition Root).

Responsibility:
- Load settings
- Instantiate container
- Register modules in dependency order
- Perform startup "gates" (contracts-as-code validation, migrations check, etc.)
- Expose built artifacts (FastAPI app, workers) via container lookups

This is intentionally "application-specific" wiring; reusable primitives live in shared/platform.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from loms.bootstrap.registry import Container, ModuleRegistry, build_default_registry


# ----- A very small container implementation (replace with your Bento container) -----
class DictContainer:
    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    def set(self, key: str, value: object) -> None:
        self._store[key] = value

    def get(self, key: str) -> object:
        if key not in self._store:
            raise KeyError(f"Container key not found: {key}")
        return self._store[key]


# ----- Settings -----


@dataclass(frozen=True)
class AppSettings:
    """Keep this minimal; real settings usually live in shared/platform/config.

    You can migrate to pydantic-settings later:
    - from pydantic_settings import BaseSettings
    """

    service_name: str = "loms-vnext"
    environment: str = "local"  # local/dev/stage/prod
    # DB / messaging / observability configs go here or in shared/platform settings.


def load_settings() -> AppSettings:
    """Replace with real env parsing (pydantic-settings recommended)."""
    # Example placeholder:
    return AppSettings()


# ----- Gates (Contracts-as-Code, schema validation, etc.) -----


def run_startup_gates(*, settings: AppSettings, container: Container) -> None:
    """Run gates that must pass before the service starts.

    Typical gates:
    - Validate OpenAPI files + examples
    - Validate event schemas + examples
    - Ensure DB migrations are up to date (optional in dev)
    - Verify required topics/streams exist (optional / env-dependent)
    """
    from pathlib import Path

    # Register settings so gates can access them
    container.set("settings", settings)

    # Skip gates in local environment for faster startup
    if settings.environment == "local":
        return

    # Gate 1: Validate contracts are loadable (reason codes, state machines, etc.)
    try:
        from loms.shared.contracts.loader import ContractLoader
        project_root = Path(".")
        contracts = ContractLoader.load_from_dir(str(project_root))
        # Verify reason codes loaded
        if contracts["reason_codes"] is None:
            raise RuntimeError("reason_codes not loaded")
    except Exception as e:
        raise RuntimeError(f"Startup gate failed: contracts validation - {e}") from e

    # Gate 2: Event schema validation (uses Bento's EventSchemaRegistry if needed)
    # Currently skipped - can be enabled when event schemas are defined


# ----- Wiring orchestration -----


@dataclass(frozen=True)
class WiredRuntime:
    """Return object for convenience in entrypoints/tests."""

    settings: AppSettings
    container: Container
    registry: ModuleRegistry
    module_order: list[str]


def build_runtime(
    *,
    registry: ModuleRegistry | None = None,
    extra_modules: Iterable[Any] = (),
) -> WiredRuntime:
    """
    Build the runtime:
    1) settings
    2) container
    3) module registry (default if not provided)
    4) gates
    5) module registrations.

    extra_modules:
    - reserved for future plugin overrides; keep it empty for now.
    """
    settings = load_settings()
    container: Container = DictContainer()

    reg = registry or build_default_registry()

    # Run gates before modules register, so we fail fast (contracts broken, etc.)
    run_startup_gates(settings=settings, container=container)

    # Register modules in deterministic dependency order
    modules = reg.build_modules_in_order()
    module_order = [m.name for m in modules]

    for m in modules:
        m.register(container)

    # Optional: register extra modules (feature flags/plugins) after core wiring
    for mod in extra_modules:
        # If you support this, enforce it implements Module
        mod.register(container)

    return WiredRuntime(
        settings=settings,
        container=container,
        registry=reg,
        module_order=module_order,
    )


# ----- Convenience accessors for entrypoints -----


def get_fastapi_app(container: Container) -> Any:
    """
    Expectation:
    - InfraModule registers a FastAPI app or an app factory under a known key.
    - Context modules register routers under known keys or directly attach to app.

    Choose one pattern and keep it consistent.
    """
    return container.get("http.app")


def get_outbox_worker(container: Container) -> Any:
    return container.get("worker.outbox")


def get_replay_runner(container: Container) -> Any:
    return container.get("runner.replay")

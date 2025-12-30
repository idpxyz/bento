"""Tests for Bento Runtime module."""

from __future__ import annotations

import pytest

from bento.runtime import BentoContainer, BentoModule, ModuleRegistry, RuntimeBuilder

pytestmark = pytest.mark.asyncio


class TestBentoContainer:
    """Tests for BentoContainer."""

    def test_set_and_get(self):
        container = BentoContainer()
        container.set("key", "value")
        assert container.get("key") == "value"

    def test_get_with_default(self):
        container = BentoContainer()
        assert container.get("missing", "default") == "default"

    def test_get_missing_raises(self):
        container = BentoContainer()
        with pytest.raises(KeyError):
            container.get("missing")

    def test_has(self):
        container = BentoContainer()
        container.set("key", "value")
        assert container.has("key") is True
        assert container.has("missing") is False

    def test_set_factory(self):
        container = BentoContainer()
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return "lazy_value"

        container.set_factory("lazy", factory)

        # Factory not called yet
        assert call_count == 0

        # First access calls factory
        assert container.get("lazy") == "lazy_value"
        assert call_count == 1

        # Second access uses cached value
        assert container.get("lazy") == "lazy_value"
        assert call_count == 1

    def test_keys(self):
        container = BentoContainer()
        container.set("a", 1)
        container.set("b", 2)
        assert set(container.keys()) == {"a", "b"}

    def test_clear(self):
        container = BentoContainer()
        container.set("key", "value")
        container.clear()
        assert container.has("key") is False


class TestModuleRegistry:
    """Tests for ModuleRegistry."""

    def test_register_module(self):
        class TestModule(BentoModule):
            name = "test"

        registry = ModuleRegistry()
        registry.register(TestModule())
        assert registry.has("test")

    def test_register_duplicate_raises(self):
        class TestModule(BentoModule):
            name = "test"

        registry = ModuleRegistry()
        registry.register(TestModule())

        with pytest.raises(ValueError, match="already registered"):
            registry.register(TestModule())

    def test_resolve_order_simple(self):
        class ModuleA(BentoModule):
            name = "a"

        class ModuleB(BentoModule):
            name = "b"
            requires = ["a"]

        registry = ModuleRegistry()
        registry.register(ModuleB())
        registry.register(ModuleA())

        order = registry.resolve_order()
        names = [m.name for m in order]
        assert names.index("a") < names.index("b")

    def test_resolve_order_complex(self):
        class ModuleA(BentoModule):
            name = "a"

        class ModuleB(BentoModule):
            name = "b"
            requires = ["a"]

        class ModuleC(BentoModule):
            name = "c"
            requires = ["a", "b"]

        registry = ModuleRegistry()
        registry.register(ModuleC())
        registry.register(ModuleA())
        registry.register(ModuleB())

        order = registry.resolve_order()
        names = [m.name for m in order]

        assert names.index("a") < names.index("b")
        assert names.index("b") < names.index("c")

    def test_missing_dependency_raises(self):
        class ModuleA(BentoModule):
            name = "a"
            requires = ["missing"]

        registry = ModuleRegistry()
        registry.register(ModuleA())

        with pytest.raises(ValueError, match="requires 'missing'"):
            registry.resolve_order()

    def test_circular_dependency_raises(self):
        class ModuleA(BentoModule):
            name = "a"
            requires = ["b"]

        class ModuleB(BentoModule):
            name = "b"
            requires = ["a"]

        registry = ModuleRegistry()
        registry.register(ModuleA())
        registry.register(ModuleB())

        with pytest.raises(ValueError, match="Circular"):
            registry.resolve_order()


class TestBentoModule:
    """Tests for BentoModule."""

    def test_auto_name(self):
        class CatalogModule(BentoModule):
            pass

        module = CatalogModule()
        assert module.name == "catalog"

    def test_explicit_name(self):
        class TestModule(BentoModule):
            name = "my-custom-name"

        module = TestModule()
        assert module.name == "my-custom-name"

    async def test_lifecycle_hooks(self):
        events = []

        class TestModule(BentoModule):
            name = "test"

            async def on_register(self, container):
                events.append("register")

            async def on_startup(self, container):
                events.append("startup")

            async def on_shutdown(self, container):
                events.append("shutdown")

        module = TestModule()
        container = BentoContainer()

        await module.on_register(container)
        await module.on_startup(container)
        await module.on_shutdown(container)

        assert events == ["register", "startup", "shutdown"]


class TestBentoRuntime:
    """Tests for BentoRuntime."""

    async def test_build_with_modules(self):
        registered = []

        class ModuleA(BentoModule):
            name = "a"

            async def on_register(self, container):
                registered.append("a")

        class ModuleB(BentoModule):
            name = "b"
            requires = ["a"]

            async def on_register(self, container):
                registered.append("b")

        runtime = RuntimeBuilder().with_modules(ModuleA(), ModuleB()).build_runtime()
        await runtime.build_async()

        # Should be registered in dependency order
        assert registered == ["a", "b"]

    async def test_container_access(self):
        class TestModule(BentoModule):
            name = "test"

            async def on_register(self, container):
                container.set("test.value", 42)

        runtime = RuntimeBuilder().with_modules(TestModule()).build_runtime()
        await runtime.build_async()

        assert runtime.container.get("test.value") == 42

    async def test_with_service(self):
        runtime = RuntimeBuilder().with_service("my.service", "my_value").build_runtime()
        await runtime.build_async()

        assert runtime.container.get("my.service") == "my_value"

    async def test_with_config(self):
        runtime = (
            RuntimeBuilder().with_config(service_name="my-app", environment="test").build_runtime()
        )
        await runtime.build_async()

        assert runtime.config.service_name == "my-app"
        assert runtime.config.environment == "test"

    async def test_create_fastapi_app(self):
        class TestModule(BentoModule):
            name = "test"

            def get_routers(self):
                from fastapi import APIRouter

                router = APIRouter(prefix="/test")

                @router.get("/hello")
                async def hello():
                    return {"message": "hello"}

                return [router]

        runtime = RuntimeBuilder().with_modules(TestModule()).build_runtime()
        app = runtime.create_fastapi_app(title="Test API")

        assert app.title == "Test API"

        # Check routes exist
        routes = [r.path for r in app.routes]
        assert "/health" in routes
        assert "/test/hello" in routes

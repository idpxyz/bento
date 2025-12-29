"""Mock factories and classes for testing."""

from typing import Any


class MockRepository:
    """Auto-generated mock repository for testing."""

    def __init__(self, initial_data: list[Any] | None = None):
        self._data: dict[str, Any] = {}
        self._id_counter = 0
        if initial_data:
            for item in initial_data:
                self._data[str(self._id_counter)] = item
                self._id_counter += 1

    async def get(self, id: str) -> Any | None:
        """Get item by ID."""
        return self._data.get(id)

    async def save(self, aggregate: Any) -> Any:
        """Save item."""
        id_str = str(getattr(aggregate, "id", self._id_counter))
        self._data[id_str] = aggregate
        self._id_counter += 1
        return aggregate

    async def delete(self, id: str) -> None:
        """Delete item."""
        self._data.pop(id, None)

    async def find_all(self, specification: Any | None = None) -> list[Any]:
        """Find all items."""
        return list(self._data.values())

    async def list(self, specification: Any | None = None) -> list[Any]:
        """List items (alias for find_all)."""
        return await self.find_all(specification)

    async def count(self, specification: Any | None = None) -> int:
        """Count items."""
        return len(self._data)

    def clear(self) -> None:
        """Clear all items."""
        self._data.clear()
        self._id_counter = 0

    def get_all_data(self) -> dict[str, Any]:
        """Get all data for assertions."""
        return self._data.copy()


class MockHandler:
    """Auto-generated mock handler for testing."""

    def __init__(self, return_value: Any = None):
        self.return_value = return_value
        self.calls: list[Any] = []
        self.last_call: Any = None

    async def validate(self, request: Any) -> None:
        """Mock validation (always passes)."""
        pass

    async def handle(self, request: Any) -> Any:
        """Mock handle method."""
        self.calls.append(request)
        self.last_call = request
        return self.return_value

    async def execute(self, request: Any) -> Any:
        """Mock execute method."""
        await self.validate(request)
        return await self.handle(request)

    def get_calls(self) -> list[Any]:
        """Get all calls for assertions."""
        return self.calls.copy()

    def reset(self) -> None:
        """Reset call history."""
        self.calls.clear()
        self.last_call = None


class MockService:
    """Auto-generated mock service for testing."""

    def __init__(self, methods: dict[str, Any] | None = None):
        self._methods = methods or {}
        self._calls: dict[str, list[Any]] = {}

    def __getattr__(self, method_name: str) -> Any:
        """Dynamically create mock methods."""
        if method_name.startswith("_"):
            raise AttributeError(f"No attribute {method_name}")

        if method_name not in self._calls:
            self._calls[method_name] = []

        async def mock_method(*args: Any, **kwargs: Any) -> Any:
            self._calls[method_name].append((args, kwargs))
            return self._methods.get(method_name)

        return mock_method

    def get_calls(self, method_name: str) -> list[tuple[Any, Any]]:
        """Get calls for a specific method."""
        return self._calls.get(method_name, []).copy()

    def reset(self) -> None:
        """Reset call history."""
        self._calls.clear()


class MockRepositoryFactory:
    """Factory for creating mock repositories."""

    @staticmethod
    def create(initial_data: list[Any] | None = None) -> Any:
        """Create a mock repository.

        Args:
            initial_data: Initial data to populate

        Returns:
            Mock repository instance
        """

        class MockRepository:
            """Auto-generated mock repository."""

            def __init__(self, data: list[Any] | None = None):
                self._data: dict[str, Any] = {}
                self._id_counter = 0
                if data:
                    for item in data:
                        self._data[str(self._id_counter)] = item
                        self._id_counter += 1

            async def get(self, id: str) -> Any | None:
                """Get item by ID."""
                return self._data.get(id)

            async def save(self, aggregate: Any) -> Any:
                """Save item."""
                id_str = str(getattr(aggregate, "id", self._id_counter))
                self._data[id_str] = aggregate
                self._id_counter += 1
                return aggregate

            async def delete(self, id: str) -> None:
                """Delete item."""
                self._data.pop(id, None)

            async def find_all(self, spec: Any | None = None) -> list[Any]:
                """Find all items."""
                return list(self._data.values())

            async def count(self, spec: Any | None = None) -> int:
                """Count items."""
                return len(self._data)

            def clear(self) -> None:
                """Clear all items."""
                self._data.clear()

        return MockRepository(initial_data)


class MockHandlerFactory:
    """Factory for creating mock handlers."""

    @staticmethod
    def create(return_value: Any = None) -> Any:
        """Create a mock handler.

        Args:
            return_value: Value to return from execute

        Returns:
            Mock handler instance
        """

        class MockHandler:
            """Auto-generated mock handler."""

            def __init__(self, value: Any = None):
                self.return_value = value
                self.calls: list[Any] = []

            async def validate(self, request: Any) -> None:
                """Mock validation."""
                pass

            async def handle(self, request: Any) -> Any:
                """Mock handle."""
                self.calls.append(request)
                return self.return_value

            async def execute(self, request: Any) -> Any:
                """Mock execute."""
                await self.validate(request)
                return await self.handle(request)

            def get_calls(self) -> list[Any]:
                """Get all calls."""
                return self.calls.copy()

        return MockHandler(return_value)


class MockServiceFactory:
    """Factory for creating mock services."""

    @staticmethod
    def create(methods: dict[str, Any] | None = None) -> Any:
        """Create a mock service.

        Args:
            methods: Dictionary of method_name -> return_value

        Returns:
            Mock service instance
        """

        class MockService:
            """Auto-generated mock service."""

            def __init__(self, method_map: dict[str, Any] | None = None):
                self._methods = method_map or {}
                self._calls: dict[str, list[Any]] = {}

            def __getattr__(self, name: str) -> Any:
                """Dynamically create mock methods."""
                if name.startswith("_"):
                    raise AttributeError(f"No attribute {name}")

                if name not in self._calls:
                    self._calls[name] = []

                async def mock_method(*args: Any, **kwargs: Any) -> Any:
                    self._calls[name].append((args, kwargs))
                    return self._methods.get(name)

                return mock_method

            def get_calls(self, method_name: str) -> list[Any]:
                """Get calls for a method."""
                return self._calls.get(method_name, []).copy()

        return MockService(methods)

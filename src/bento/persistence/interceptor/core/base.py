"""Base interceptor infrastructure for handling cross-cutting concerns.

This module provides the foundation for the interceptor pattern implementation,
allowing separation of cross-cutting concerns from core business logic.

Key Components:
- Interceptor: Base class for all interceptors
- InterceptorChain: Manages execution of multiple interceptors
- Metadata registry for entity-specific configuration
"""

from collections.abc import Awaitable, Callable
from typing import Any, ClassVar

from .types import InterceptorContext, InterceptorPriority


class Interceptor[T]:
    """Base class for all interceptors.

    Interceptors implement the chain of responsibility pattern to handle
    cross-cutting concerns like auditing, caching, logging, etc.

    Each interceptor can:
    - Process entities before operations
    - Process results after operations
    - Handle errors
    - Transform data
    - Execute side effects
    """

    # Interceptor type identifier for configuration
    interceptor_type: ClassVar[str] = ""

    @property
    def priority(self) -> InterceptorPriority:
        """Get interceptor priority.

        Lower priority number means higher precedence.

        Returns:
            Interceptor priority
        """
        return InterceptorPriority.NORMAL

    @classmethod
    def is_enabled_in_config(cls, config: Any) -> bool:
        """Check if interceptor is enabled in configuration.

        Args:
            config: Interceptor configuration

        Returns:
            True if enabled
        """
        return True

    def is_enabled_for_entity(self, entity_type: type[T]) -> bool:
        """Check if interceptor is enabled for specific entity type.

        Args:
            entity_type: Entity type to check

        Returns:
            True if enabled for this entity type
        """
        # Default: enabled for all entities
        # Subclasses can override with metadata registry checks
        return True

    def has_field(self, entity: Any, field_name: str) -> bool:
        """Check if entity has a specific field.

        Args:
            entity: Entity instance
            field_name: Field name to check

        Returns:
            True if field exists
        """
        return hasattr(entity, field_name)

    def get_field_value(self, entity: Any, field_name: str, default: Any = None) -> Any:
        """Get field value from entity.

        Args:
            entity: Entity instance
            field_name: Field name
            default: Default value if field doesn't exist

        Returns:
            Field value or default
        """
        return getattr(entity, field_name, default)

    def set_field_value(self, entity: Any, field_name: str, value: Any) -> None:
        """Set field value on entity.

        Args:
            entity: Entity instance
            field_name: Field name
            value: Value to set
        """
        setattr(entity, field_name, value)

    async def before_operation(
        self,
        context: InterceptorContext[T],
        next_interceptor: Callable[[InterceptorContext[T]], Awaitable[Any]],
    ) -> Any:
        """Process before operation execution.

        Args:
            context: Interceptor context
            next_interceptor: Next interceptor in chain

        Returns:
            Result from next interceptor
        """
        return await next_interceptor(context)

    async def after_operation(
        self,
        context: InterceptorContext[T],
        result: Any,
        next_interceptor: Callable[[InterceptorContext[T], Any], Awaitable[Any]],
    ) -> Any:
        """Process after operation execution.

        Args:
            context: Interceptor context
            result: Operation result
            next_interceptor: Next interceptor in chain

        Returns:
            Processed result
        """
        return await next_interceptor(context, result)

    async def on_error(
        self,
        context: InterceptorContext[T],
        error: Exception,
        next_interceptor: Callable[[InterceptorContext[T], Exception], Awaitable[Any]],
    ) -> Any:
        """Handle errors during operation.

        Args:
            context: Interceptor context
            error: Exception that occurred
            next_interceptor: Next error handler in chain

        Returns:
            Result from next handler
        """
        return await next_interceptor(context, error)

    async def process_result(
        self,
        context: InterceptorContext[T],
        result: T,
        next_interceptor: Callable[[InterceptorContext[T], T], Awaitable[T]],
    ) -> T:
        """Process operation result.

        Args:
            context: Interceptor context
            result: Operation result
            next_interceptor: Next processor in chain

        Returns:
            Processed result
        """
        return await next_interceptor(context, result)

    async def handle_exception(
        self,
        context: InterceptorContext[T],
        error: Exception,
        next_interceptor: Callable[[InterceptorContext[T], Exception], Awaitable[Any]],
    ) -> Any:
        """Handle exceptions.

        Can transform, wrap, or swallow exceptions.
        Returning None indicates exception was handled and should not propagate.
        Returning an exception continues propagation.

        Args:
            context: Interceptor context
            error: Original exception
            next_interceptor: Next exception handler

        Returns:
            Processed exception or None
        """
        return await self.on_error(context, error, next_interceptor)

    async def process_batch_results(
        self,
        context: InterceptorContext[T],
        results: list[T],
        next_interceptor: Callable[[InterceptorContext[T], list[T]], Awaitable[list[T]]],
    ) -> list[T]:
        """Process batch operation results.

        Default implementation processes each result individually.
        Subclasses can override for batch-optimized processing.

        Args:
            context: Interceptor context
            results: List of operation results
            next_interceptor: Next processor in chain

        Returns:
            Processed results
        """
        processed_results = []
        for result in results:
            # Create context for individual entity
            entity_context = InterceptorContext(
                session=context.session,
                entity_type=context.entity_type,
                operation=context.operation,
                entity=result,
                actor=context.actor,
                config=context.config,
                context_data=context.context_data.copy(),
            )

            async def single_next(ctx: InterceptorContext[T], res: T) -> T:
                return res

            processed_result = await self.process_result(entity_context, result, single_next)
            processed_results.append(processed_result)

        return processed_results

    async def publish_event(self, event_type: str, event_data: dict[str, Any]) -> None:
        """Publish an event.

        Args:
            event_type: Type of event
            event_data: Event payload
        """
        # Default implementation is no-op
        # Subclasses can override to publish to event bus
        pass


class InterceptorChain[T]:
    """Manages execution of multiple interceptors in a chain.

    Interceptors are executed in priority order, with lower priority
    numbers executing first.
    """

    def __init__(self, interceptors: list[Interceptor[T]] | None = None) -> None:
        """Initialize interceptor chain.

        Args:
            interceptors: List of interceptors to include in chain
        """
        self._interceptors = sorted(
            interceptors or [],
            key=lambda i: (i.priority, id(i)),  # Sort by priority, then by ID for stability
        )

    def add_interceptor(self, interceptor: Interceptor[T]) -> None:
        """Add an interceptor to the chain.

        Args:
            interceptor: Interceptor to add
        """
        self._interceptors.append(interceptor)
        self._interceptors.sort(key=lambda i: (i.priority, id(i)))

    def remove_interceptor(self, interceptor: Interceptor[T]) -> None:
        """Remove an interceptor from the chain.

        Args:
            interceptor: Interceptor to remove
        """
        if interceptor in self._interceptors:
            self._interceptors.remove(interceptor)

    async def execute_before(self, context: InterceptorContext[T]) -> Any:
        """Execute before_operation chain.

        Args:
            context: Interceptor context

        Returns:
            Final result after all interceptors
        """

        async def build_chain(index: int) -> Callable[[InterceptorContext[T]], Awaitable[Any]]:
            if index >= len(self._interceptors):
                # Terminal case: return no-op
                async def terminal(ctx: InterceptorContext[T]) -> None:
                    return None

                return terminal

            interceptor = self._interceptors[index]
            next_fn = await build_chain(index + 1)

            async def wrapper(ctx: InterceptorContext[T]) -> Any:
                return await interceptor.before_operation(ctx, next_fn)

            return wrapper

        chain = await build_chain(0)
        return await chain(context)

    async def execute_after(self, context: InterceptorContext[T], result: Any) -> Any:
        """Execute after_operation chain.

        Args:
            context: Interceptor context
            result: Operation result

        Returns:
            Processed result
        """

        async def build_chain(index: int) -> Callable[[InterceptorContext[T], Any], Awaitable[Any]]:
            if index >= len(self._interceptors):
                # Terminal case: return result as-is
                async def terminal(ctx: InterceptorContext[T], res: Any) -> Any:
                    return res

                return terminal

            interceptor = self._interceptors[index]
            next_fn = await build_chain(index + 1)

            async def wrapper(ctx: InterceptorContext[T], res: Any) -> Any:
                return await interceptor.after_operation(ctx, res, next_fn)

            return wrapper

        chain = await build_chain(0)
        return await chain(context, result)

    async def execute_on_error(self, context: InterceptorContext[T], error: Exception) -> Any:
        """Execute on_error chain.

        Args:
            context: Interceptor context
            error: Exception that occurred

        Returns:
            Processed error or None
        """

        async def build_chain(
            index: int,
        ) -> Callable[[InterceptorContext[T], Exception], Awaitable[Any]]:
            if index >= len(self._interceptors):
                # Terminal case: re-raise error
                async def terminal(ctx: InterceptorContext[T], err: Exception) -> None:
                    raise err

                return terminal

            interceptor = self._interceptors[index]
            next_fn = await build_chain(index + 1)

            async def wrapper(ctx: InterceptorContext[T], err: Exception) -> Any:
                return await interceptor.on_error(ctx, err, next_fn)

            return wrapper

        chain = await build_chain(0)
        try:
            return await chain(context, error)
        except Exception:
            # If exception is raised, return it
            raise

    async def process_result(self, context: InterceptorContext[T], result: T) -> T:
        """Process a single result through the chain.

        Args:
            context: Interceptor context
            result: Result to process

        Returns:
            Processed result
        """

        async def build_chain(index: int) -> Callable[[InterceptorContext[T], T], Awaitable[T]]:
            if index >= len(self._interceptors):
                # Terminal case: return result as-is
                async def terminal(ctx: InterceptorContext[T], res: T) -> T:
                    return res

                return terminal

            interceptor = self._interceptors[index]
            next_fn = await build_chain(index + 1)

            async def wrapper(ctx: InterceptorContext[T], res: T) -> T:
                return await interceptor.process_result(ctx, res, next_fn)

            return wrapper

        chain = await build_chain(0)
        return await chain(context, result)

    async def process_batch_results(
        self, context: InterceptorContext[T], results: list[T]
    ) -> list[T]:
        """Process batch results through the chain.

        Args:
            context: Interceptor context
            results: Results to process

        Returns:
            Processed results
        """

        async def build_chain(
            index: int,
        ) -> Callable[[InterceptorContext[T], list[T]], Awaitable[list[T]]]:
            if index >= len(self._interceptors):
                # Terminal case: return results as-is
                async def terminal(ctx: InterceptorContext[T], res: list[T]) -> list[T]:
                    return res

                return terminal

            interceptor = self._interceptors[index]
            next_fn = await build_chain(index + 1)

            async def wrapper(ctx: InterceptorContext[T], res: list[T]) -> list[T]:
                return await interceptor.process_batch_results(ctx, res, next_fn)

            return wrapper

        chain = await build_chain(0)
        return await chain(context, results)

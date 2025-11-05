"""Interceptor factory for building interceptor chains.

This module provides factory functions for creating and configuring
interceptor chains based on configuration.
"""

from typing import Any, TypeVar

from .core import Interceptor, InterceptorChain
from .impl import AuditInterceptor, OptimisticLockInterceptor, SoftDeleteInterceptor

T = TypeVar("T")


class InterceptorConfig:
    """Configuration for interceptors.

    Attributes:
        enable_audit: Enable audit interceptor
        enable_soft_delete: Enable soft delete interceptor
        enable_optimistic_lock: Enable optimistic lock interceptor
        actor: Current actor/user for operations
    """

    def __init__(
        self,
        *,
        enable_audit: bool = True,
        enable_soft_delete: bool = True,
        enable_optimistic_lock: bool = True,
        actor: str | None = None,
    ) -> None:
        """Initialize interceptor configuration.

        Args:
            enable_audit: Enable audit interceptor
            enable_soft_delete: Enable soft delete interceptor
            enable_optimistic_lock: Enable optimistic lock interceptor
            actor: Current actor/user for operations
        """
        self.enable_audit = enable_audit
        self.enable_soft_delete = enable_soft_delete
        self.enable_optimistic_lock = enable_optimistic_lock
        self.actor = actor or "system"


class InterceptorFactory:
    """Factory for creating interceptor chains.

    This factory creates interceptor chains with standard interceptors
    based on configuration.

    Example:
        ```python
        # Create factory with configuration
        factory = InterceptorFactory(
            InterceptorConfig(
                enable_audit=True,
                enable_soft_delete=True,
                actor="user@example.com"
            )
        )

        # Build interceptor chain
        chain = factory.build_chain()
        ```
    """

    def __init__(self, config: InterceptorConfig | None = None) -> None:
        """Initialize interceptor factory.

        Args:
            config: Interceptor configuration
        """
        self._config = config or InterceptorConfig()

    def build_chain(
        self, additional_interceptors: list[Interceptor[Any]] | None = None
    ) -> InterceptorChain[Any]:
        """Build interceptor chain with configured interceptors.

        Args:
            additional_interceptors: Additional custom interceptors to include

        Returns:
            Configured interceptor chain
        """
        interceptors: list[Interceptor[Any]] = []

        # Add standard interceptors based on configuration
        if self._config.enable_audit:
            interceptors.append(AuditInterceptor(actor=self._config.actor))

        if self._config.enable_soft_delete:
            interceptors.append(SoftDeleteInterceptor(actor=self._config.actor))

        if self._config.enable_optimistic_lock:
            interceptors.append(OptimisticLockInterceptor(config=self._config))

        # Add any additional custom interceptors
        if additional_interceptors:
            interceptors.extend(additional_interceptors)

        return InterceptorChain(interceptors)

    def build_audit_chain(self) -> InterceptorChain[Any]:
        """Build chain with only audit interceptor.

        Returns:
            Interceptor chain with audit only
        """
        return InterceptorChain([AuditInterceptor(actor=self._config.actor)])

    def build_soft_delete_chain(self) -> InterceptorChain[Any]:
        """Build chain with only soft delete interceptor.

        Returns:
            Interceptor chain with soft delete only
        """
        return InterceptorChain([SoftDeleteInterceptor(actor=self._config.actor)])

    def build_optimistic_lock_chain(self) -> InterceptorChain[Any]:
        """Build chain with only optimistic lock interceptor.

        Returns:
            Interceptor chain with optimistic lock only
        """
        return InterceptorChain([OptimisticLockInterceptor(config=self._config)])

    def create_custom_chain(self, interceptors: list[Interceptor[Any]]) -> InterceptorChain[Any]:
        """Create a custom interceptor chain.

        Args:
            interceptors: List of interceptors to include

        Returns:
            Custom interceptor chain
        """
        return InterceptorChain(interceptors)


# Convenience function for creating a default chain
def create_default_chain(actor: str | None = None) -> InterceptorChain[Any]:
    """Create a default interceptor chain with all standard interceptors.

    Args:
        actor: Current actor/user for operations

    Returns:
        Default interceptor chain
    """
    config = InterceptorConfig(actor=actor)
    factory = InterceptorFactory(config)
    return factory.build_chain()

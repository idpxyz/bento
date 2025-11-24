"""Interceptor factory for building interceptor chains.

This module provides factory functions for creating and configuring
interceptor chains based on configuration.
"""

from typing import Any, TypeVar

from bento.application.ports.cache import Cache

from .core import Interceptor, InterceptorChain
from .impl import (
    AuditInterceptor,
    CacheInterceptor,
    OptimisticLockInterceptor,
    SoftDeleteInterceptor,
)

T = TypeVar("T")


class InterceptorConfig:
    """Configuration for interceptors.

    Attributes:
        enable_audit: Enable audit interceptor
        enable_soft_delete: Enable soft delete interceptor
        enable_optimistic_lock: Enable optimistic lock interceptor
        enable_cache: Enable cache interceptor
        cache: Cache instance
        cache_ttl_seconds: Default cache TTL in seconds
        cache_prefix: Cache key prefix

        # Cache optimizations (Phase 1 improvements)
        enable_singleflight: Enable Singleflight (prevent cache breakdown)
        singleflight_timeout: Singleflight timeout in seconds
        enable_jitter: Enable TTL jitter (prevent cache avalanche)
        jitter_range: TTL jitter range (±percentage)
        enable_null_cache: Enable null value caching (prevent cache penetration)
        null_cache_ttl: Null value cache TTL in seconds
        fail_open: Enable fail-open mode (degrade on cache failure)
        cache_timeout: Cache operation timeout in seconds

        actor: Current actor/user for operations
    """

    def __init__(
        self,
        *,
        enable_audit: bool = True,
        enable_soft_delete: bool = True,
        enable_optimistic_lock: bool = True,
        enable_cache: bool = False,
        cache: Cache | None = None,
        cache_ttl_seconds: int = 300,
        cache_prefix: str | None = None,
        # Cache optimization parameters (Phase 1)
        enable_singleflight: bool = True,  # Prevent cache breakdown
        singleflight_timeout: float = 5.0,  # Singleflight timeout in seconds
        enable_jitter: bool = True,  # Enable TTL jitter (prevent cache avalanche)
        jitter_range: float = 0.1,  # TTL jitter range (±percentage)
        enable_null_cache: bool = True,  # Enable null value caching (prevent cache penetration)
        null_cache_ttl: int = 10,  # Null value cache TTL in seconds
        fail_open: bool = True,  # Enable fail-open mode (degrade on cache failure)
        cache_timeout: float = 0.1,  # Cache operation timeout in seconds
        actor: str | None = None,  # Current actor/user for operations
    ) -> None:
        """Initialize interceptor configuration.

        Args:
            enable_audit: Enable audit interceptor
            enable_soft_delete: Enable soft delete interceptor
            enable_optimistic_lock: Enable optimistic lock interceptor
            enable_cache: Enable cache interceptor
            cache: Cache instance (required if enable_cache=True)
            cache_ttl_seconds: Default cache TTL (default: 300s)
            cache_prefix: Cache key prefix (default: "")

            # Cache optimizations
            enable_singleflight: Enable Singleflight protection (default: True)
            singleflight_timeout: Singleflight timeout (default: 5.0s)
            enable_jitter: Enable TTL jitter (default: True)
            jitter_range: TTL jitter range ±% (default: 0.1 = ±10%)
            enable_null_cache: Enable null value caching (default: True)
            null_cache_ttl: Null value TTL (default: 10s)
            fail_open: Enable fail-open mode (default: True)
            cache_timeout: Cache operation timeout (default: 0.1s = 100ms)

            actor: Current actor/user for operations
        """
        self.enable_audit = enable_audit
        self.enable_soft_delete = enable_soft_delete
        self.enable_optimistic_lock = enable_optimistic_lock
        self.enable_cache = enable_cache
        self.cache = cache
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache_prefix = cache_prefix or ""

        # Cache optimization settings
        self.enable_singleflight = enable_singleflight
        self.singleflight_timeout = singleflight_timeout
        self.enable_jitter = enable_jitter
        self.jitter_range = jitter_range
        self.enable_null_cache = enable_null_cache
        self.null_cache_ttl = null_cache_ttl
        self.fail_open = fail_open
        self.cache_timeout = cache_timeout

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
        if self._config.enable_cache and self._config.cache:
            interceptors.append(
                CacheInterceptor(
                    self._config.cache,
                    ttl=self._config.cache_ttl_seconds,
                    enabled=True,
                    prefix=self._config.cache_prefix,
                    # Cache optimization parameters (Phase 1)
                    enable_singleflight=self._config.enable_singleflight,
                    singleflight_timeout=self._config.singleflight_timeout,
                    enable_jitter=self._config.enable_jitter,
                    jitter_range=self._config.jitter_range,
                    enable_null_cache=self._config.enable_null_cache,
                    null_cache_ttl=self._config.null_cache_ttl,
                    fail_open=self._config.fail_open,
                    cache_timeout=self._config.cache_timeout,
                )
            )

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

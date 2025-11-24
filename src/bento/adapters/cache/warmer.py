"""Cache warmer implementation.

This module provides the CacheWarmer class for warming up cache
using application-defined strategies.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from bento.application.ports.cache import Cache
from bento.application.ports.cache_warmup import CacheWarmupStrategy

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class WarmupStats:
    """Cache warmup statistics.

    Attributes:
        total_keys: Total number of keys to warmup
        warmed_keys: Number of successfully warmed keys
        failed_keys: Number of keys that failed to warmup
        skipped_keys: Number of keys skipped (no data)
        duration_seconds: Total duration in seconds
        errors: List of errors encountered
    """

    total_keys: int = 0
    warmed_keys: int = 0
    failed_keys: int = 0
    skipped_keys: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate.

        Returns:
            Success rate as percentage (0.0 to 1.0)
        """
        if self.total_keys == 0:
            return 0.0
        return self.warmed_keys / self.total_keys

    def __str__(self) -> str:
        """String representation of stats."""
        return (
            f"WarmupStats(total={self.total_keys}, "
            f"warmed={self.warmed_keys}, "
            f"failed={self.failed_keys}, "
            f"skipped={self.skipped_keys}, "
            f"duration={self.duration_seconds:.2f}s, "
            f"success_rate={self.success_rate:.1%})"
        )


class CacheWarmer:
    """Generic cache warmer.

    Provides mechanism for cache warmup with:
    - Batch processing
    - Concurrency control
    - Progress tracking
    - Error handling
    - Statistics collection

    The CacheWarmer is framework-provided machinery that executes
    application-defined strategies (CacheWarmupStrategy).

    Example:
        ```python
        # Framework provides the warmer
        warmer = CacheWarmer(
            cache,
            max_concurrency=10,
            default_ttl=3600
        )

        # Application provides the strategy
        strategy = HotProductsWarmupStrategy(product_service)

        # Execute warmup
        stats = await warmer.warmup(strategy)
        print(f"Warmed {stats.warmed_keys}/{stats.total_keys} keys")
        ```
    """

    def __init__(
        self,
        cache: Cache,
        *,
        max_concurrency: int = 10,
        batch_size: int = 100,
        default_ttl: int = 3600,
        enable_progress: bool = True,
    ) -> None:
        """Initialize cache warmer.

        Args:
            cache: Cache instance to warm up
            max_concurrency: Maximum concurrent warmup tasks
            batch_size: Batch size for processing (currently not used, for future optimization)
            default_ttl: Default TTL for warmed cache entries (seconds)
            enable_progress: Enable progress logging
        """
        self._cache = cache
        self._max_concurrency = max_concurrency
        self._batch_size = batch_size
        self._default_ttl = default_ttl
        self._enable_progress = enable_progress

    async def warmup(
        self,
        strategy: CacheWarmupStrategy[T],
        *,
        progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> WarmupStats:
        """Warmup cache using provided strategy.

        Args:
            strategy: Warmup strategy (application-provided)
            progress_callback: Optional callback(current, total) for progress tracking

        Returns:
            Warmup statistics

        Example:
            ```python
            async def on_progress(current: int, total: int):
                print(f"Progress: {current}/{total} ({current/total*100:.1f}%)")

            stats = await warmer.warmup(strategy, progress_callback=on_progress)
            ```
        """
        start_time = time.time()
        stats = WarmupStats()

        try:
            # Get keys from strategy (application logic)
            keys = await strategy.get_keys_to_warmup()
            stats.total_keys = len(keys)

            if self._enable_progress:
                logger.info(
                    f"Starting cache warmup: {len(keys)} keys "
                    f"(strategy: {strategy.__class__.__name__})"
                )

            if stats.total_keys == 0:
                logger.warning("No keys to warmup")
                return stats

            # Get TTL for this strategy
            ttl = strategy.get_ttl() if hasattr(strategy, "get_ttl") else None
            if ttl is None:
                ttl = self._default_ttl

            # Process keys with concurrency control
            semaphore = asyncio.Semaphore(self._max_concurrency)
            completed = 0

            async def warmup_key(key: str) -> None:
                nonlocal completed

                async with semaphore:
                    try:
                        # Load data using strategy (application logic)
                        data = await strategy.load_data(key)

                        if data is not None:
                            # Cache the data (framework mechanism)
                            await self._cache.set(key, data, ttl=ttl)
                            stats.warmed_keys += 1
                        else:
                            # Data not found or should not be cached
                            stats.skipped_keys += 1

                        completed += 1

                        # Progress callback
                        if progress_callback:
                            await progress_callback(completed, stats.total_keys)

                        # Log progress
                        if self._enable_progress and completed % 100 == 0:
                            logger.info(
                                f"Progress: {completed}/{stats.total_keys} "
                                f"({completed / stats.total_keys * 100:.1f}%)"
                            )

                    except Exception as e:
                        stats.failed_keys += 1
                        error_msg = f"Failed to warmup key '{key}': {e}"
                        stats.errors.append(error_msg)
                        logger.error(error_msg, exc_info=True)
                        completed += 1

            # Execute warmup tasks
            tasks = [warmup_key(key) for key in keys]
            await asyncio.gather(*tasks, return_exceptions=True)

            stats.duration_seconds = time.time() - start_time

            if self._enable_progress:
                logger.info(
                    f"Cache warmup completed: "
                    f"{stats.warmed_keys} warmed, "
                    f"{stats.skipped_keys} skipped, "
                    f"{stats.failed_keys} failed "
                    f"in {stats.duration_seconds:.2f}s "
                    f"(success rate: {stats.success_rate:.1%})"
                )

            return stats

        except Exception as e:
            stats.duration_seconds = time.time() - start_time
            error_msg = f"Warmup failed: {e}"
            stats.errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
            raise

    async def warmup_multiple(
        self,
        strategies: list[CacheWarmupStrategy[Any]],
        *,
        stop_on_error: bool = False,
    ) -> dict[str, WarmupStats]:
        """Warmup cache using multiple strategies.

        Strategies are executed sequentially in priority order
        (higher priority first).

        Args:
            strategies: List of warmup strategies
            stop_on_error: Stop execution if any strategy fails

        Returns:
            Dictionary mapping strategy name to its statistics

        Example:
            ```python
            strategies = [
                HotProductsWarmupStrategy(product_service),    # priority: 100
                RecommendationWarmupStrategy(rec_service),     # priority: 60
                CategoryCacheWarmupStrategy(category_service), # priority: 50
            ]

            results = await warmer.warmup_multiple(strategies)

            for name, stats in results.items():
                print(f"{name}: {stats}")
            ```
        """
        if not strategies:
            logger.warning("No strategies provided for warmup")
            return {}

        # Sort by priority (higher first)
        sorted_strategies = sorted(strategies, key=lambda s: s.get_priority(), reverse=True)

        logger.info(f"Executing {len(sorted_strategies)} warmup strategies in priority order")

        results: dict[str, WarmupStats] = {}

        for strategy in sorted_strategies:
            strategy_name = strategy.__class__.__name__
            priority = strategy.get_priority()

            logger.info(f"Executing warmup strategy: {strategy_name} (priority: {priority})")

            try:
                stats = await self.warmup(strategy)
                results[strategy_name] = stats

                if stop_on_error and stats.failed_keys > 0:
                    logger.error(f"Stopping warmup: strategy {strategy_name} had failures")
                    break

            except Exception as e:
                logger.error(f"Strategy {strategy_name} failed: {e}", exc_info=True)

                # Create error stats
                error_stats = WarmupStats()
                error_stats.errors.append(str(e))
                results[strategy_name] = error_stats

                if stop_on_error:
                    logger.error("Stopping warmup due to strategy failure")
                    break

        # Summary
        total_warmed = sum(s.warmed_keys for s in results.values())
        total_keys = sum(s.total_keys for s in results.values())
        total_duration = sum(s.duration_seconds for s in results.values())

        logger.info(
            f"All strategies completed: "
            f"{total_warmed}/{total_keys} keys warmed "
            f"in {total_duration:.2f}s"
        )

        return results

    async def warmup_single_key(
        self,
        key: str,
        loader: Callable[[str], Awaitable[T]],
        *,
        ttl: int | None = None,
    ) -> bool:
        """Warmup a single cache key.

        Utility method for warming up individual keys without
        defining a full strategy.

        Args:
            key: Cache key to warmup
            loader: Async function to load data
            ttl: TTL for this key (uses default if None)

        Returns:
            True if successfully warmed, False otherwise

        Example:
            ```python
            async def load_product(key: str):
                product_id = key.split(":")[-1]
                return await product_service.get_by_id(product_id)

            success = await warmer.warmup_single_key(
                "Product:id:123",
                load_product,
                ttl=7200
            )
            ```
        """
        try:
            data = await loader(key)

            if data is not None:
                await self._cache.set(key, data, ttl=ttl or self._default_ttl)
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to warmup key '{key}': {e}", exc_info=True)
            return False

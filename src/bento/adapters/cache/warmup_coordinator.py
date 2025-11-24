"""Cache warmup coordinator (framework-provided).

This module provides a coordinator for managing multiple warmup strategies.
It's a higher-level abstraction over CacheWarmer.
"""

from __future__ import annotations

import logging
from typing import Any

from bento.adapters.cache.warmer import CacheWarmer, WarmupStats
from bento.application.ports.cache import Cache

logger = logging.getLogger(__name__)


class CacheWarmupCoordinator:
    """Cache warmup coordinator (framework layer).

    Responsibilities:
    1. Manage multiple warmup strategies from different parts of the application
    2. Coordinate execution order (by priority)
    3. Collect and aggregate statistics
    4. Provide filtering capabilities (by tags)

    This is a technical infrastructure component with no business logic.
    Applications use tags/metadata to organize their strategies.

    Example:
        ```python
        # Framework provides the coordinator
        coordinator = CacheWarmupCoordinator(cache)

        # Application registers strategies with tags
        coordinator.register_strategy(
            ProductWarmupStrategy(...),
            tags=["catalog", "product"],
            metadata={"priority": "high"}
        )

        # Execute by tags
        await coordinator.warmup_by_tags(["catalog"])
        await coordinator.warmup_all()
        ```
    """

    def __init__(
        self,
        cache: Cache,
        *,
        max_concurrency: int = 20,
        default_ttl: int = 3600,
        enable_progress: bool = True,
    ):
        """Initialize coordinator.

        Args:
            cache: Cache instance
            max_concurrency: Maximum concurrent warmup tasks
            default_ttl: Default TTL in seconds
            enable_progress: Enable progress logging
        """
        self._warmer = CacheWarmer(
            cache,
            max_concurrency=max_concurrency,
            default_ttl=default_ttl,
            enable_progress=enable_progress,
        )
        self._strategies: list[Any] = []
        self._strategy_metadata: dict[str, dict] = {}

    def register_strategy(
        self,
        strategy: Any,
        *,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register a warmup strategy.

        Args:
            strategy: Warmup strategy instance
            tags: Tags for filtering (e.g., ["catalog", "product"])
            metadata: Additional metadata (e.g., {"owner": "team-a"})
        """
        self._strategies.append(strategy)

        strategy_name = strategy.__class__.__name__

        # Store metadata
        self._strategy_metadata[strategy_name] = {
            "tags": tags or [],
            "metadata": metadata or {},
            "priority": (strategy.get_priority() if hasattr(strategy, "get_priority") else 0),
        }

        tags_str = ", ".join(tags) if tags else "none"
        logger.info(
            f"Registered warmup strategy: {strategy_name} "
            f"(tags: {tags_str}, priority: {self._strategy_metadata[strategy_name]['priority']})"
        )

    async def warmup_all(self) -> dict[str, WarmupStats]:
        """Execute all registered strategies.

        Returns:
            Dictionary mapping strategy name to its statistics
        """
        if not self._strategies:
            logger.warning("No strategies registered")
            return {}

        logger.info("=" * 70)
        logger.info(f"🔥 Starting cache warmup, {len(self._strategies)} strategies")
        logger.info("=" * 70)

        # Execute warmup (automatically sorted by priority)
        results = await self._warmer.warmup_multiple(self._strategies)

        # Summary
        total_warmed = sum(s.warmed_keys for s in results.values())
        total_keys = sum(s.total_keys for s in results.values())
        total_duration = sum(s.duration_seconds for s in results.values())

        logger.info("")
        logger.info("✨ Cache warmup completed!")
        logger.info("-" * 70)
        logger.info(f"  🎯 Total: {total_warmed}/{total_keys} keys warmed")
        logger.info(f"  ⏱️  Duration: {total_duration:.2f}s")
        success_rate = total_warmed / total_keys * 100 if total_keys > 0 else 0
        logger.info(f"  🏆 Success rate: {success_rate:.1f}%")
        logger.info("=" * 70)

        return results

    async def warmup_by_tags(
        self,
        tags: list[str],
        *,
        match_all: bool = False,
    ) -> dict[str, WarmupStats]:
        """Execute strategies filtered by tags.

        Args:
            tags: Tags to filter by
            match_all: If True, strategy must have ALL tags.
                      If False, strategy must have ANY tag (default)

        Returns:
            Dictionary mapping strategy name to its statistics

        Example:
            ```python
            # Warmup all strategies with "catalog" tag
            await coordinator.warmup_by_tags(["catalog"])

            # Warmup strategies with both "catalog" AND "high-priority"
            await coordinator.warmup_by_tags(
                ["catalog", "high-priority"],
                match_all=True
            )
            ```
        """
        # Filter strategies by tags
        filtered_strategies = []

        for strategy in self._strategies:
            strategy_name = strategy.__class__.__name__
            strategy_tags = self._strategy_metadata.get(strategy_name, {}).get("tags", [])

            if match_all:
                # Must have ALL tags
                if all(tag in strategy_tags for tag in tags):
                    filtered_strategies.append(strategy)
            else:
                # Must have ANY tag
                if any(tag in strategy_tags for tag in tags):
                    filtered_strategies.append(strategy)

        if not filtered_strategies:
            logger.warning(f"No strategies found with tags: {tags}")
            return {}

        tags_str = " AND ".join(tags) if match_all else " OR ".join(tags)
        logger.info(
            f"🔄 Executing warmup for {len(filtered_strategies)} strategies (tags: {tags_str})"
        )

        results = await self._warmer.warmup_multiple(filtered_strategies)

        total_warmed = sum(s.warmed_keys for s in results.values())
        total_keys = sum(s.total_keys for s in results.values())

        logger.info(f"✅ Warmup completed: {total_warmed}/{total_keys} keys")

        return results

    def list_strategies(self) -> dict[str, dict]:
        """List all registered strategies.

        Returns:
            Dictionary mapping strategy name to its metadata
        """
        return self._strategy_metadata.copy()

    def get_strategies_by_tags(
        self,
        tags: list[str],
        *,
        match_all: bool = False,
    ) -> list[str]:
        """Get strategy names filtered by tags.

        Args:
            tags: Tags to filter by
            match_all: If True, must match ALL tags

        Returns:
            List of strategy names
        """
        result = []

        for name, metadata in self._strategy_metadata.items():
            strategy_tags = metadata.get("tags", [])

            if match_all:
                if all(tag in strategy_tags for tag in tags):
                    result.append(name)
            else:
                if any(tag in strategy_tags for tag in tags):
                    result.append(name)

        return result

    def get_warmer(self) -> CacheWarmer:
        """Get the underlying CacheWarmer instance.

        Returns:
            CacheWarmer instance
        """
        return self._warmer

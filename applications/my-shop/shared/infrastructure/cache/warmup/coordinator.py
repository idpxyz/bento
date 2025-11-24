"""跨上下文的缓存预热协调器（共享基础设施）.

职责：协调多个BC的预热策略，提供统一的预热入口
符合DDD原则：基础设施层服务，不包含业务逻辑
"""

from __future__ import annotations

import logging
from typing import Any

from bento.adapters.cache.warmer import CacheWarmer, WarmupStats
from bento.application.ports.cache import Cache

logger = logging.getLogger(__name__)


class CacheWarmupCoordinator:
    """缓存预热协调器（基础设施层）.

    职责：
    1. 管理来自多个BC的预热策略
    2. 协调预热执行顺序（按优先级）
    3. 收集和汇总预热统计
    4. 提供按上下文预热的能力

    不包含业务逻辑，只负责技术协调
    """

    def __init__(
        self,
        cache: Cache,
        *,
        max_concurrency: int = 20,
        default_ttl: int = 3600,
        enable_progress: bool = True,
    ):
        """初始化协调器.

        Args:
            cache: 缓存实例
            max_concurrency: 最大并发数
            default_ttl: 默认TTL（秒）
            enable_progress: 启用进度日志
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
        bc_name: str | None = None,
        description: str | None = None,
    ) -> None:
        """注册预热策略.

        Args:
            strategy: 预热策略实例（来自各个BC）
            bc_name: 所属BC名称（可选，用于按BC预热）
            description: 策略描述（可选）
        """
        self._strategies.append(strategy)

        # 保存元数据
        strategy_name = strategy.__class__.__name__
        self._strategy_metadata[strategy_name] = {
            "bc_name": bc_name,
            "description": description,
            "priority": strategy.get_priority() if hasattr(strategy, "get_priority") else 0,
        }

        logger.info(
            f"注册预热策略: {strategy_name} "
            f"(BC: {bc_name or 'Unknown'}, Priority: {self._strategy_metadata[strategy_name]['priority']})"
        )

    async def warmup_all(self) -> dict[str, WarmupStats]:
        """执行所有已注册策略的预热.

        Returns:
            预热统计结果字典
        """
        if not self._strategies:
            logger.warning("没有已注册的预热策略")
            return {}

        logger.info("=" * 70)
        logger.info(f"🔥 开始执行缓存预热，共 {len(self._strategies)} 个策略")
        logger.info("=" * 70)

        # 使用CacheWarmer执行预热（自动按优先级排序）
        results = await self._warmer.warmup_multiple(self._strategies)

        # 统计汇总
        total_warmed = sum(s.warmed_keys for s in results.values())
        total_keys = sum(s.total_keys for s in results.values())
        total_duration = sum(s.duration_seconds for s in results.values())

        logger.info("")
        logger.info("✨ 缓存预热完成！")
        logger.info("-" * 70)
        logger.info(f"  🎯 总计: {total_warmed}/{total_keys} 个键已预热")
        logger.info(f"  ⏱️  总耗时: {total_duration:.2f}s")
        logger.info(
            f"  🏆 总成功率: {total_warmed / total_keys * 100 if total_keys > 0 else 0:.1f}%"
        )
        logger.info("=" * 70)

        return results

    async def warmup_by_bc(self, bc_name: str) -> dict[str, WarmupStats]:
        """按上下文预热.

        Args:
            bc_name: BC名称（如 "catalog", "identity", "ordering"）

        Returns:
            该BC的预热统计结果
        """
        # 过滤出指定BC的策略
        bc_strategies = [
            strategy
            for strategy in self._strategies
            if self._strategy_metadata.get(strategy.__class__.__name__, {}).get("bc_name")
            == bc_name
        ]

        if not bc_strategies:
            logger.warning(f"没有找到 BC '{bc_name}' 的预热策略")
            return {}

        logger.info(f"🔄 执行 {bc_name} BC 的预热，共 {len(bc_strategies)} 个策略")

        results = await self._warmer.warmup_multiple(bc_strategies)

        total_warmed = sum(s.warmed_keys for s in results.values())
        total_keys = sum(s.total_keys for s in results.values())

        logger.info(f"✅ {bc_name} BC 预热完成: {total_warmed}/{total_keys} 个键")

        return results

    def list_strategies(self) -> dict[str, dict]:
        """列出所有已注册的策略.

        Returns:
            策略元数据字典
        """
        return self._strategy_metadata.copy()

    def get_warmer(self) -> CacheWarmer:
        """获取底层的CacheWarmer实例.

        Returns:
            CacheWarmer实例
        """
        return self._warmer

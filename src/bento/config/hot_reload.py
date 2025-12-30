"""配置热更新支持 - 运行时动态配置变更"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from watchfiles import awatch

from .outbox import OutboxProjectorConfig, set_outbox_projector_config

logger = logging.getLogger(__name__)


class ConfigHotReloader:
    """配置热更新管理器

    支持监听配置文件变更和环境变量变更，
    在运行时动态更新配置并通知相关组件。
    """

    def __init__(self):
        self._callbacks: list[Callable[[OutboxProjectorConfig], Any]] = []
        self._current_config: OutboxProjectorConfig | None = None
        self._watcher_task: asyncio.Task | None = None
        self._lock = threading.Lock()
        self._running = False

    def register_callback(self, callback: Callable[[OutboxProjectorConfig], Any]) -> None:
        """注册配置变更回调

        Args:
            callback: 配置变更时调用的回调函数
        """
        with self._lock:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[OutboxProjectorConfig], Any]) -> None:
        """取消注册配置变更回调

        Args:
            callback: 要移除的回调函数
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    async def start_file_watcher(self, config_file_path: str) -> None:
        """启动配置文件监听

        Args:
            config_file_path: 配置文件路径
        """
        if self._running:
            logger.warning("配置热更新已经在运行")
            return

        self._running = True
        config_path = Path(config_file_path)

        if not config_path.exists():
            logger.warning(f"配置文件不存在: {config_file_path}")
            return

        # 首次加载配置
        await self._reload_from_file(config_path)

        # 启动文件监听
        self._watcher_task = asyncio.create_task(self._watch_config_file(config_path))
        logger.info(f"开始监听配置文件: {config_file_path}")

    async def _watch_config_file(self, config_path: Path) -> None:
        """监听配置文件变更"""
        try:
            async for changes in awatch(config_path.parent):
                for change_type, changed_path in changes:
                    if Path(changed_path) == config_path:
                        logger.info(f"检测到配置文件变更: {change_type}")
                        await self._reload_from_file(config_path)
                        break
        except Exception as e:
            logger.error(f"配置文件监听错误: {e}")
        finally:
            self._running = False

    async def _reload_from_file(self, config_path: Path) -> None:
        """从文件重新加载配置"""
        try:
            # 支持不同格式的配置文件
            if config_path.suffix.lower() == ".json":
                import json

                with open(config_path, encoding="utf-8") as f:
                    config_data = json.load(f)
            elif config_path.suffix.lower() in [".yaml", ".yml"]:
                import yaml

                with open(config_path, encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)
            else:
                logger.error(f"不支持的配置文件格式: {config_path.suffix}")
                return

            # 创建新配置
            new_config = OutboxProjectorConfig.from_dict(config_data.get("outbox", {}))

            # 检查配置是否有变更
            if self._current_config != new_config:
                old_config = self._current_config
                self._current_config = new_config

                # 更新全局配置
                set_outbox_projector_config(new_config)

                # 通知所有回调
                await self._notify_config_changed(new_config, old_config)

                logger.info("配置热更新完成")

        except Exception as e:
            logger.error(f"配置重新加载失败: {e}")

    async def reload_from_env(self) -> None:
        """从环境变量重新加载配置"""
        try:
            new_config = OutboxProjectorConfig.from_env()

            if self._current_config != new_config:
                old_config = self._current_config
                self._current_config = new_config

                # 更新全局配置
                set_outbox_projector_config(new_config)

                # 通知所有回调
                await self._notify_config_changed(new_config, old_config)

                logger.info("环境变量配置重新加载完成")

        except Exception as e:
            logger.error(f"环境变量配置重新加载失败: {e}")

    async def _notify_config_changed(
        self, new_config: OutboxProjectorConfig, old_config: OutboxProjectorConfig | None
    ) -> None:
        """通知配置变更"""
        with self._lock:
            callbacks = self._callbacks.copy()

        for callback in callbacks:
            try:
                # 如果回调是异步函数
                if asyncio.iscoroutinefunction(callback):
                    await callback(new_config)
                else:
                    callback(new_config)
            except Exception as e:
                logger.error(f"配置变更回调执行失败: {e}")

        # 记录配置变更
        if old_config:
            self._log_config_changes(old_config, new_config)

    def _log_config_changes(
        self, old_config: OutboxProjectorConfig, new_config: OutboxProjectorConfig
    ) -> None:
        """记录配置变更详情"""
        changes = []

        # 比较所有配置字段
        for field_name in new_config.__dataclass_fields__:
            old_value = getattr(old_config, field_name)
            new_value = getattr(new_config, field_name)

            if old_value != new_value:
                changes.append(f"{field_name}: {old_value} → {new_value}")

        if changes:
            logger.info(f"配置变更详情: {', '.join(changes)}")

    async def stop(self) -> None:
        """停止配置热更新"""
        self._running = False

        if self._watcher_task:
            self._watcher_task.cancel()
            try:
                await self._watcher_task
            except asyncio.CancelledError:
                pass

        logger.info("配置热更新已停止")


# 全局热更新管理器实例
_hot_reloader: ConfigHotReloader | None = None


def get_hot_reloader() -> ConfigHotReloader:
    """获取全局配置热更新管理器"""
    global _hot_reloader
    if _hot_reloader is None:
        _hot_reloader = ConfigHotReloader()
    return _hot_reloader


class HotReloadableComponent:
    """支持热更新的组件基类"""

    def __init__(self, config: OutboxProjectorConfig | None = None):
        self._config = config
        self._hot_reloader = get_hot_reloader()

        # 注册配置变更回调
        self._hot_reloader.register_callback(self._on_config_changed)

    async def _on_config_changed(self, new_config: OutboxProjectorConfig) -> None:
        """配置变更回调 - 子类可以重写"""
        old_config = self._config
        self._config = new_config

        logger.info(f"{self.__class__.__name__} 配置已更新")

        # 子类可以重写此方法实现特定的配置更新逻辑
        await self._handle_config_update(old_config, new_config)

    async def _handle_config_update(
        self, old_config: OutboxProjectorConfig | None, new_config: OutboxProjectorConfig
    ) -> None:
        """处理配置更新 - 子类应该重写此方法"""
        pass

    def cleanup(self) -> None:
        """清理资源"""
        self._hot_reloader.unregister_callback(self._on_config_changed)

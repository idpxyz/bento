# infrastructure/uow/abstract_uow.py
from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from typing import Generic, List, Set, TypeVar

from sqlalchemy.orm import Session

from idp.framework.domain.base.entity import BaseAggregateRoot
from idp.framework.domain.base.event import DomainEvent
from idp.framework.infrastructure.messaging.core.event_bus import AbstractEventBus

T = TypeVar("T", bound=BaseAggregateRoot)


class AbstractUnitOfWork(AbstractAsyncContextManager, ABC, Generic[T]):
    """
    高层事务边界 + 事件收集/发布 抽象基类
    进入时创建 Session，退出时自动 commit / rollback + publish events
    """

    def __init__(self, event_bus: AbstractEventBus):
        self._event_bus = event_bus
        self._session: Session | None = None  # 由子类在 begin() 创建

    # ------------- async context-protocol -------------
    async def __aenter__(self) -> "AbstractUnitOfWork[T]":
        await self.begin()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                await self.rollback()
            else:
                await self.commit()
        except Exception:
            await self.rollback()
            raise
        finally:
            await self._cleanup()

    # ------------------ abstract hooks ----------------
    @abstractmethod
    async def begin(self): ...
    @abstractmethod
    async def _do_commit(self): ...
    @abstractmethod
    async def rollback(self): ...
    @abstractmethod
    async def _cleanup(self): ...

    # ------------------ template commit --------------
    async def commit(self):
        """模板方法：持久化后收集并发布领域事件"""
        await self._do_commit()
        events = self._collect_events()
        if events:
            await self._event_bus.publish(events)

    # ------------------ event collector --------------
    def _collect_events(self) -> List[DomainEvent]:
        if not self._session:
            return []
        aggregate_set: Set[BaseAggregateRoot] = (
            set(self._session.new)
            | set(self._session.dirty)
            | set(self._session.deleted)
        )
        events: List[DomainEvent] = []
        for agg in aggregate_set:
            if isinstance(agg, BaseAggregateRoot):
                events.extend(agg.pull_events())
        return events

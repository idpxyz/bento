"""
Cascade Helper - 简化聚合级联操作的工具类
"""

from collections.abc import Callable
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from bento.persistence.interceptor import create_default_chain
from bento.persistence.repository.sqlalchemy import BaseRepository


class CascadeHelper:
    """级联操作助手"""

    def __init__(self, session: AsyncSession, actor: str = "system") -> None:
        self.session = session
        self.actor = actor

    async def replace_children(
        self,
        parent_entity: Any,
        child_entities: list[Any],
        child_po_type: type[Any],
        child_mapper: Callable[[Any], Any],
        foreign_key_field: str,
    ) -> None:
        """替换子实体 (删除旧的，创建新的)

        Args:
            parent_entity: 父聚合根
            child_entities: 新的子实体列表
            child_po_type: 子实体 PO 类型
            child_mapper: 子实体映射器
            foreign_key_field: 外键字段名
        """
        parent_id = str(parent_entity.id)

        # 1. 删除旧的子实体
        await self.session.execute(
            delete(child_po_type).where(getattr(child_po_type, foreign_key_field) == parent_id)
        )

        # 2. 创建新的子实体
        if child_entities:
            child_repo = BaseRepository(
                session=self.session,
                po_type=child_po_type,
                actor=self.actor,
                interceptor_chain=create_default_chain(self.actor),
            )

            for entity in child_entities:
                po = child_mapper(entity)
                await child_repo.create_po(po)


class CascadeConfig:
    """级联配置类"""

    def __init__(
        self,
        child_po_type: type[Any],
        child_mapper: Callable[[Any], Any],
        foreign_key_field: str,
    ) -> None:
        self.child_po_type = child_po_type
        self.child_mapper = child_mapper
        self.foreign_key_field = foreign_key_field


class CascadeMixin:
    """级联操作混入类

    注意：这个类需要与 RepositoryAdapter 一起使用
    需要确保有 session 和 actor 属性
    """

    def get_cascade_helper(self) -> CascadeHelper:
        """获取级联助手"""
        session = getattr(self, "session", None)
        if session is None:
            raise AttributeError("CascadeMixin requires 'session' attribute")

        actor = getattr(self, "actor", "system")
        return CascadeHelper(session=session, actor=actor)

    async def save_with_cascade(
        self, aggregate: Any, cascade_configs: dict[str, CascadeConfig] | None = None
    ) -> None:
        """带级联的保存方法

        Args:
            aggregate: 聚合根
            cascade_configs: 级联配置字典
        """
        # 1. 保存聚合根 (需要子类实现)
        if hasattr(super(), "save"):
            await super().save(aggregate)  # type: ignore
        else:
            raise NotImplementedError("save method must be implemented")

        # 2. 处理级联
        if cascade_configs:
            helper = self.get_cascade_helper()

            for field_name, config in cascade_configs.items():
                child_entities = getattr(aggregate, field_name, [])

                await helper.replace_children(
                    parent_entity=aggregate,
                    child_entities=child_entities,
                    child_po_type=config.child_po_type,
                    child_mapper=config.child_mapper,
                    foreign_key_field=config.foreign_key_field,
                )

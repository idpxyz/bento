"""Automatic cross-entity cache invalidation.

自动跨实体缓存失效机制：
- 开发者只需定义实体关联关系
- 框架自动监听事件并失效相关缓存
- 避免手动失效导致的遗漏
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bento.application.ports.cache import Cache
    from bento.domain.domain_event import DomainEvent


@dataclass
class EntityRelation:
    """实体关联关系配置.

    Example:
        ```python
        # Order 创建会影响 Customer 和 Product
        EntityRelation(
            source_entity="Order",
            related_entities=["Customer", "Product"],
            operations=["CREATE", "UPDATE", "DELETE"]
        )
        ```
    """

    source_entity: str
    """源实体类型（触发变更的实体）"""

    related_entities: list[str]
    """受影响的关联实体列表"""

    operations: list[str] = None
    """触发失效的操作类型，默认 ["CREATE", "UPDATE", "DELETE"]"""

    cache_patterns: dict[str, list[str]] | None = None
    """自定义缓存失效模式

    Example:
        {
            "Customer": ["Customer:{customer_id}:*"],
            "Product": ["Product:{product_id}:sales:*"]
        }
    """

    def __post_init__(self):
        if self.operations is None:
            self.operations = ["CREATE", "UPDATE", "DELETE"]


class CacheInvalidationConfig:
    """缓存失效配置管理器.

    Example:
        ```python
        config = CacheInvalidationConfig()

        # 配置 Order 的关联关系
        config.add_relation(
            EntityRelation(
                source_entity="Order",
                related_entities=["Customer", "Product"],
            )
        )

        # 配置 Review 的关联关系
        config.add_relation(
            EntityRelation(
                source_entity="Review",
                related_entities=["Product"],
                cache_patterns={
                    "Product": [
                        "Product:{product_id}:rating:*",
                        "ProductRanking:by_rating:*"
                    ]
                }
            )
        )
        ```
    """

    def __init__(self):
        self._relations: dict[str, list[EntityRelation]] = {}

    def add_relation(self, relation: EntityRelation) -> None:
        """添加实体关联关系."""
        if relation.source_entity not in self._relations:
            self._relations[relation.source_entity] = []
        self._relations[relation.source_entity].append(relation)

    def get_related_entities(self, entity_type: str, operation: str) -> list[EntityRelation]:
        """获取指定实体和操作的关联关系."""
        relations = self._relations.get(entity_type, [])
        return [
            rel for rel in relations if operation.upper() in [op.upper() for op in rel.operations]
        ]


class AutoCacheInvalidationHandler:
    """自动缓存失效处理器.

    监听领域事件，根据配置自动失效跨实体缓存。

    Usage:
        ```python
        # 1. 配置关联关系
        config = CacheInvalidationConfig()
        config.add_relation(
            EntityRelation(
                source_entity="Order",
                related_entities=["Customer", "Product"],
            )
        )

        # 2. 创建处理器
        handler = AutoCacheInvalidationHandler(cache, config)

        # 3. 注册到事件总线（框架自动完成）
        event_bus.subscribe(handler)

        # 4. 之后所有 Order 变更会自动失效相关缓存
        await order_repo.save(order)  # ✅ 自动失效 Customer 和 Product 缓存
        ```
    """

    def __init__(self, cache: Cache, config: CacheInvalidationConfig):
        self._cache = cache
        self._config = config

    async def handle_entity_changed(
        self, entity_type: str, operation: str, event_data: dict[str, Any]
    ) -> None:
        """处理实体变更事件.

        Args:
            entity_type: 实体类型（如 "Order"）
            operation: 操作类型（CREATE/UPDATE/DELETE）
            event_data: 事件数据，包含实体 ID 和其他关联 ID
        """
        # 获取该实体的关联关系
        relations = self._config.get_related_entities(entity_type, operation)

        if not relations:
            return

        # 对每个关联关系失效缓存
        for relation in relations:
            await self._invalidate_related_caches(relation, event_data)

    async def _invalidate_related_caches(
        self, relation: EntityRelation, event_data: dict[str, Any]
    ) -> None:
        """失效关联实体的缓存."""
        for related_entity in relation.related_entities:
            # 使用自定义模式或默认模式
            if relation.cache_patterns and related_entity in relation.cache_patterns:
                patterns = relation.cache_patterns[related_entity]
                for pattern in patterns:
                    # 替换占位符
                    resolved_pattern = self._resolve_pattern(pattern, event_data)
                    await self._cache.delete_pattern(resolved_pattern)
            else:
                # 默认：失效该实体类型的所有缓存
                await self._cache.delete_pattern(f"{related_entity}:*")

    def _resolve_pattern(self, pattern: str, event_data: dict[str, Any]) -> str:
        """解析缓存模式中的占位符.

        Example:
            pattern: "Customer:{customer_id}:orders:*"
            event_data: {"customer_id": "c123"}
            result: "Customer:c123:orders:*"
        """
        result = pattern
        for key, value in event_data.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result


# ==================== 事件监听器集成 ====================


class DomainEventCacheInvalidator:
    """领域事件缓存失效器.

    自动监听所有领域事件，识别实体变更并触发缓存失效。

    框架会自动注册这个处理器，开发者只需要配置关联关系。

    Example:
        ```python
        # 在应用启动时配置
        # config/cache_relations.py

        def configure_cache_relations():
            config = CacheInvalidationConfig()

            # Order 关联关系
            config.add_relation(EntityRelation(
                source_entity="Order",
                related_entities=["Customer", "Product"],
                cache_patterns={
                    "Customer": ["Customer:{customer_id}:orders:*"],
                    "Product": ["Product:{product_id}:sales:*"]
                }
            ))

            # Review 关联关系
            config.add_relation(EntityRelation(
                source_entity="Review",
                related_entities=["Product"],
                cache_patterns={
                    "Product": [
                        "Product:{product_id}:rating:*",
                        "ProductRanking:*"
                    ]
                }
            ))

            return config
        ```
    """

    def __init__(self, cache: Cache, config: CacheInvalidationConfig):
        self._handler = AutoCacheInvalidationHandler(cache, config)

    async def on_domain_event(self, event: DomainEvent) -> None:
        """处理领域事件."""
        # 解析事件名称获取实体类型和操作
        entity_type, operation = self._parse_event_name(event.topic)

        if not entity_type or not operation:
            return

        # 提取事件数据
        event_data = event.to_payload()

        # 触发缓存失效
        await self._handler.handle_entity_changed(entity_type, operation, event_data)

    def _parse_event_name(self, event_name: str) -> tuple[str | None, str | None]:
        """解析事件名称获取实体类型和操作.

        Example:
            "OrderCreated" -> ("Order", "CREATE")
            "ProductUpdated" -> ("Product", "UPDATE")
            "ReviewDeleted" -> ("Review", "DELETE")
        """
        if not event_name:
            return None, None

        # 支持的操作模式
        operations = {
            "Created": "CREATE",
            "Updated": "UPDATE",
            "Deleted": "DELETE",
            "Modified": "UPDATE",
        }

        for suffix, operation in operations.items():
            if event_name.endswith(suffix):
                entity_type = event_name[: -len(suffix)]
                return entity_type, operation

        return None, None


# ==================== 便捷配置工具 ====================


def create_simple_relation(
    source: str,
    related: str | list[str],
    id_field: str | None = None,
) -> EntityRelation:
    """创建简单的实体关联关系.

    Args:
        source: 源实体类型
        related: 关联实体类型（单个或列表）
        id_field: 关联实体的 ID 字段名（如 "customer_id"）

    Example:
        ```python
        # Order 影响 Customer
        relation = create_simple_relation(
            source="Order",
            related="Customer",
            id_field="customer_id"
        )
        # 自动生成模式: Customer:{customer_id}:*
        ```
    """
    if isinstance(related, str):
        related = [related]

    cache_patterns = {}
    if id_field:
        for entity in related:
            cache_patterns[entity] = [f"{entity}:{{{id_field}}}:*"]

    return EntityRelation(
        source_entity=source,
        related_entities=related,
        cache_patterns=cache_patterns if cache_patterns else None,
    )


def create_relation_builder():
    """创建关联关系构建器（流式 API）.

    Example:
        ```python
        builder = create_relation_builder()

        config = (
            builder
            .relation("Order")
                .affects("Customer", id_field="customer_id")
                .affects("Product", id_field="product_id")
                .with_pattern("ProductSales:*")
            .relation("Review")
                .affects("Product", id_field="product_id")
                .with_pattern("Product:{product_id}:rating:*")
                .with_pattern("ProductRanking:*")
            .build()
        )
        ```
    """
    return RelationBuilder()


class RelationBuilder:
    """关联关系流式构建器."""

    def __init__(self):
        self._config = CacheInvalidationConfig()
        self._current_source: str | None = None
        self._current_related: list[str] = []
        self._current_patterns: dict[str, list[str]] = {}

    def relation(self, source: str) -> RelationBuilder:
        """开始定义新的关联关系."""
        self._flush_current()
        self._current_source = source
        self._current_related = []
        self._current_patterns = {}
        return self

    def affects(self, entity: str, id_field: str | None = None) -> RelationBuilder:
        """添加受影响的实体."""
        if not self._current_source:
            raise ValueError("Must call relation() first")

        self._current_related.append(entity)

        # 如果提供了 ID 字段，生成默认模式
        if id_field:
            if entity not in self._current_patterns:
                self._current_patterns[entity] = []
            self._current_patterns[entity].append(f"{entity}:{{{id_field}}}:*")

        return self

    def with_pattern(self, pattern: str, entity: str | None = None) -> RelationBuilder:
        """添加自定义缓存模式."""
        if not self._current_related:
            raise ValueError("Must call affects() first")

        # 如果没有指定实体，应用到最后一个关联实体
        target_entity = entity or self._current_related[-1]

        if target_entity not in self._current_patterns:
            self._current_patterns[target_entity] = []
        self._current_patterns[target_entity].append(pattern)

        return self

    def build(self) -> CacheInvalidationConfig:
        """构建配置."""
        self._flush_current()
        return self._config

    def _flush_current(self):
        """保存当前配置."""
        if self._current_source and self._current_related:
            self._config.add_relation(
                EntityRelation(
                    source_entity=self._current_source,
                    related_entities=self._current_related,
                    cache_patterns=self._current_patterns if self._current_patterns else None,
                )
            )

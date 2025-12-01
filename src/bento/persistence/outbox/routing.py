"""智能路由配置模块"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoutingRule:
    """路由规则"""

    destination: str
    conditions: dict[str, Any] = field(default_factory=dict)
    transform: dict[str, Any] = field(default_factory=dict)
    delay_seconds: int = 0
    sampling_rate: float = 1.0
    retry_policy: str = "default"


@dataclass
class DestinationConfig:
    """目标配置"""

    destination: str
    payload: dict[str, Any] | None = None
    delay: int = 0
    retry_policy: str = "default"


class SmartRouter:
    """智能事件路由器"""

    def resolve_destinations(self, record) -> list[DestinationConfig]:
        """解析事件的目标路由

        Args:
            record: OutboxRecord 实例

        Returns:
            目标配置列表
        """
        # 1. 简单路由（向下兼容）
        if not record.routing_config and record.routing_key:
            return [DestinationConfig(destination=record.routing_key, payload=record.payload)]

        # 2. 智能路由
        if not record.routing_config.get("targets"):
            # 没有配置，使用默认路由
            return [DestinationConfig(destination="default.events", payload=record.payload)]

        destinations = []
        routing_config = record.routing_config

        for rule_data in routing_config.get("targets", []):
            rule = RoutingRule(**rule_data)

            # 条件匹配
            if self._match_conditions(rule.conditions, record):
                # 采样决策
                if self._should_sample(rule.sampling_rate):
                    # 转换 payload
                    transformed_payload = self._transform_payload(record.payload, rule.transform)

                    destinations.append(
                        DestinationConfig(
                            destination=rule.destination,
                            payload=transformed_payload,
                            delay=rule.delay_seconds,
                            retry_policy=rule.retry_policy,
                        )
                    )

        # 降级策略
        if not destinations and routing_config.get("fallback"):
            destinations.append(
                DestinationConfig(destination=routing_config["fallback"], payload=record.payload)
            )

        return destinations

    def _match_conditions(self, conditions: dict[str, Any], record) -> bool:
        """条件匹配引擎"""
        if not conditions:
            return True

        for path, expected in conditions.items():
            actual = self._extract_value(record, path)
            if not self._compare_values(actual, expected):
                return False
        return True

    def _extract_value(self, record, path: str) -> Any:
        """路径提取：支持 payload.field.subfield 语法"""
        parts = path.split(".")
        value = record

        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        return value

    def _compare_values(self, actual: Any, expected: Any) -> bool:
        """值比较"""
        if isinstance(expected, dict):
            # 支持操作符：$gt, $lt, $in, $ne 等
            for op, value in expected.items():
                if op == "$gt" and not (actual is not None and actual > value):
                    return False
                elif op == "$lt" and not (actual is not None and actual < value):
                    return False
                elif op == "$gte" and not (actual is not None and actual >= value):
                    return False
                elif op == "$lte" and not (actual is not None and actual <= value):
                    return False
                elif op == "$in" and actual not in value:
                    return False
                elif op == "$ne" and actual == value:
                    return False
                elif op == "$exists" and bool(actual is not None) != value:
                    return False
            return True
        else:
            # 直接比较
            return actual == expected

    def _should_sample(self, sampling_rate: float) -> bool:
        """采样决策"""
        if sampling_rate >= 1.0:
            return True
        return random.random() < sampling_rate

    def _transform_payload(
        self, payload: dict[str, Any], transform_config: dict[str, Any]
    ) -> dict[str, Any]:
        """转换 payload"""
        if not transform_config:
            return payload

        result = payload.copy()

        # 包含字段过滤
        if "include_fields" in transform_config:
            include_fields = transform_config["include_fields"]
            result = {k: v for k, v in result.items() if k in include_fields}

        # 排除字段过滤
        if "exclude_fields" in transform_config:
            exclude_fields = transform_config["exclude_fields"]
            result = {k: v for k, v in result.items() if k not in exclude_fields}

        # 字段映射
        if "field_mapping" in transform_config:
            field_mapping = transform_config["field_mapping"]
            mapped_result = {}
            for old_key, new_key in field_mapping.items():
                if old_key in result:
                    mapped_result[new_key] = result[old_key]
                    del result[old_key]
            result.update(mapped_result)

        # 添加字段
        if "add_fields" in transform_config:
            result.update(transform_config["add_fields"])

        return result


class RoutingConfigBuilder:
    """路由配置构建器"""

    def __init__(self):
        self.config = {
            "targets": [],
            "strategy": "best_effort",
            "fallback": None,
        }

    def add_target(
        self,
        destination: str,
        conditions: dict[str, Any] | None = None,
        transform: dict[str, Any] | None = None,
        delay_seconds: int = 0,
        sampling_rate: float = 1.0,
        retry_policy: str = "default",
    ) -> RoutingConfigBuilder:
        """添加目标路由"""
        target = {
            "destination": destination,
            "conditions": conditions or {},
            "transform": transform or {},
            "delay_seconds": delay_seconds,
            "sampling_rate": sampling_rate,
            "retry_policy": retry_policy,
        }
        self.config["targets"].append(target)
        return self

    def set_fallback(self, destination: str) -> RoutingConfigBuilder:
        """设置降级目标"""
        self.config["fallback"] = destination
        return self

    def set_strategy(self, strategy: str) -> RoutingConfigBuilder:
        """设置路由策略"""
        self.config["strategy"] = strategy
        return self

    def build(self) -> dict[str, Any]:
        """构建配置"""
        return self.config.copy()


# 便捷函数
def create_simple_routing(destination: str) -> dict[str, Any]:
    """创建简单路由配置"""
    return RoutingConfigBuilder().add_target(destination).build()


def create_conditional_routing(targets: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    """创建条件路由配置

    Args:
        targets: [(destination, conditions), ...] 列表
    """
    builder = RoutingConfigBuilder()
    for destination, conditions in targets:
        builder.add_target(destination, conditions=conditions)
    return builder.build()


def create_sampling_routing(destination: str, sampling_rate: float) -> dict[str, Any]:
    """创建采样路由配置"""
    return RoutingConfigBuilder().add_target(destination, sampling_rate=sampling_rate).build()

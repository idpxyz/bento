"""
Schema 兼容性测试
"""
import json
import os
import tempfile
from typing import Dict, List, Tuple

import pytest

from idp.framework.infrastructure.schema.cli.schemactl import (
    are_avro_types_compatible,
    are_json_types_compatible,
)


class TestAvroCompatibility:
    """测试 Avro 兼容性检查"""
    
    @pytest.mark.parametrize("type1,type2,expected", [
        # 相同类型兼容
        ("string", "string", True),
        ("int", "int", True),
        
        # 数值类型扩展兼容
        ("int", "long", True),
        ("int", "float", True),
        ("int", "double", True),
        ("long", "double", True),
        ("float", "double", True),
        
        # 不兼容类型
        ("string", "int", False),
        ("int", "string", False),
        ("boolean", "string", False),
        
        # 复杂类型
        ({"type": "array", "items": "string"}, {"type": "array", "items": "string"}, True),
        ({"type": "array", "items": "string"}, {"type": "array", "items": "int"}, False),
    ])
    def test_avro_type_compatibility(self, type1, type2, expected):
        """测试 Avro 类型兼容性"""
        assert are_avro_types_compatible(type1, type2) == expected

class TestJsonCompatibility:
    """测试 JSON Schema 兼容性检查"""
    
    @pytest.mark.parametrize("type1,type2,reverse,expected", [
        # 相同类型兼容
        ({"type": "string"}, {"type": "string"}, False, True),
        ({"type": "integer"}, {"type": "integer"}, False, True),
        
        # integer 可以转换为 number
        ({"type": "integer"}, {"type": "number"}, False, True),
        ({"type": "number"}, {"type": "integer"}, False, False),
        
        # 数组兼容性
        (
            {"type": "array", "items": {"type": "string"}},
            {"type": "array", "items": {"type": "string"}},
            False,
            True
        ),
        (
            {"type": "array", "items": {"type": "string"}},
            {"type": "array", "items": {"type": "integer"}},
            False,
            False
        ),
        
        # 对象兼容性
        (
            {"type": "object", "properties": {"name": {"type": "string"}}},
            {"type": "object", "properties": {"name": {"type": "string"}}},
            False,
            True
        ),
        (
            {"type": "object", "properties": {"name": {"type": "string"}}},
            {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}},
            False,
            True
        ),
        (
            {"type": "object", "properties": {"name": {"type": "string"}}},
            {"type": "object", "properties": {"age": {"type": "integer"}}},
            False,
            True  # 向后兼容，新对象不需要包含所有旧属性
        ),
        (
            {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
            {"type": "object", "properties": {"age": {"type": "integer"}}},
            False,
            False  # 不兼容，缺少必需属性
        ),
    ])
    def test_json_type_compatibility(self, type1, type2, reverse, expected):
        """测试 JSON Schema 类型兼容性"""
        assert are_json_types_compatible(type1, type2, reverse) == expected

    def test_json_forward_compatibility(self):
        """测试 JSON Schema 向前兼容性"""
        # 向前兼容：旧版本能读取新版本数据
        old_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"]
        }
        
        # 新版本添加了可选字段
        new_schema_compatible = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string"}  # 新增可选字段
            },
            "required": ["name"]  # 只保留原来的必需字段
        }
        
        # 新版本添加了必需字段，不向前兼容
        new_schema_incompatible = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string"}
            },
            "required": ["name", "email"]  # 新增必需字段
        }
        
        # 检查兼容性
        assert are_json_types_compatible(old_schema, new_schema_compatible, reverse=True)
        assert not are_json_types_compatible(old_schema, new_schema_incompatible, reverse=True) 
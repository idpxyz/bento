#!/usr/bin/env python3
"""
测试 Schema 到 Pydantic 模型转换器是否正确处理 Literal 类型
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from .generators.avro_generator import generate_pydantic_from_avro
from .generators.json_generator import generate_pydantic_from_json
from .generators.proto_generator import generate_pydantic_from_proto


class TestGenerators(unittest.TestCase):
    """测试 Schema 生成器处理 Literal 类型的功能"""
    
    def setUp(self):
        """准备测试环境"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        
        # 创建测试 JSON Schema 文件
        self.json_schema = {
            "title": "UserActivity",
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["login", "logout", "view", "click", "search", "purchase"],
                    "description": "活动类型"
                }
            }
        }
        self.json_schema_path = os.path.join(self.test_dir, "user_activity.json")
        with open(self.json_schema_path, "w") as f:
            json.dump(self.json_schema, f, indent=2)
        
        # 创建测试 Avro schema 文件
        self.avro_schema = {
            "type": "record",
            "name": "UserPreference",
            "fields": [
                {
                    "name": "theme",
                    "type": {
                        "type": "enum",
                        "name": "Theme",
                        "symbols": ["light", "dark", "auto"]
                    },
                    "doc": "用户界面主题"
                }
            ]
        }
        self.avro_schema_path = os.path.join(self.test_dir, "user_preference.avsc")
        with open(self.avro_schema_path, "w") as f:
            json.dump(self.avro_schema, f, indent=2)
        
        # 创建测试 Proto 文件
        self.proto_content = """
        syntax = "proto3";
        
        package test;
        
        // 用户状态事件
        message UserStatusChanged {
            string user_id = 1;                // 用户ID
            string status = 2;                 // 用户状态 选项: "active", "inactive", "suspended"
        }
        """
        self.proto_path = os.path.join(self.test_dir, "user_status.proto")
        with open(self.proto_path, "w") as f:
            f.write(self.proto_content)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    def test_json_generator_adds_literal_import(self):
        """测试 JSON 生成器是否正确添加 Literal 导入"""
        output_path = os.path.join(self.test_dir, "json_test.py")
        generate_pydantic_from_json(self.json_schema_path, output_path)
        
        # 检查生成的文件是否包含 Literal 导入
        with open(output_path, "r") as f:
            content = f.read()
            self.assertIn("from typing import Literal", content)
            self.assertIn("action: Literal['login', 'logout', 'view', 'click', 'search', 'purchase']", content)
    
    def test_avro_generator_handles_literal(self):
        """测试 Avro 生成器是否正确处理 Literal 类型"""
        output_path = os.path.join(self.test_dir, "avro_test.py")
        generate_pydantic_from_avro(self.avro_schema_path, output_path)
        
        # 检查生成的文件是否包含 Literal 导入
        with open(output_path, "r") as f:
            content = f.read()
            self.assertIn("from typing import Literal", content)
            # 验证是否使用了 Literal 类型或生成了枚举
            self.assertTrue(
                "theme: Literal['light', 'dark', 'auto']" in content or 
                "class Theme(str, Enum):" in content
            )
    
    def test_proto_generator_adds_literal_import(self):
        """测试 Proto 生成器是否正确添加 Literal 导入"""
        output_path = os.path.join(self.test_dir, "proto_test.py")
        generate_pydantic_from_proto(self.proto_path, output_path)
        
        # 检查生成的文件是否包含 Literal 导入
        with open(output_path, "r") as f:
            content = f.read()
            self.assertIn("from typing import Literal", content)
            self.assertIn("status: Optional[Literal['active', 'inactive', 'suspended']]", content)


if __name__ == "__main__":
    unittest.main() 
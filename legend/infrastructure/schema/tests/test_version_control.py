"""
Schema 版本控制测试
"""
import json
import os
import tempfile
from unittest.mock import patch

import pytest
import yaml

from idp.framework.infrastructure.schema.cli.schemactl import (
    load_registry,
    save_registry,
    version_list,
    version_new,
)


class TestVersionControl:
    """测试 Schema 版本控制功能"""
    
    def setup_method(self):
        """设置测试环境"""
        # 创建临时目录和文件
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # 设置路径
        self.schema_dir = os.path.join(self.temp_dir.name, "schema")
        self.proto_dir = os.path.join(self.schema_dir, "proto")
        self.registry_file = os.path.join(self.schema_dir, "registry.yml")
        
        # 创建目录
        os.makedirs(self.proto_dir, exist_ok=True)
        
        # 创建示例 Proto 文件
        self.proto_file = os.path.join(self.proto_dir, "test_event.proto")
        with open(self.proto_file, "w") as f:
            f.write("""syntax = "proto3";

package events;

// 测试事件
message TestEvent {
    string id = 1;
    string name = 2;
    int32 count = 3;
}
""")
        
        # 创建示例注册表
        self.registry = {
            "schemas": [
                {
                    "name": "TestEvent",
                    "format": "proto",
                    "file": "proto/test_event.proto",
                    "topic": "persistent://test/default/test.event",
                    "description": "测试事件"
                }
            ]
        }
        
        # 保存注册表
        with open(self.registry_file, "w") as f:
            yaml.dump(self.registry, f)
    
    def teardown_method(self):
        """清理测试环境"""
        self.temp_dir.cleanup()
    
    @patch("idp.framework.infrastructure.schema.cli.schemactl.SCHEMA_DIR")
    @patch("idp.framework.infrastructure.schema.cli.schemactl.REGISTRY_FILE")
    def test_version_new(self, mock_registry_file, mock_schema_dir):
        """测试创建 Schema 新版本"""
        # 设置模拟
        mock_schema_dir.return_value = self.schema_dir
        mock_registry_file.return_value = self.registry_file
        
        # 创建参数对象
        class Args:
            name = "TestEvent"
            version = "2"
            update_topic = True
        
        with patch("idp.framework.infrastructure.schema.cli.schemactl.SCHEMA_DIR", self.schema_dir):
            with patch("idp.framework.infrastructure.schema.cli.schemactl.REGISTRY_FILE", self.registry_file):
                # 执行版本创建
                version_new(Args())
                
                # 验证生成的文件
                versioned_file = os.path.join(self.proto_dir, "test_event_v2.proto")
                assert os.path.exists(versioned_file)
                
                # 验证注册表更新
                with open(self.registry_file, "r") as f:
                    registry = yaml.safe_load(f)
                
                # 应该有两个 schema
                assert len(registry["schemas"]) == 2
                
                # 验证新版本信息
                new_schema = next(s for s in registry["schemas"] if s["name"] == "TestEventV2")
                assert new_schema["version"] == "2"
                assert new_schema["parent"] == "TestEvent"
                assert new_schema["file"] == "proto/test_event_v2.proto"
                assert "v2" in new_schema["topic"]
    
    @patch("builtins.print")
    @patch("idp.framework.infrastructure.schema.cli.schemactl.SCHEMA_DIR")
    @patch("idp.framework.infrastructure.schema.cli.schemactl.REGISTRY_FILE")
    def test_version_list(self, mock_registry_file, mock_schema_dir, mock_print):
        """测试列出 Schema 版本"""
        # 设置模拟
        mock_schema_dir.return_value = self.schema_dir
        mock_registry_file.return_value = self.registry_file
        
        # 创建参数对象
        class Args:
            name = "TestEvent"
            version = "2"
            update_topic = True
        
        with patch("idp.framework.infrastructure.schema.cli.schemactl.SCHEMA_DIR", self.schema_dir):
            with patch("idp.framework.infrastructure.schema.cli.schemactl.REGISTRY_FILE", self.registry_file):
                # 先创建一个新版本
                version_new(Args())
                
                # 创建参数对象用于 version_list
                class ListArgs:
                    name = "TestEvent"
                
                # 执行版本列表
                version_list(ListArgs())
                
                # 验证输出包含主版本和衍生版本
                assert any("主版本" in str(call) for call in mock_print.call_args_list)
                assert any("衍生版本" in str(call) for call in mock_print.call_args_list)
                assert any("版本 2" in str(call) for call in mock_print.call_args_list) 
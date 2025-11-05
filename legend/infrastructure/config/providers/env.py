"""
环境变量配置提供器

从环境变量和.env文件加载配置，使用统一的环境前缀命名方式
例如：DB_DEV_CONNECTION_HOST=localhost
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type

from dotenv import load_dotenv
from pydantic import BaseModel

from idp.framework.infrastructure.config.core.provider import ConfigProvider


class EnvProvider(ConfigProvider):
    """环境变量配置提供器"""
    
    def __init__(self, namespace: str, schema_class: Optional[Type[BaseModel]] = None,
                 env_name: Optional[str] = None, prefix: Optional[str] = None, 
                 config_dir: Optional[str] = None):
        """
        初始化环境变量提供器
        
        Args:
            namespace: 配置命名空间
            schema_class: Pydantic 模型类，用于验证配置结构
            env_name: 环境名称，如果为None则使用ENV环境变量或默认为dev
            prefix: 环境变量前缀，用于过滤特定前缀的环境变量
            config_dir: 配置文件目录，如果提供则在该目录下寻找.env文件
        """
        self.env_name = env_name if env_name is not None else os.getenv("ENV", "dev")
        self.namespace = namespace
        self.schema_class = schema_class
        self.env_prefix = prefix.upper() if prefix is not None else ""
        self.config_dir = config_dir
        
        # 用于存储字段路径映射
        self._field_paths: Dict[str, str] = {}
        self._env_keys: Dict[str, str] = {}
        
        # 如果提供了schema，预处理字段路径
        if schema_class is not None:
            self._process_schema()
    
    def get_namespace(self) -> str:
        """获取配置命名空间"""
        return self.namespace
    
    def load(self) -> Dict[str, Any]:
        """从环境变量加载配置
        
        Returns:
            Dict[str, Any]: 配置数据
        """
        config = {}
        env_vars = self.get_env_vars()
        
        for key, value in env_vars.items():
            path = self._env_key_to_path(key)
            
            # 将路径转换为嵌套字典
            current = config
            parts = path.split(".")
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        
        return config
    
    def reload(self) -> Dict[str, Any]:
        """重新加载环境变量配置
        
        Returns:
            Dict[str, Any]: 重新加载的配置数据
        """
        return self.load()
    
    def supports_hot_reload(self) -> bool:
        """环境变量配置不支持热重载"""
        return False
    
    def _process_schema(self) -> None:
        """处理 Pydantic 模型的 schema，生成字段路径映射"""
        schema = self.schema_class.model_json_schema()
        
        def process_properties(properties: Dict[str, Any], prefix: str = "") -> None:
            for field_name, field_info in properties.items():
                # 获取完整路径
                full_path = f"{prefix}.{field_name}" if prefix else field_name
                
                # 如果是嵌套对象，递归处理
                if field_info.get("type") == "object" and "properties" in field_info:
                    process_properties(field_info["properties"], full_path)
                else:
                    # 生成环境变量键
                    env_key = self._path_to_env_key(full_path)
                    self._field_paths[env_key] = full_path
                    self._env_keys[full_path] = env_key
        
        if "properties" in schema:
            process_properties(schema["properties"])
    
    def _path_to_env_key(self, path: str) -> str:
        """将配置路径转换为环境变量键名
        
        Args:
            path: 配置路径，如 "connection.host"
            
        Returns:
            str: 环境变量键名，如 "CONNECTION_HOST"
        """
        # 转换为大写并替换点为下划线
        env_key = path.upper().replace(".", "_")
        
        # 如果有前缀，添加前缀
        if self.env_prefix:
            env_key = f"{self.env_prefix}_{env_key}"
            
        return env_key
    
    def _env_key_to_path(self, key: str) -> str:
        """将环境变量键名转换为配置路径
        
        Args:
            key: 环境变量键名，如 "DB_CONNECTION_HOST"
            
        Returns:
            str: 配置路径，如 "connection.host"
        """
        # 如果有前缀，移除前缀
        if self.env_prefix and key.startswith(f"{self.env_prefix}_"):
            key = key[len(self.env_prefix) + 1:]
        
        # 如果有schema并且键在映射中存在，使用预定义的路径
        if self.schema_class and key in self._field_paths:
            return self._field_paths[key]
        
        # 否则，使用简单的转换规则
        return key.lower().replace("_", ".")
    
    def get_env_vars(self) -> Dict[str, str]:
        """获取所有相关的环境变量
        
        Returns:
            Dict[str, str]: 环境变量字典
        """
        # 如果指定了配置目录，尝试加载.env文件
        if self.config_dir:
            env_file = os.path.join(self.config_dir, ".env")
            if os.path.exists(env_file):
                load_dotenv(env_file)
        
        # 获取所有环境变量
        env_vars = {}
        for key, value in os.environ.items():
            # 如果有前缀，只获取带前缀的环境变量
            if self.env_prefix and not key.startswith(f"{self.env_prefix}_"):
                continue
            env_vars[key] = value
        
        return env_vars
    
    def get_env_key(self, path: str) -> str:
        """根据配置路径获取对应的环境变量键名
        
        Args:
            path: 配置路径，如 "connection.host"
            
        Returns:
            str: 环境变量键名，如 "DB_CONNECTION_HOST"
        """
        if self.schema_class and path in self._env_keys:
            return self._env_keys[path]
        return self._path_to_env_key(path)

    def _print_loaded_config(self) -> None:
        """打印已加载的配置，方便调试"""
        print(f"\n🔍 [EnvProvider] [{self.namespace}] 已加载配置:")
        
        def print_nested_dict(d: Dict[str, Any], prefix: str = "") -> None:
            for key, value in d.items():
                if isinstance(value, dict):
                    print(f"{prefix}{key}:")
                    print_nested_dict(value, prefix + "  ")
                else:
                    # 对于敏感信息，不显示实际值
                    if any(secret in key.upper() for secret in ["PASSWORD", "SECRET", "KEY"]):
                        print(f"{prefix}{key}: ********")
                    else:
                        print(f"{prefix}{key}: {value}")
        
        print_nested_dict(self._config_data)
        print("") 
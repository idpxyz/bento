"""
YAML配置提供器

从YAML文件加载配置
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from idp.framework.infrastructure.config.core.base import ConfigurationError
from idp.framework.infrastructure.config.core.provider import ConfigProvider


class YamlProvider(ConfigProvider):
    """YAML配置提供器"""
    
    def __init__(self, namespace: str, file_paths: List[str], required: bool = False, env_name: str = "dev"):
        """
        初始化YAML配置提供器
        
        Args:
            namespace: 配置命名空间
            file_paths: YAML文件路径列表，按优先级从低到高排序
            required: 是否必须存在配置文件
            env_name: 环境名称，默认为 dev
        """
        self._namespace = namespace
        self._file_paths = file_paths
        self._required = required
        self._env_name = env_name
        self._loaded = False
        self._config_data: Dict[str, Any] = {}
        
    def get_namespace(self) -> str:
        """获取配置命名空间"""
        return self._namespace
    
    def load(self) -> Dict[str, Any]:
        """加载YAML配置文件
        
        Returns:
            Dict[str, Any]: 配置数据
            
        Raises:
            ConfigurationError: 如果required=True且文件不存在
        """
        if self._loaded:
            return self._config_data
        
        self._config_data = {
            'default': {},
            self._env_name: {}
        }
        found_any = False
        
        for file_path in self._file_paths:
            path = Path(file_path)
            if not path.exists():
                continue
                
            found_any = True
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = yaml.safe_load(f)
                    
                if not isinstance(file_data, dict):
                    print(f"⚠️ [YamlProvider] YAML内容不是字典: {file_path}")
                    continue
                    
                # 提取默认配置和环境特定配置
                default_config = file_data.get('default', {})
                env_config = file_data.get(self._env_name, {})
                
                # 更新配置数据，保持嵌套结构
                self._config_data['default'] = self._deep_merge(
                    self._config_data['default'],
                    default_config
                )
                self._config_data[self._env_name] = self._deep_merge(
                    self._config_data[self._env_name],
                    env_config
                )
                
                print(f"✅ [YamlProvider] 已加载YAML配置: {file_path}")
                print(f"📋 加载的配置:")
                print(f"   默认配置: {self._config_data['default']}")
                print(f"   环境配置: {env_config}")
                    
            except Exception as e:
                print(f"⚠️ [YamlProvider] 加载YAML配置失败: {file_path}, 错误: {e}")
                if self._required:
                    raise ConfigurationError(f"无法加载必需的YAML配置: {file_path}, 错误: {e}")
        
        if self._required and not found_any:
            raise ConfigurationError(f"未找到任何必需的YAML配置文件: {self._file_paths}")
            
        self._loaded = True
        return self._config_data
    
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个字典，保持嵌套结构
        
        Args:
            target: 目标字典
            source: 源字典
            
        Returns:
            Dict[str, Any]: 合并后的字典
        """
        result = target.copy()
        for key, value in source.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def reload(self) -> Dict[str, Any]:
        """重新加载YAML配置
        
        Returns:
            Dict[str, Any]: 重新加载的配置数据
        """
        self._loaded = False
        return self.load()
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置
        
        Returns:
            Dict[str, Any]: 默认配置
        """
        if not self._loaded:
            self.load()
        return self._config_data.get('default', {})
    
    def supports_hot_reload(self) -> bool:
        """YAML配置支持热重载"""
        return True 
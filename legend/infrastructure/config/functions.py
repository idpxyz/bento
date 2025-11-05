"""
配置系统实用函数

提供对配置管理器常用操作的简便访问函数
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel

from idp.framework.infrastructure.config.core.base import ConfigSection
from idp.framework.infrastructure.config.core.manager import (
    ConfigManager,
    config_manager,
)

T = TypeVar('T', bound=BaseModel)


def initialize(env_name: Optional[str] = None) -> None:
    """初始化配置系统
    
    Args:
        env_name: 环境名称，用于加载对应的环境配置
    """
    config_manager.initialize(env_name)


def register_section(name: str, schema_class: Type[BaseModel]) -> ConfigSection:
    """注册配置段
    
    Args:
        name: 配置名称
        schema_class: 配置模式类
        
    Returns:
        ConfigSection: 配置段实例
    """
    return config_manager.register_section(name, schema_class)


def register_yaml_config(namespace: str, file_paths: List[str], required: bool = False) -> None:
    """注册YAML配置
    
    Args:
        namespace: 配置命名空间
        file_paths: YAML文件路径列表
        required: 是否必须存在配置文件
    """
    config_manager.register_yaml_config(namespace, file_paths, required)


def register_json_config(namespace: str, file_paths: List[str], required: bool = False) -> None:
    """注册JSON配置
    
    Args:
        namespace: 配置命名空间
        file_paths: JSON文件路径列表
        required: 是否必须存在配置文件
    """
    config_manager.register_json_config(namespace, file_paths, required)


def get_config(name: str, model_class: Optional[Type[T]] = None) -> Any:
    """获取指定名称的配置
    
    Args:
        name: 配置名称
        model_class: 配置模型类，用于类型检查（可选）
        
    Returns:
        Any: 配置实例
    """
    return config_manager.get_config(name, model_class)


def get_config_by_path(name: str, path: str, default: Any = None) -> Any:
    """通过路径获取配置值
    
    Args:
        name: 配置段名称
        path: 配置路径，以点分隔，如 "connection.pool.min_size"
        default: 如果路径不存在，返回的默认值
        
    Returns:
        Any: 配置值
    """
    return config_manager.get_config_by_path(name, path, default) 
"""
IDP Schema Center 模块

提供事件模式管理、代码生成和版本控制功能。
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import requests

# Schema 目录
SCHEMA_DIR = os.getenv('SCHEMA_DIR', os.path.dirname(os.path.abspath(__file__)))
REGISTRY_FILE = os.path.join(SCHEMA_DIR, 'registry', 'registry.json')

# 从 CLI 导入 schemactl
from idp.framework.infrastructure.schema.cli import schemactl


def load_registry(registry_path: Optional[str] = None) -> Dict:
    """
    加载 Schema 注册表
    
    Args:
        registry_path: 注册表路径，可以是本地文件路径或远程 URL
        
    Returns:
        Dict: 注册表数据
    """
    path = registry_path or REGISTRY_FILE
    
    # 检查是否是 URL
    if path.startswith(('http://', 'https://')):
        try:
            response = requests.get(path)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"无法从 URL 加载注册表: {e}")
            return {'schemas': []}
    
    # 本地文件
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logging.warning(f"注册表文件不存在: {path}")
            return {'schemas': []}
    except Exception as e:
        logging.error(f"加载注册表失败: {e}")
        return {'schemas': []}

def load_schema(name: str, version: Optional[int] = None) -> Optional[Dict]:
    """
    加载指定名称和版本的 Schema
    
    Args:
        name: Schema 名称
        version: Schema 版本号，如不指定则使用最新版本
        
    Returns:
        Optional[Dict]: Schema 定义，如找不到则返回 None
    """
    registry = load_registry()
    
    # 查找匹配的 Schema
    for schema in registry.get('schemas', []):
        if schema.get('name') == name:
            # 如果没有指定版本或版本匹配
            if version is None or schema.get('version') == version:
                return schema
    
    logging.warning(f"找不到 Schema: {name}" + (f" 版本: {version}" if version else ""))
    return None

def get_schema_topic(name: str) -> Optional[str]:
    """
    获取 Schema 对应的主题名称
    
    Args:
        name: Schema 名称
        
    Returns:
        Optional[str]: 主题名称，如找不到则返回 None
    """
    schema = load_schema(name)
    if schema:
        return schema.get('topic')
    return None

def get_schema_doc_url(name: str) -> Optional[str]:
    """
    获取 Schema 的文档 URL
    
    Args:
        name: Schema 名称
        
    Returns:
        Optional[str]: 文档 URL，如找不到则返回 None
    """
    schema = load_schema(name)
    if schema:
        return schema.get('doc_url')
    return None

def get_schemas_by_topics(topics: List[str]) -> Dict[str, Dict]:
    """
    通过主题列表获取 Schema 映射
    
    Args:
        topics: 主题名称列表
        
    Returns:
        Dict[str, Dict]: 主题到 Schema 的映射
    """
    registry = load_registry()
    schemas_map = {}
    
    for schema in registry.get('schemas', []):
        topic = schema.get('topic')
        if topic and topic in topics:
            schemas_map[topic] = schema
    
    return schemas_map

__all__ = [
    'load_registry',
    'load_schema',
    'get_schema_topic',
    'get_schema_doc_url',
    'get_schemas_by_topics',
    'schemactl'
] 
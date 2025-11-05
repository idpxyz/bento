"""
JSON配置提供器

从JSON文件加载配置
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from idp.framework.infrastructure.config.core.base import ConfigurationError
from idp.framework.infrastructure.config.core.provider import ConfigProvider
from idp.framework.shared.utils.dict import DictUtils


class JsonProvider(ConfigProvider):
    """JSON配置提供器，从JSON文件加载配置"""
    
    def __init__(self, namespace: str, file_paths: List[str], required: bool = False):
        """
        初始化JSON配置提供器
        
        Args:
            namespace: 配置命名空间
            file_paths: JSON文件路径列表，按优先级从低到高排序
            required: 是否必须存在配置文件
        """
        self._namespace = namespace
        self._file_paths = file_paths
        self._required = required
        self._loaded = False
        self._config_data: Dict[str, Any] = {}
        
        # 打印初始化信息
        print(f"✅ [JsonProvider] 初始化配置提供器: namespace={namespace}, required={required}")
        print(f"✅ [JsonProvider] 配置文件列表:")
        for i, path in enumerate(file_paths):
            print(f"   {i+1}. {path} (存在: {Path(path).exists()})")
        
    def get_namespace(self) -> str:
        """获取配置命名空间"""
        return self._namespace
    
    def load(self) -> Dict[str, Any]:
        """加载JSON配置文件
        
        Returns:
            Dict[str, Any]: 配置数据
            
        Raises:
            ConfigurationError: 如果required=True且文件不存在
        """
        if self._loaded:
            return self._config_data
        
        self._config_data = {}
        found_any = False
        
        # 打印当前工作目录
        print(f"📂 [JsonProvider] 当前工作目录: {os.getcwd()}")
        
        for file_path in self._file_paths:
            path = Path(file_path)
            print(f"🔍 [JsonProvider] 检查文件: {path} (绝对路径: {path.absolute()})")
            
            if not path.exists():
                print(f"⚠️ [JsonProvider] 文件不存在: {path}")
                # 尝试向上查找
                parent_file = Path(os.getcwd()) / path.name
                if parent_file.exists():
                    print(f"✅ [JsonProvider] 在当前目录找到同名文件: {parent_file}")
                    path = parent_file
                else:
                    print(f"❌ [JsonProvider] 在当前目录未找到同名文件")
                    continue
                
            found_any = True
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    print(f"📖 [JsonProvider] 读取文件: {path}")
                    file_data = json.load(f)
                    
                if not isinstance(file_data, dict):
                    print(f"⚠️ [JsonProvider] JSON内容不是字典: {path}")
                    continue
                    
                # 深度合并配置
                print(f"🔄 [JsonProvider] 合并配置: {path}")
                DictUtils.deep_merge(self._config_data, file_data)
                print(f"✅ [JsonProvider] 已加载JSON配置: {path}")
                print(f"📊 [JsonProvider] 配置项数量: {len(file_data)}")
                    
            except json.JSONDecodeError as e:
                print(f"⚠️ [JsonProvider] JSON格式错误: {path}")
                print(f"   位置: {e.pos}, 行: {e.lineno}, 列: {e.colno}")
                print(f"   错误信息: {e.msg}")
                if self._required:
                    raise ConfigurationError(f"无法解析必需的JSON配置: {path}, 错误: {e}")
            except Exception as e:
                print(f"⚠️ [JsonProvider] 加载JSON配置失败: {path}, 错误类型: {type(e).__name__}")
                print(f"   错误信息: {str(e)}")
                if self._required:
                    raise ConfigurationError(f"无法加载必需的JSON配置: {path}, 错误: {e}")
        
        if self._required and not found_any:
            raise ConfigurationError(f"未找到任何必需的JSON配置文件: {self._file_paths}")
            
        self._loaded = True
        
        print(f"✅ [JsonProvider] 配置加载完成: namespace={self._namespace}")
        print(f"   最终配置项数量: {len(self._config_data)}")
        
        return self._config_data
    
    def reload(self) -> Dict[str, Any]:
        """重新加载JSON配置
        
        Returns:
            Dict[str, Any]: 重新加载的配置数据
        """
        print(f"🔄 [JsonProvider] 重新加载配置: namespace={self._namespace}")
        self._loaded = False
        return self.load()
    
    def supports_hot_reload(self) -> bool:
        """JSON配置支持热重载"""
        return True 
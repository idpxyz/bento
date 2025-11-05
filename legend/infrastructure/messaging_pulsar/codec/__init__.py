"""
消息编解码器模块

提供多种编解码格式支持:
1. JSON: 默认编解码器，提供基本的序列化和反序列化功能
2. Protocol Buffers: 高效二进制序列化格式，支持向前/向后兼容
3. Avro: 支持复杂数据类型和 Schema 演化的序列化系统

使用方法:
```python
from idp.framework.infrastructure.messaging.core.codec import get_codec

# 默认使用 JSON 编解码器
codec = get_codec()  
# 或指定使用特定编解码器
protobuf_codec = get_codec("protobuf") 
avro_codec = get_codec("avro")

# 编码
serialized = codec.encode(message_envelope)
# 解码
message = codec.decode(serialized)
```
"""

import importlib
import pkgutil
import sys
from pathlib import Path

# 先导入核心模块
from idp.framework.infrastructure.messaging.core.codec import (
    _codec_registry,
    get_codec,
    register_codec,
)

# 确保拥有 protobuf 目录
from . import protobuf

# 当前模块路径：idp.framework.infrastructure.messaging.codec
PACKAGE_PATH = __path__
PACKAGE_NAME = __name__  # "idp.framework.infrastructure.messaging.codec"

# 确保明确导入所有编解码器实现
def register_all_codecs():
    """手动注册所有编解码器"""
    try:
        # 使用 _codec_files 而不是 module 名称来避免与内置模块冲突
        codec_files = [
            "json_codec", 
            "protobuf_codec",
            "avro_codec"
        ]
        
        for codec_file in codec_files:
            try:
                if codec_file in sys.modules:
                    del sys.modules[f"{PACKAGE_NAME}.{codec_file}"]
                
                importlib.import_module(f"{PACKAGE_NAME}.{codec_file}")
                print(f"[codec] 已导入 {codec_file}")
            except ImportError as e:
                print(f"[codec] 导入 {codec_file} 失败: {e}")
        
        # 检查是否成功注册
        registered = list(_codec_registry.keys())
        if registered:
            print(f"[codec] 已注册编解码器: {', '.join(registered)}")
        else:
            print("[codec] 直接导入后注册表仍为空，尝试动态导入")
            # 回退到动态导入机制
            _register_via_pkgutil()
    except Exception as e:
        print(f"[codec] 编解码器导入错误: {e}")
        # 回退到动态导入机制
        _register_via_pkgutil()

def _register_via_pkgutil():
    """通过pkgutil自动扫描并导入模块"""
    # 自动导入所有 codec 模块（触发 register_codec）
    loaded = []
    for _, module_name, is_pkg in pkgutil.iter_modules(PACKAGE_PATH):
        if not is_pkg and module_name.endswith('_codec'):
            try:
                importlib.import_module(f"{PACKAGE_NAME}.{module_name}")
                loaded.append(module_name)
            except ImportError as e:
                print(f"[codec] 无法导入 {module_name}: {e}")
    
    print(f"[codec] 动态导入完成: {', '.join(loaded)}")

# 立即注册所有编解码器
register_all_codecs()

# 确保至少有一个默认编解码器
if "json" not in _codec_registry:
    print("[codec] 警告: JSON编解码器未注册，尝试手动注册")
    try:
        from .json_codec import JsonMessageCodec
        register_codec("json", JsonMessageCodec())
    except Exception as e:
        print(f"[codec] 手动注册JSON编解码器失败: {e}")

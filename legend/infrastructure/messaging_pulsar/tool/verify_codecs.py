#!/usr/bin/env python3
"""
验证编解码器安装和功能脚本

使用:
    python verify_codecs.py
"""

import importlib.util
import json as python_json
import sys
from datetime import UTC, datetime
from pathlib import Path

# 添加当前目录到 Python 路径
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir.parent.parent.parent.parent))

print("=== 验证编解码器安装和功能 ===\n")

# 导入核心模块
try:
    from idp.framework.infrastructure.messaging.core.base_message import MessageEnvelope
    from idp.framework.infrastructure.messaging.core.codec import (
        MessageCodec,
        _codec_registry,
        get_codec,
        register_codec,
    )
    print("✅ 核心模块导入成功")
except ImportError as e:
    print(f"❌ 核心模块导入失败: {str(e)}")
    sys.exit(1)

# 初始化编解码器
print("\n初始化编解码器...")
try:
    # 确保不会导入自定义json模块
    import sys
    if 'idp.framework.infrastructure.messaging.codec.json' in sys.modules:
        del sys.modules['idp.framework.infrastructure.messaging.codec.json']
    
    from idp.framework.infrastructure.messaging.init import auto_register_codecs
    auto_register_codecs()
    print("✅ 自动注册编解码器完成")
except Exception as e:
    print(f"❌ 自动注册编解码器失败: {str(e)}")

# 检查已注册的编解码器
print(f"\n已注册的编解码器: {list(_codec_registry.keys())}")

# 如果编解码器没有正确注册，尝试手动注册
if "json" not in _codec_registry:
    print("手动注册 JSON 编解码器...")
    try:
        from idp.framework.infrastructure.messaging.codec.json import JsonMessageCodec
        register_codec("json", JsonMessageCodec())
        print("✅ 手动注册 JSON 编解码器成功")
    except Exception as e:
        print(f"❌ 注册 JSON 编解码器失败: {str(e)}")

if "protobuf" not in _codec_registry:
    print("手动注册 Protocol Buffer 编解码器...")
    try:
        # 尝试从文件动态加载
        protobuf_path = current_dir / "codec" / "protobuf.py"
        if protobuf_path.exists():
            spec = importlib.util.spec_from_file_location("protobuf_codec", protobuf_path)
            protobuf_module = importlib.util.module_from_spec(spec)
            sys.modules["protobuf_codec"] = protobuf_module
            spec.loader.exec_module(protobuf_module)
            
            # 检查是否有 ProtobufMessageCodec 类
            if hasattr(protobuf_module, "ProtobufMessageCodec"):
                register_codec("protobuf", protobuf_module.ProtobufMessageCodec())
                print("✅ 通过文件路径导入 ProtobufMessageCodec 成功")
            else:
                print("❌ 在 protobuf.py 中未找到 ProtobufMessageCodec 类")
        else:
            print(f"❌ 未找到 protobuf.py 文件: {protobuf_path}")
    except Exception as e:
        print(f"❌ 注册 Protocol Buffer 编解码器失败: {str(e)}")

if "avro" not in _codec_registry:
    print("手动注册 Avro 编解码器...")
    try:
        # 尝试从文件动态加载
        avro_path = current_dir / "codec" / "avro.py"
        if avro_path.exists():
            spec = importlib.util.spec_from_file_location("avro_codec", avro_path)
            avro_module = importlib.util.module_from_spec(spec)
            sys.modules["avro_codec"] = avro_module
            spec.loader.exec_module(avro_module)
            
            # 检查是否有 AvroMessageCodec 类
            if hasattr(avro_module, "AvroMessageCodec"):
                register_codec("avro", avro_module.AvroMessageCodec())
                print("✅ 通过文件路径导入 AvroMessageCodec 成功")
            else:
                print("❌ 在 avro.py 中未找到 AvroMessageCodec 类")
        else:
            print(f"❌ 未找到 avro.py 文件: {avro_path}")
    except Exception as e:
        print(f"❌ 注册 Avro 编解码器失败: {str(e)}")

# 更新已注册的编解码器列表
print(f"\n更新后的编解码器列表: {list(_codec_registry.keys())}")

# 创建测试消息
test_message = MessageEnvelope(
    event_type="codec.test",
    payload={"id": "test-123", "timestamp": datetime.now(UTC).isoformat()},
    source="verify-script",
    correlation_id="verify-001"
)

print(f"\n测试消息: {test_message.event_type} ({test_message.correlation_id})")

# 测试各编解码器
codec_names = ["json", "protobuf", "avro"]
success_count = 0

for name in codec_names:
    print(f"\n--- 测试 {name} 编解码器 ---")
    
    try:
        # 获取编解码器
        if name not in _codec_registry:
            print(f"❌ {name} 编解码器未注册")
            continue
            
        codec = get_codec(name)
        print(f"✅ 已获取 {name} 编解码器: {type(codec).__name__}")
        
        # 编码
        encoded = codec.encode(test_message)
        print(f"✅ 编码成功，大小: {len(encoded)} 字节")
        
        # 解码
        decoded = codec.decode(encoded)
        print(f"✅ 解码成功，event_type: {decoded.event_type}, correlation_id: {decoded.correlation_id}")
        
        # 对比一致性
        if (decoded.event_type == test_message.event_type and 
            decoded.correlation_id == test_message.correlation_id):
            print(f"✅ 验证通过: 编解码一致")
            success_count += 1
        else:
            print(f"❌ 验证失败: 编解码结果不一致")
    
    except Exception as e:
        print(f"❌ 测试出错: {str(e)}")
        import traceback
        traceback.print_exc()

# 总结
print(f"\n=== 验证结果: {success_count}/{len(codec_names)} 个编解码器通过 ===")
if success_count == len(codec_names):
    print("\n✅ 所有编解码器正常工作！")
else:
    print("\n⚠️ 有编解码器验证失败，请检查错误信息并修复问题")
    
if success_count < len(codec_names):
    print("\n建议: 运行 python install_codecs.py 确保所有依赖已安装且代码已生成") 
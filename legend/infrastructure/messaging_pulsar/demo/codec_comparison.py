#!/usr/bin/env python3
"""
编解码器性能对比示例

运行示例: python codec_comparison.py
"""

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Dict, List

from infrastructure.messaging.codec import (
    protobuf as protobuf_codec,  # 确保Protobuf编解码器被导入
)

# 确保编解码器被正确加载
from idp.framework.infrastructure.messaging.codec import (
    avro as avro_codec,  # 确保Avro编解码器被导入
)
from idp.framework.infrastructure.messaging.codec import (
    json as json_codec,  # 确保JSON编解码器被导入
)
from idp.framework.infrastructure.messaging.core.base_message import MessageEnvelope
from idp.framework.infrastructure.messaging.core.codec import get_codec


@dataclass
class CodecBenchmarkResult:
    codec_name: str
    encode_time: float
    decode_time: float
    data_size: int
    
    def __str__(self):
        return (f"Codec: {self.codec_name:<10} | "
                f"Encode: {self.encode_time:.6f}s | "
                f"Decode: {self.decode_time:.6f}s | "
                f"Size: {self.data_size:,} bytes")


def create_test_message() -> MessageEnvelope:
    """创建一个复杂测试消息"""
    return MessageEnvelope(
        event_type="user.profile.updated",
        payload={
            "user_id": "user-123456",
            "name": "张三",
            "email": "zhangsan@example.com",
            "age": 28,
            "is_active": True,
            "roles": ["user", "admin", "editor"],
            "preferences": {
                "language": "zh-CN",
                "theme": "dark",
                "notifications": {
                    "email": True,
                    "sms": False,
                    "push": True
                }
            },
            "address": {
                "street": "幸福大道123号",
                "city": "上海市",
                "zip": "200000",
                "coordinates": [121.4737, 31.2304]
            },
            "registration_date": "2020-01-01T00:00:00Z",
            "last_login": datetime.now(UTC).isoformat(),  # 使用timezone-aware的UTC时间
            "activity_log": [
                {"action": "login", "timestamp": "2023-01-01T10:00:00Z", "ip": "192.168.1.1"},
                {"action": "update_profile", "timestamp": "2023-01-02T11:30:00Z", "ip": "192.168.1.2"},
                {"action": "purchase", "timestamp": "2023-01-03T15:45:00Z", "ip": "192.168.1.3"}
            ]
        },
        source="user-service",
        correlation_id="req-abcdef-123456-xyz",
    )


def benchmark_codec(codec_name: str, message: MessageEnvelope, iterations: int = 1000) -> CodecBenchmarkResult:
    """对指定编解码器进行基准测试"""
    try:
        # 获取编解码器实例
        codec = get_codec(codec_name)
        
        # 运行一次预热
        serialized = codec.encode(message)
        codec.decode(serialized)
        
        # 编码性能测试
        start_time = time.time()
        for _ in range(iterations):
            serialized = codec.encode(message)
        encode_time = (time.time() - start_time) / iterations
        
        # 解码性能测试
        start_time = time.time()
        for _ in range(iterations):
            codec.decode(serialized)
        decode_time = (time.time() - start_time) / iterations
        
        # 数据大小
        data_size = len(serialized)
        
        return CodecBenchmarkResult(
            codec_name=codec_name,
            encode_time=encode_time,
            decode_time=decode_time,
            data_size=data_size
        )
    except Exception as e:
        print(f"  ✗ 测试 {codec_name} 失败: {str(e)}")
        # 为了调试，打印更详细的错误信息
        import traceback
        traceback.print_exc()
        return None


def run_comparison():
    """运行所有编解码器对比"""
    # 创建测试消息
    message = create_test_message()
    
    # 对比不同编解码器
    codec_names = ["json", "protobuf", "avro"]
    results = []
    
    print("\n====== 消息编解码器性能对比 ======\n")
    print(f"测试消息: event_type={message.event_type}, source={message.source}")
    print(f"消息复杂度: payload 包含 {len(json.dumps(message.payload))} 字符\n")
    
    # 打印可用的编解码器
    from idp.framework.infrastructure.messaging.core.codec import _codec_registry
    print(f"已注册的编解码器: {list(_codec_registry.keys())}\n")
    
    for codec_name in codec_names:
        print(f"测试 {codec_name} 编解码器...")
        result = benchmark_codec(codec_name, message)
        if result:
            results.append(result)
            print(f"  → {result}")
    
    # 打印比较结果
    if len(results) > 1:
        print("\n====== 性能对比结果 ======\n")
        
        # 基准编解码器 (JSON)
        base = next((r for r in results if r.codec_name == "json"), None)
        
        if base:
            for r in results:
                if r.codec_name == "json":
                    continue
                    
                encode_speedup = base.encode_time / r.encode_time
                decode_speedup = base.decode_time / r.decode_time
                size_reduction = (base.data_size - r.data_size) / base.data_size * 100
                
                print(f"{r.codec_name} vs JSON:")
                print(f"  - 编码速度: {encode_speedup:.2f}x 更快")
                print(f"  - 解码速度: {decode_speedup:.2f}x 更快")
                print(f"  - 数据大小: 减少 {size_reduction:.1f}%")
                print()


if __name__ == "__main__":
    # 确保初始化
    print("正在初始化编解码器...")
    from idp.framework.infrastructure.messaging.init import auto_register_codecs
    auto_register_codecs()
    
    run_comparison() 
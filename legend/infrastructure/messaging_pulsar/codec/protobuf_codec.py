import json
import os
import sys
from datetime import datetime
from typing import Any, Dict

# 使用 protobuf 而不是 pb 来确保正确导入
try:
    import google.protobuf
    from google.protobuf.json_format import MessageToDict, ParseDict
except ImportError:
    raise ImportError("未安装 protobuf 包，请运行 pip install protobuf")

from idp.framework.infrastructure.messaging.core.base_message import MessageEnvelope
from idp.framework.infrastructure.messaging.core.codec import (
    MessageCodec,
    register_codec,
)

# 尝试导入 message_pb2，如果不存在，则创建内存中的 protobuf 消息类型
try:
    from idp.framework.infrastructure.messaging.codec.protobuf import message_pb2
except ImportError:
    print(f"[protobuf] 警告: 未找到 message_pb2.py, 尝试生成临时消息类型")
    
    # 创建一个简单的 MessageEnvelope 类替代 message_pb2.MessageEnvelope
    from google.protobuf.descriptor import FieldDescriptor
    from google.protobuf.descriptor_pb2 import FieldDescriptorProto
    from google.protobuf.message import Message
    
    class DynamicMessageEnvelope(Message):
        """动态创建的 MessageEnvelope 消息类型，用于临时替代 message_pb2.MessageEnvelope"""
        
        class _NestedMap(Message):
            """嵌套的 map 类型"""
            
            def __init__(self):
                super().__init__()
                self._entries = {}
            
            def __getitem__(self, key):
                return self._entries.get(key, "")
                
            def __setitem__(self, key, value):
                self._entries[key] = value
            
            def items(self):
                return self._entries.items()
                
            def CopyFrom(self, other):
                self._entries = {}
                for k, v in other.items():
                    self._entries[k] = v
            
            def SerializeToString(self):
                return json.dumps(self._entries).encode('utf-8')
            
            def ParseFromString(self, data):
                self._entries = json.loads(data.decode('utf-8'))
                return self
            
            @classmethod
            def FromString(cls, data):
                result = cls()
                result._entries = json.loads(data.decode('utf-8'))
                return result
        
        def __init__(self):
            super().__init__()
            self.event_type = ""
            self.payload = self._NestedMap()
            self.occurred_at = ""
            self.source = ""
            self.correlation_id = ""
        
        def CopyFrom(self, other):
            self.event_type = other.event_type
            self.payload.CopyFrom(other.payload)
            self.occurred_at = other.occurred_at
            self.source = other.source
            self.correlation_id = other.correlation_id
        
        def Clear(self):
            self.event_type = ""
            self.payload = self._NestedMap()
            self.occurred_at = ""
            self.source = ""
            self.correlation_id = ""
        
        def SerializeToString(self):
            data = {
                "event_type": self.event_type,
                "payload": dict(self.payload.items()),
                "occurred_at": self.occurred_at,
                "source": self.source,
                "correlation_id": self.correlation_id
            }
            return json.dumps(data).encode('utf-8')
            
        def ParseFromString(self, data):
            self.Clear()
            parsed = json.loads(data.decode('utf-8'))
            self.event_type = parsed.get("event_type", "")
            
            for k, v in parsed.get("payload", {}).items():
                self.payload[k] = v
                
            self.occurred_at = parsed.get("occurred_at", "")
            self.source = parsed.get("source", "")
            self.correlation_id = parsed.get("correlation_id", "")
            return self
        
        @classmethod
        def FromString(cls, data):
            result = cls()
            result.ParseFromString(data)
            return result
    
    # 使用动态创建的消息类型替代 message_pb2.MessageEnvelope
    message_pb2 = type('message_pb2', (), {'MessageEnvelope': DynamicMessageEnvelope})
    
    print("[protobuf] 已创建临时消息类型。建议运行 install_codecs.py 生成真正的 Protocol Buffer 代码")


class ProtobufMessageCodec(MessageCodec):
    """Protocol Buffer implementation of the message codec"""
    
    def encode(self, envelope: MessageEnvelope) -> bytes:
        """Encode a MessageEnvelope into protocol buffer bytes"""
        # 转换复杂 payload 为字符串值以兼容 protobuf map
        string_payload = {
            k: json.dumps(v) if not isinstance(v, (str, int, float, bool)) else str(v)
            for k, v in envelope.payload.items()
        }
        
        # 创建 protobuf 消息
        proto_msg = message_pb2.MessageEnvelope()
        proto_msg.event_type = envelope.event_type
        
        # 填充 payload map
        for k, v in string_payload.items():
            proto_msg.payload[k] = v
            
        proto_msg.occurred_at = envelope.occurred_at.isoformat()
        proto_msg.source = envelope.source
        proto_msg.correlation_id = envelope.correlation_id
        
        return proto_msg.SerializeToString()
    
    def decode(self, raw: bytes) -> MessageEnvelope:
        """Decode protocol buffer bytes into a MessageEnvelope"""
        proto_msg = message_pb2.MessageEnvelope()
        proto_msg.ParseFromString(raw)
        
        # 转换 proto payload 回复杂对象
        payload = {}
        for k, v in proto_msg.payload.items():
            try:
                # 尝试解析为 JSON 复杂对象
                payload[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                # 否则保持为字符串
                payload[k] = v
        
        return MessageEnvelope(
            event_type=proto_msg.event_type,
            payload=payload,
            occurred_at=datetime.fromisoformat(proto_msg.occurred_at),
            source=proto_msg.source,
            correlation_id=proto_msg.correlation_id
        )


# 注册编解码器
try:
    register_codec("protobuf", ProtobufMessageCodec())
    print("[codec] Protocol Buffer 编解码器已注册")
except Exception as e:
    print(f"[codec] Protocol Buffer 编解码器注册失败: {str(e)}") 
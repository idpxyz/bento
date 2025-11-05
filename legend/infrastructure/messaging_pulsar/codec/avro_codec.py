import io
import json
import os
from datetime import datetime
from typing import Any, Dict

import avro
from avro.io import BinaryDecoder, BinaryEncoder, DatumReader, DatumWriter
from avro.schema import parse as avro_parse

from idp.framework.infrastructure.messaging.core.base_message import MessageEnvelope
from idp.framework.infrastructure.messaging.core.codec import (
    MessageCodec,
    register_codec,
)


class AvroMessageCodec(MessageCodec):
    """Avro implementation of the message codec"""
    
    def __init__(self):
        # 加载schema从文件
        schema_path = os.path.join(os.path.dirname(__file__), "avro", "message.avsc")
        
        # 确保schema目录存在
        avro_dir = os.path.join(os.path.dirname(__file__), "avro")
        if not os.path.exists(avro_dir):
            os.makedirs(avro_dir)
        
        # 如果schema文件不存在，创建默认schema
        if not os.path.exists(schema_path):
            self._create_default_schema(schema_path)
        
        # 加载schema
        with open(schema_path, "r") as schema_file:
            schema_str = schema_file.read()
        
        # 处理不同版本的avro
        try:
            # 新版本avro
            self.schema = avro_parse(schema_str)
        except AttributeError:
            # 旧版本avro
            self.schema = schema.parse(schema_str)
        
        self.writer = DatumWriter(self.schema)
        self.reader = DatumReader(self.schema)
    
    def _create_default_schema(self, schema_path):
        """创建默认Avro schema文件"""
        default_schema = {
            "namespace": "idp.messaging",
            "type": "record",
            "name": "MessageEnvelope",
            "fields": [
                {"name": "event_type", "type": "string"},
                {"name": "payload", "type": {"type": "map", "values": "string"}},
                {"name": "occurred_at", "type": "string"},
                {"name": "source", "type": "string"},
                {"name": "correlation_id", "type": "string"}
            ]
        }
        
        # 创建目录
        os.makedirs(os.path.dirname(schema_path), exist_ok=True)
        
        # 写入schema文件
        with open(schema_path, 'w') as f:
            json.dump(default_schema, f, indent=2)
        
        print(f"[avro] 已创建默认schema文件: {schema_path}")
    
    def encode(self, envelope: MessageEnvelope) -> bytes:
        """Encode a MessageEnvelope into Avro binary format"""
        # 转换复杂payload为字符串值，以兼容Avro map
        string_payload = {
            k: json.dumps(v) if not isinstance(v, (str, int, float, bool)) else str(v)
            for k, v in envelope.payload.items()
        }
        
        # 创建Avro记录
        avro_record = {
            "event_type": envelope.event_type,
            "payload": string_payload,
            "occurred_at": envelope.occurred_at.isoformat(),
            "source": envelope.source,
            "correlation_id": envelope.correlation_id
        }
        
        # 序列化使用Avro
        bytes_io = io.BytesIO()
        encoder = BinaryEncoder(bytes_io)
        self.writer.write(avro_record, encoder)
        
        return bytes_io.getvalue()
    
    def decode(self, raw: bytes) -> MessageEnvelope:
        """Decode Avro binary format into a MessageEnvelope"""
        # 反序列化使用Avro
        bytes_io = io.BytesIO(raw)
        decoder = BinaryDecoder(bytes_io)
        avro_record = self.reader.read(decoder)
        
        # 转换Avro payload回复杂对象
        payload = {}
        for k, v in avro_record["payload"].items():
            try:
                # 尝试解析为JSON复杂对象
                payload[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                # 否则保持为字符串
                payload[k] = v
        
        return MessageEnvelope(
            event_type=avro_record["event_type"],
            payload=payload,
            occurred_at=datetime.fromisoformat(avro_record["occurred_at"]),
            source=avro_record["source"],
            correlation_id=avro_record["correlation_id"]
        )


# 注册编解码器
try:
    register_codec("avro", AvroMessageCodec())
    print("[codec] Avro编解码器已注册")
except Exception as e:
    print(f"[codec] Avro编解码器注册失败: {str(e)}") 
from __future__ import annotations

import json
import pytest

from bento.messaging.codec.json import JsonCodec
from bento.messaging.envelope import MessageEnvelope


@pytest.mark.asyncio
async def test_encode_decode_roundtrip():
    codec = JsonCodec()
    env = MessageEnvelope(event_type="order.OrderCreated", payload={"order_id": "123"})
    data = codec.encode(env)
    decoded = codec.decode(data)
    assert isinstance(decoded, MessageEnvelope)
    assert decoded.event_type == env.event_type
    assert decoded.payload == env.payload


@pytest.mark.asyncio
async def test_decode_invalid_json_raises():
    codec = JsonCodec()
    with pytest.raises(json.JSONDecodeError):
        codec.decode(b"{not-json}")


@pytest.mark.asyncio
async def test_decode_missing_required_field_raises():
    codec = JsonCodec()
    # Missing occurred_at
    env_dict = {
        "event_type": "x",
        "payload": {"a": 1},
        # "occurred_at": ...
    }
    data = json.dumps(env_dict).encode("utf-8")
    with pytest.raises(KeyError):
        codec.decode(data)

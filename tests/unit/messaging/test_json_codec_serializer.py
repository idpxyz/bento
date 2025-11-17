from __future__ import annotations

import pytest

from bento.messaging.codec.json import JsonCodec
from bento.messaging.envelope import MessageEnvelope


@pytest.mark.asyncio
async def test_json_codec_serializer_raises_for_unknown_object():
    codec = JsonCodec()

    class X:
        pass

    env = MessageEnvelope(event_type="t", payload={"x": X()})
    with pytest.raises(TypeError):
        codec.encode(env)

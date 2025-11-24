from __future__ import annotations

import pytest

from bento.messaging.codec import decode, encode


@pytest.mark.asyncio
async def test_codec_module_encode_decode_roundtrip():
    obj = {"a": 1, "b": "x"}
    data = encode(obj)
    out = decode(data)
    assert out == obj

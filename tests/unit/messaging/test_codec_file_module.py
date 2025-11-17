from __future__ import annotations

import importlib.util
import sys

import pytest


@pytest.mark.asyncio
async def test_codec_py_module_encode_decode_roundtrip():
    path = "src/bento/messaging/codec.py"
    spec = importlib.util.spec_from_file_location("bento.messaging.codec_file", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    data = mod.encode({"x": 1})
    out = mod.decode(data)
    assert out == {"x": 1}

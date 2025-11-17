from __future__ import annotations

import pytest

from bento.messaging.envelope import MessageEnvelope


@pytest.mark.asyncio
async def test_to_dict_from_dict_roundtrip_with_iso_datetime():
    env = MessageEnvelope(event_type="x.y", payload={"a": 1})
    d = env.to_dict()
    # occurred_at as iso string
    assert isinstance(d["occurred_at"], str)
    env2 = MessageEnvelope.from_dict(d)
    assert env2.event_type == env.event_type
    assert env2.payload == env.payload
    assert env2.occurred_at == env.occurred_at


@pytest.mark.asyncio
async def test_with_causation_creates_new_envelope():
    env = MessageEnvelope(event_type="x", payload={})
    derived = env.with_causation(env.event_id)
    assert derived is not env
    assert derived.causation_id == env.event_id

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from bento.domain.domain_event import DomainEvent
from bento.persistence.outbox.listener import persist_events_DISABLED


@dataclass(frozen=True)
class TestEvt(DomainEvent):
    kind: str = "t"


class FakeSession:
    def __init__(self, uow):
        self.info: Mapping[str, Any] = {"uow": uow}  # ✅ 显式类型注解
        self.added: list = []

    def execute(self, stmt):
        # Simulate empty existing ids result
        return []

    def add(self, obj):
        self.added.append(obj)


class UowStub:
    def __init__(self, events):
        self.pending_events = events


def test_outbox_listener_manual_call_persists_event_via_fake_session():
    evt = TestEvt()
    uow = UowStub([evt])
    sess = FakeSession(uow)

    persist_events_DISABLED(sess, None)

    # One OutboxRecord should have been added
    assert len(sess.added) == 1
    rec = sess.added[0]
    assert rec.type == "TestEvt"

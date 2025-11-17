from dataclasses import dataclass

from bento.domain.domain_event import DomainEvent
from bento.persistence.sqlalchemy.outbox_listener import persist_events_DISABLED


@dataclass(frozen=True)
class TestEvt(DomainEvent):
    kind: str = "t"


class FakeSession:
    def __init__(self, uow):
        self.info = {"uow": uow}
        self.added = []

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

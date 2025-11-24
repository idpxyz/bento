from __future__ import annotations

from bento.domain.aggregate import AggregateRoot
from bento.domain.domain_event import DomainEvent


class AggStub(AggregateRoot):
    pass


def test_aggregate_add_and_clear_events_and_copy():
    agg = AggStub(id="agg-1")
    e1 = DomainEvent(name="E1")
    e2 = DomainEvent(name="E2")

    # add events
    agg.add_event(e1)
    agg.add_event(e2)
    events_copy = agg.events

    # returns a copy and preserves order
    assert events_copy == [e1, e2]
    events_copy.append(DomainEvent(name="E3"))

    # internal list not affected
    assert agg.events == [e1, e2]

    # clear
    agg.clear_events()
    assert agg.events == []

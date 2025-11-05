# ─────────────────────────  pulsar_bus.py  ──────────────────────────
"""Apache Pulsar adapter for AbstractEventBus (Exactly‑Once capable).

* Requires **pulsar‑client >= 3.2** with transaction support enabled.
* One producer per tenant/topic; created lazily and cached.
* Implements *at‑least‑once* semantics by default, *exactly‑once* when
  `enable_tx=True` and the broker supports it.
* Any failure raises Exception so UoW / Projector can retry.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Sequence

import pulsar
from pulsar import Client, Producer, Transaction

from idp.framework.domain.base.event import DomainEvent

from idp.framework.infrastructure.messaging.core.event_bus import AbstractEventBus

logger = logging.getLogger(__name__)

# ------------------------------ helpers -----------------------------


def _default_serializer(evt: DomainEvent) -> bytes:
    """Serialize event payload as utf‑8 JSON."""
    return json.dumps(evt.to_payload(), separators=(',', ':')).encode()

# ---------------------------- Pulsar Bus ---------------------------


class PulsarEventBus(AbstractEventBus):
    """Publish DomainEvents to Pulsar, tenant‑scoped topic template.

    Parameters
    ----------
    client : pulsar.Client
        Pre‑configured Pulsar client (thread‑safe).
    topic_tpl : str, default "tenant-{tenant}"
        Template expanded with `tenant_id` from event (or "default").
    enable_tx : bool, default True
        If broker supports transactions, wrap batch in Pulsar Tx for
        exactly‑once semantics.
    props_fn : callable, optional
        Custom function `(DomainEvent) -> dict[str,str]` to attach message
        properties (default adds `event_id`, `schema_id`).
    """

    def __init__(
        self,
        client: Client,
        *,
        topic_tpl: str = "tenant-{tenant}",
        enable_tx: bool = True,
        props_fn: callable | None = None,
        serializer: callable[[DomainEvent], bytes] = _default_serializer,
    ) -> None:
        self._cli = client
        self._topic_tpl = topic_tpl
        self._enable_tx = enable_tx
        self._props_fn = props_fn or self._default_props
        self._ser = serializer
        self._producers: dict[str, Producer] = {}
        self._lock = asyncio.Lock()          # protect producer cache

    # --------------------------- API ----------------------------
    # type: ignore[override]
    async def publish(self, events: Sequence[DomainEvent]) -> None:
        if not events:
            return
        # Group by tenant/topic → minimise producer churn
        by_topic: dict[str, list[DomainEvent]] = {}
        for e in events:
            t = self._topic_tpl.format(tenant=(e.tenant_id or "default"))
            by_topic.setdefault(t, []).append(e)

        for topic, evts in by_topic.items():
            prod = await self._get_producer(topic)
            txn: Transaction | None = None
            try:
                if self._enable_tx:
                    txn = self._cli.new_transaction().build()
                for ev in evts:
                    prod.send_async(
                        self._ser(ev),
                        partition_key=str(ev.aggregate_id or ev.event_id),
                        txn=txn,
                        properties=self._props_fn(ev),
                    )
                prod.flush()        # wait for async sends
                if txn:
                    txn.commit()
            except Exception:
                if txn:
                    try:
                        txn.abort()
                    except Exception:  # pragma: no cover
                        logger.error("Txn abort failed", exc_info=True)
                raise               # bubble up for retry

    # ------------------------ internals -------------------------
    async def _get_producer(self, topic: str) -> Producer:
        if topic in self._producers:
            return self._producers[topic]
        async with self._lock:
            if topic in self._producers:
                return self._producers[topic]
            # create producer synchronously (Pulsar client is sync) inside thread loop
            loop = asyncio.get_running_loop()
            prod = await loop.run_in_executor(
                None,
                lambda: self._cli.create_producer(
                    topic=topic,
                    batching_enabled=True,
                    batching_max_publish_delay_ms=10,
                    compression_type=pulsar.CompressionType.LZ4,
                    send_timeout_millis=0,
                    block_if_queue_full=True,
                ),
            )
            self._producers[topic] = prod
            return prod

    @staticmethod
    def _default_props(evt: DomainEvent) -> Dict[str, str]:
        return {
            "event_id": str(evt.event_id),
            "schema_id": evt.schema_id or "",  # empty str allowed
            "schema_ver": str(evt.schema_version),
        }

# ───────────────────────────── End of file ─────────────────────────────

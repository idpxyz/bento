# src/bento/adapters/event_store/clickhouse_event_store.py
from typing import Any

from clickhouse_driver import Client as ClickHouseClient


class ClickHouseEventStore:
    def __init__(self, host: str = "localhost", port: int = 9000, database: str = "events"):
        self.client = ClickHouseClient(host=host, port=port, database=database)
        self._ensure_tables()

    def _ensure_tables(self):
        self.client.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id String,
            event_type String,
            aggregate_id String,
            aggregate_type String,
            version UInt32,
            payload String,
            metadata String,
            timestamp DateTime DEFAULT now(),
            _ingest_time DateTime DEFAULT now()
        ) ENGINE = ReplacingMergeTree()
        ORDER BY (aggregate_type, aggregate_id, version)
        PARTITION BY toYYYYMM(timestamp)
        """)

    async def save_events(self, events: list[dict[str, Any]]):
        if not events:
            return

        query = """
        INSERT INTO events (
            event_id, event_type, aggregate_id,
            aggregate_type, version, payload, metadata
        ) VALUES
        """

        values = []
        for event in events:
            values.append(
                (
                    str(event["event_id"]),
                    event["event_type"],
                    str(event["aggregate_id"]),
                    event["aggregate_type"],
                    event.get("version", 1),
                    event.get("payload", "{}"),
                    event.get("metadata", "{}"),
                )
            )

        self.client.execute(query, values)

    async def get_events(
        self, aggregate_type: str, aggregate_id: str, from_version: int = 0
    ) -> list[dict[str, Any]]:
        rows = self.client.execute(
            """
        SELECT
            event_id, event_type, aggregate_id,
            aggregate_type, version, payload, metadata, timestamp
        FROM events
        WHERE aggregate_type = %(aggregate_type)s
        AND aggregate_id = %(aggregate_id)s
        AND version >= %(from_version)s
        ORDER BY version ASC
        """,
            {
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "from_version": from_version,
            },
        )

        return [
            {
                "event_id": r[0],
                "event_type": r[1],
                "aggregate_id": r[2],
                "aggregate_type": r[3],
                "version": r[4],
                "payload": r[5],
                "metadata": r[6],
                "timestamp": r[7],
            }
            for r in rows
        ]

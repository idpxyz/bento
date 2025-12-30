import hashlib
import json
import uuid
from datetime import UTC, datetime


def canonical_hash(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",",":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def now_iso() -> str:
    return datetime.now(UTC).isoformat()

def new_event_id() -> str:
    return uuid.uuid4().hex

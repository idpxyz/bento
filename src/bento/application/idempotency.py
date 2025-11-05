from typing import Protocol

class IdempotencyStore(Protocol):
    async def check_and_set(self, key: str, ttl_sec: int = 600) -> bool: ...

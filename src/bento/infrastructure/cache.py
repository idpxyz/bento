from typing import Any


class Cache:
    async def get(self, key: str) -> Any: ...

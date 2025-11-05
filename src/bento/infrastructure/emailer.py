from typing import Any


class Emailer:
    async def send(self, to: str, subject: str, body: str) -> Any: ...

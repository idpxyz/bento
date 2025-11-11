# infrastructure/opa_client.py
import os

import httpx
from infrastructure.settings import settings


class OPAExecutor:
    def __init__(self):
        self.url: str = settings.opa_url

    async def allow(self, input_data: dict) -> tuple[bool, dict]:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.url}/v1/data/policy/allow", json={"input": input_data}, timeout=2)
            r.raise_for_status()
            allowed = bool(r.json().get("result"))
            return allowed, {}

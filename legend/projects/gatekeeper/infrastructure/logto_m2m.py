# infrastructure/logto_m2m.py
import os

import httpx
from cachetools import TTLCache, cached

ISSUER = os.getenv("LOGTO_ENDPOINT").rstrip("/") + "/oidc"
_cache = TTLCache(maxsize=1, ttl=300)


@cached(_cache)
def get_m2m_token():
    data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("LOGTO_M2M_ID"),
        "client_secret": os.getenv("LOGTO_M2M_SECRET"),
        "scope": "management:read management:write"
    }
    r = httpx.post(f"{ISSUER}/token", data=data, timeout=5)
    r.raise_for_status()
    tok = r.json()
    _cache.ttl = max(30, tok["expires_in"] - 60)
    return tok["access_token"]

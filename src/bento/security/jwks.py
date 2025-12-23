import json
import httpx
from jose import jwk
from jose.utils import base64url_decode
from app.settings import settings
from app.platform.runtime.redis import init_redis

JWKS_CACHE_KEY = "loms:auth:jwks"

async def fetch_jwks() -> dict:
    if not settings.auth_issuer:
        return {"keys": []}
    url = settings.auth_issuer.rstrip("/") + "/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()

async def get_jwks() -> dict:
    rds = await init_redis()
    cached = await rds.get(JWKS_CACHE_KEY)
    if cached:
        return json.loads(cached)
    jwks = await fetch_jwks()
    await rds.set(JWKS_CACHE_KEY, json.dumps(jwks), ex=settings.jwks_cache_ttl_seconds)
    return jwks

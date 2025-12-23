from app.settings import settings
from app.domain.errors import ContractError

try:
    from jose import jwt
    from jose.exceptions import JWTError
except Exception:  # pragma: no cover
    jwt = None
    JWTError = Exception

from app.platform.security.jwks import get_jwks

async def verify_jwt(token: str) -> dict:
    # Dev bypass when issuer/audience not configured
    if not settings.auth_issuer or not settings.auth_audience:
        return {"sub": "dev", "scope": "dev", "tenant_id": None}

    if jwt is None:
        raise ContractError.unauthorized(details={"reason": "jwt_lib_missing"})

    jwks = await get_jwks()
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")

    key = None
    for k in jwks.get("keys", []):
        if k.get("kid") == kid:
            key = k
            break
    if not key:
        raise ContractError.unauthorized(details={"reason": "jwks_kid_not_found"})

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[headers.get("alg","RS256")],
            audience=settings.auth_audience,
            issuer=settings.auth_issuer,
        )
        return claims
    except JWTError as e:
        raise ContractError.unauthorized(details={"reason": "jwt_invalid", "error": str(e)})

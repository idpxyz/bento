from app.domain.errors import ContractError

def require_scope(claims: dict, required: str):
    scopes = claims.get("scope") or claims.get("scp") or ""
    if isinstance(scopes, list):
        scopes = " ".join(scopes)
    if required not in scopes.split():
        raise ContractError.forbidden(details={"required_scope": required})

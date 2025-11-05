from dataclasses import dataclass

@dataclass
class RequestContext:
    tenant_id: str | None = None
    user_id: str | None = None
    scopes: list[str] | None = None

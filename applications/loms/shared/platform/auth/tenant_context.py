from fastapi import Request


async def tenant_context_middleware(request: Request, call_next):
    # P0 stub: later replace with real authn/authz integration
    request.state.tenant_id = request.headers.get("x-tenant-id", "demo-tenant")
    return await call_next(request)

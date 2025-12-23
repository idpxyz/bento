# Security Providers

Pre-built authenticators for popular identity providers.

## Available Providers

| Provider | Class | Identity Platform |
|----------|-------|-------------------|
| Logto | `LogtoAuthenticator` | [logto.io](https://logto.io) |
| Auth0 | `Auth0Authenticator` | [auth0.com](https://auth0.com) |
| Keycloak | `KeycloakAuthenticator` | [keycloak.org](https://keycloak.org) |

## Requirements

```bash
pip install PyJWT[crypto]
```

## Logto

```python
from bento.security.providers import LogtoAuthenticator
from bento.security import add_security_middleware

authenticator = LogtoAuthenticator(
    endpoint="https://your-app.logto.app",
    app_id="your-app-id",
)

add_security_middleware(app, authenticator)
```

### Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `endpoint` | Logto endpoint URL | Required |
| `app_id` | Application ID | Required |
| `permissions_claim` | Claim for permissions | `"permissions"` |
| `roles_claim` | Claim for roles | `"roles"` |

### Token Claims

```json
{
  "sub": "user-id",
  "permissions": ["read", "write"],
  "roles": ["admin"],
  "email": "user@example.com",
  "tenant_id": "tenant-123"
}
```

## Auth0

```python
from bento.security.providers import Auth0Authenticator

authenticator = Auth0Authenticator(
    domain="your-tenant.auth0.com",
    audience="https://your-api.example.com",
)
```

### Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `domain` | Auth0 tenant domain | Required |
| `audience` | API audience | Required |
| `namespace` | Custom claims namespace | `""` |

### Namespaced Claims

Auth0 requires custom claims to be namespaced:

```python
authenticator = Auth0Authenticator(
    domain="your-tenant.auth0.com",
    audience="https://your-api.example.com",
    namespace="https://your-app.com/",
)
```

Token claims with namespace:
```json
{
  "sub": "auth0|user-id",
  "https://your-app.com/permissions": ["read", "write"],
  "https://your-app.com/roles": ["admin"],
  "https://your-app.com/tenant_id": "tenant-123"
}
```

## Keycloak

```python
from bento.security.providers import KeycloakAuthenticator

authenticator = KeycloakAuthenticator(
    server_url="https://keycloak.example.com",
    realm="your-realm",
    client_id="your-client-id",
)
```

### Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `server_url` | Keycloak server URL | Required |
| `realm` | Realm name | Required |
| `client_id` | Client ID | Required |
| `use_realm_roles` | Extract realm roles | `True` |
| `use_client_roles` | Extract client roles | `True` |

### Role Extraction

Keycloak has two types of roles:

```json
{
  "sub": "user-uuid",
  "realm_access": {
    "roles": ["admin", "user"]
  },
  "resource_access": {
    "your-client-id": {
      "roles": ["client-admin"]
    }
  }
}
```

Both are extracted and combined into `CurrentUser.roles`.

## Custom Provider

Create your own provider by extending `JWTAuthenticatorBase`:

```python
from bento.security.providers import JWTAuthenticatorBase
from bento.security.providers.base import JWTConfig
from bento.security import CurrentUser

class MyAuthenticator(JWTAuthenticatorBase):
    def __init__(self, issuer_url: str, client_id: str):
        config = JWTConfig(
            jwks_url=f"{issuer_url}/.well-known/jwks.json",
            issuer=issuer_url,
            audience=client_id,
        )
        super().__init__(config)

    def _extract_user_from_claims(self, claims: dict) -> CurrentUser:
        return CurrentUser(
            id=claims["sub"],
            permissions=claims.get("permissions", []),
            roles=claims.get("roles", []),
        )
```

## Multi-Tenancy Integration

All providers extract `tenant_id` from token claims:

```python
from bento.multitenancy import TokenTenantResolver, add_tenant_middleware

# Security middleware first
add_security_middleware(app, LogtoAuthenticator(...))

# Then tenant middleware using token resolver
add_tenant_middleware(
    app,
    resolver=TokenTenantResolver(claim_name="tenant_id"),
)
```

The `TokenTenantResolver` reads tenant from `request.state.user.metadata["tenant_id"]`.

## M2M (Machine-to-Machine) Authentication

All providers support M2M authentication for service-to-service communication.

### Enable M2M

```python
# Logto with M2M
authenticator = LogtoAuthenticator(
    endpoint="https://your-app.logto.app",
    app_id="your-app-id",
    # M2M credentials
    client_id="m2m-client-id",
    client_secret="m2m-client-secret",
    m2m_permissions=["api:access"],
    m2m_roles=["service"],
)

# Auth0 with M2M
authenticator = Auth0Authenticator(
    domain="your-tenant.auth0.com",
    audience="https://your-api.example.com",
    client_id="m2m-client-id",
    client_secret="m2m-client-secret",
)

# Keycloak with M2M
authenticator = KeycloakAuthenticator(
    server_url="https://keycloak.example.com",
    realm="your-realm",
    client_id="your-client-id",
    client_secret="your-client-secret",
)
```

### M2M Request Detection

Requests are detected as M2M when:

1. **Explicit header**: `X-M2M-Auth: true`
2. **Client credentials headers**: `X-Client-ID` + `X-Client-Secret`
3. **Basic auth**: `Authorization: Basic <base64(client_id:client_secret)>`

### M2M User

M2M clients get a `CurrentUser` with:

```python
CurrentUser(
    id="m2m:client-id",
    permissions=["api:access"],  # from m2m_permissions
    roles=["service"],           # from m2m_roles
    metadata={"type": "m2m", "client_id": "..."},
)
```

### Get Token for Outbound Calls

When your service needs to call another service:

```python
# Get access token using Client Credentials Grant
token = await authenticator.get_m2m_token(scope="api:read api:write")

# Use token in outbound request
headers = {"Authorization": f"Bearer {token}"}
response = await httpx.get("https://other-service/api", headers=headers)
```

## Error Handling

All providers return `None` on authentication failure:
- Missing token
- Invalid token
- Expired token
- Invalid signature
- Wrong issuer/audience

The middleware handles this and either:
- Continues (if `require_auth=False`)
- Returns 401 (if `require_auth=True`)

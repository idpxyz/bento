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

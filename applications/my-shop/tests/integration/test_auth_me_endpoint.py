"""Test script for /api/v1/auth/me endpoint with tenant context."""

from fastapi.testclient import TestClient
from runtime.bootstrap import create_app


def main():
    """Test /api/v1/auth/me endpoint."""
    app = create_app()
    client = TestClient(app)

    print("\n" + "="*70)
    print("🔐 Testing /api/v1/auth/me Endpoint with Tenant Context")
    print("="*70)

    # Test 1: Without tenant
    print("\n1️⃣  GET /api/v1/auth/me (without tenant):")
    response = client.get("/api/v1/auth/me")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response:")
    print(f"     - id: {data.get('id')}")
    print(f"     - permissions: {data.get('permissions')}")
    print(f"     - roles: {data.get('roles')}")
    print(f"     - tenant_id: {data.get('tenant_id')}")
    print(f"     - metadata: {data.get('metadata')}")
    assert data.get('id') == 'demo-user', "User ID should be demo-user"
    assert data.get('tenant_id') is None, "Tenant ID should be None"
    print(f"   ✅ Response includes tenant_id field (None)")

    # Test 2: With tenant
    print("\n2️⃣  GET /api/v1/auth/me (with X-Tenant-ID: tenant-a):")
    response = client.get(
        "/api/v1/auth/me",
        headers={"X-Tenant-ID": "tenant-a"}
    )
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response:")
    print(f"     - id: {data.get('id')}")
    print(f"     - permissions: {data.get('permissions')}")
    print(f"     - roles: {data.get('roles')}")
    print(f"     - tenant_id: {data.get('tenant_id')}")
    print(f"     - metadata: {data.get('metadata')}")
    assert data.get('id') == 'demo-user', "User ID should be demo-user"
    assert data.get('tenant_id') == 'tenant-a', "Tenant ID should be tenant-a"
    print(f"   ✅ Response includes tenant_id field (tenant-a)")

    # Test 3: Different tenant
    print("\n3️⃣  GET /api/v1/auth/me (with X-Tenant-ID: tenant-xyz):")
    response = client.get(
        "/api/v1/auth/me",
        headers={"X-Tenant-ID": "tenant-xyz"}
    )
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response:")
    print(f"     - id: {data.get('id')}")
    print(f"     - tenant_id: {data.get('tenant_id')}")
    assert data.get('tenant_id') == 'tenant-xyz', "Tenant ID should be tenant-xyz"
    print(f"   ✅ Response includes tenant_id field (tenant-xyz)")

    # Test 4: Verify response schema
    print("\n4️⃣  Verifying response schema:")
    response = client.get(
        "/api/v1/auth/me",
        headers={"X-Tenant-ID": "test-tenant"}
    )
    data = response.json()
    required_fields = {'id', 'permissions', 'roles', 'tenant_id', 'metadata'}
    actual_fields = set(data.keys())
    print(f"   Required fields: {required_fields}")
    print(f"   Actual fields: {actual_fields}")
    assert required_fields == actual_fields, f"Schema mismatch: {required_fields} vs {actual_fields}"
    print(f"   ✅ Response schema is correct")

    print("\n" + "="*70)
    print("✅ All /api/v1/auth/me endpoint tests passed!")
    print("="*70)

    print("\n📊 Response Schema:")
    print("""
    {
        "id": "demo-user",
        "permissions": ["*"],
        "roles": ["admin"],
        "tenant_id": "tenant-a",  # ✨ New field
        "metadata": {
            "stub": true,
            "environment": "development",
            "username": "demo"
        }
    }
    """)

    print("\n💡 Usage:")
    print("""
    # Without tenant
    curl http://localhost:8000/api/v1/auth/me

    # With tenant
    curl -H "X-Tenant-ID: tenant-a" http://localhost:8000/api/v1/auth/me
    """)

    print("\n📚 Documentation:")
    print("   See: applications/my-shop/docs/SECURITY_INTEGRATION.md")
    print()


if __name__ == "__main__":
    main()

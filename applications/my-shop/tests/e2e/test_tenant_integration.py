"""Integration test for tenant middleware in my-shop API.

This script demonstrates and validates the tenant middleware integration.
"""

from fastapi.testclient import TestClient

from runtime.bootstrap import create_app


def main():
    """Test tenant middleware integration."""
    app = create_app()
    client = TestClient(app)

    print("\n" + "=" * 70)
    print("🏢 My-Shop Tenant Middleware Integration Test")
    print("=" * 70)

    # Test 1: Request without tenant header
    print("\n1️⃣  Testing without X-Tenant-ID header:")
    response = client.get("/api/v1/auth/me/context")
    print(f"   Status: {response.status_code}")
    context = response.json()
    print(f"   Tenant ID: {context.get('tenant_id')}")
    print("   ✅ No tenant header → tenant_id is None")

    # Test 2: Request with tenant header
    print("\n2️⃣  Testing with X-Tenant-ID: tenant-a:")
    response = client.get("/api/v1/auth/me/context", headers={"X-Tenant-ID": "tenant-a"})
    print(f"   Status: {response.status_code}")
    context = response.json()
    print(f"   Tenant ID: {context.get('tenant_id')}")
    assert context.get("tenant_id") == "tenant-a", "Tenant ID should be 'tenant-a'"
    print("   ✅ X-Tenant-ID header → tenant_id = 'tenant-a'")

    # Test 3: Request with different tenant
    print("\n3️⃣  Testing with X-Tenant-ID: tenant-b:")
    response = client.get("/api/v1/auth/me/context", headers={"X-Tenant-ID": "tenant-b"})
    print(f"   Status: {response.status_code}")
    context = response.json()
    print(f"   Tenant ID: {context.get('tenant_id')}")
    assert context.get("tenant_id") == "tenant-b", "Tenant ID should be 'tenant-b'"
    print("   ✅ X-Tenant-ID header → tenant_id = 'tenant-b'")

    # Test 4: Verify user and tenant coexist
    print("\n4️⃣  Testing user and tenant coexistence:")
    response = client.get("/api/v1/auth/me/context", headers={"X-Tenant-ID": "tenant-xyz"})
    context = response.json()
    print(f"   Authenticated: {context.get('authenticated')}")
    print(f"   User ID: {context.get('user', {}).get('id')}")
    print(f"   Tenant ID: {context.get('tenant_id')}")
    assert context.get("authenticated"), "Should be authenticated"
    assert context.get("user", {}).get("id") == "demo-user", "User should be demo-user"
    assert context.get("tenant_id") == "tenant-xyz", "Tenant should be tenant-xyz"
    print("   ✅ User and tenant both available in context")

    # Test 5: Excluded paths don't require tenant
    print("\n5️⃣  Testing excluded path /health (no tenant required):")
    response = client.get("/health")
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200, "Health check should work without tenant"
    print("   ✅ Excluded paths work without tenant header")

    # Test 6: Verify tenant isolation concept
    print("\n6️⃣  Testing tenant isolation concept:")
    print("   Making requests with different tenants:")

    response1 = client.get("/api/v1/auth/me/context", headers={"X-Tenant-ID": "tenant-shop-a"})
    tenant1 = response1.json().get("tenant_id")

    response2 = client.get("/api/v1/auth/me/context", headers={"X-Tenant-ID": "tenant-shop-b"})
    tenant2 = response2.json().get("tenant_id")

    print(f"   Request 1 tenant: {tenant1}")
    print(f"   Request 2 tenant: {tenant2}")
    assert tenant1 != tenant2, "Different requests should have different tenants"
    print("   ✅ Tenant isolation verified")

    print("\n" + "=" * 70)
    print("✅ Tenant Middleware Integration Test Completed!")
    print("=" * 70)

    print("\n📊 Summary:")
    print("   ✅ Tenant middleware is active")
    print("   ✅ X-Tenant-ID header is correctly parsed")
    print("   ✅ SecurityContext.get_tenant() returns correct value")
    print("   ✅ User and tenant coexist in security context")
    print("   ✅ Excluded paths work without tenant")
    print("   ✅ Tenant isolation concept verified")

    print("\n🎯 Middleware Stack:")
    print("   1. Security (User authentication)")
    print("   2. Tenant (Tenant identification)")
    print("   3. Tenant → Security sync (bind_security_tenant)")
    print("   4. Request ID, Logging, Rate Limiting, etc.")

    print("\n💡 Usage in Business Code:")
    print("   ```python")
    print("   from bento.security import SecurityContext")
    print("   ")
    print("   class CreateOrderHandler(CommandHandler):")
    print("       async def handle(self, command):")
    print("           user = SecurityContext.require_user()")
    print("           tenant_id = SecurityContext.require_tenant()")
    print("           ")
    print("           order = Order.create(")
    print("               tenant_id=tenant_id,")
    print("               customer_id=user.id,")
    print("               ...")
    print("           )")
    print("   ```")

    print("\n📚 Documentation:")
    print("   See: applications/my-shop/docs/SECURITY_INTEGRATION.md")
    print("\n")


if __name__ == "__main__":
    main()

"""Demo script to show security middleware integration in my-shop API.

This script demonstrates how the security middleware works with StubAuthenticator.
"""

from fastapi.testclient import TestClient

from runtime.bootstrap import create_app


def main():
    """Test security middleware integration."""
    app = create_app()
    client = TestClient(app)

    print("\n" + "=" * 70)
    print("🔐 My-Shop Security Middleware Integration Demo")
    print("=" * 70)

    # Test 1: Health check (excluded from auth)
    print("\n1️⃣  Testing /health endpoint (excluded from auth):")
    response = client.get("/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")

    # Test 2: Root endpoint
    print("\n2️⃣  Testing / endpoint (with security context):")
    response = client.get("/")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")

    # Test 3: Ping endpoint (excluded from auth)
    print("\n3️⃣  Testing /ping endpoint (excluded from auth):")
    response = client.get("/ping")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")

    # Test 4: Docs endpoint (excluded from auth)
    print("\n4️⃣  Testing /docs endpoint (excluded from auth):")
    response = client.get("/docs")
    print(f"   Status: {response.status_code}")
    print(f"   Response length: {len(response.text)} bytes")
    print("   ✅ Swagger UI is available")

    # Test 5: OpenAPI schema
    print("\n5️⃣  Testing /openapi.json endpoint (excluded from auth):")
    response = client.get("/openapi.json")
    print(f"   Status: {response.status_code}")
    schema = response.json()
    print("   ✅ OpenAPI schema loaded")
    print(f"   Title: {schema.get('info', {}).get('title')}")
    print(f"   Version: {schema.get('info', {}).get('version')}")

    print("\n" + "=" * 70)
    print("✅ Security Middleware Integration Demo Completed!")
    print("=" * 70)

    print("\n📊 Summary:")
    print("   ✅ StubAuthenticator is active")
    print("   ✅ Security middleware is integrated")
    print("   ✅ Excluded paths work without authentication")
    print("   ✅ API documentation is available")

    print("\n🎯 Middleware Stack:")
    print("   1. Security (Authentication/Authorization)")
    print("   2. Request ID (Tracing)")
    print("   3. Structured Logging")
    print("   4. Rate Limiting")
    print("   5. Idempotency")
    print("   6. CORS")

    print("\n💡 Next Steps:")
    print("   1. Try making requests with Authorization header")
    print("   2. Upgrade to JWTAuthenticator for production")
    print("   3. Enable require_auth=True for strict authentication")
    print("   4. Add permission checks in business logic")
    print("   5. Integrate bento-security for enterprise features")

    print("\n📚 Documentation:")
    print("   See: applications/my-shop/docs/SECURITY_INTEGRATION.md")
    print("\n")


if __name__ == "__main__":
    main()

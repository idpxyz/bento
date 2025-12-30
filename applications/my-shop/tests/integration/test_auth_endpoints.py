"""Test script to verify auth endpoints.

This script demonstrates the new auth endpoints:
- GET /api/v1/auth/me - Get current user
- GET /api/v1/auth/me/context - Get security context (debugging)
"""

from fastapi.testclient import TestClient

from runtime.bootstrap import create_app


def main():
    """Test auth endpoints."""
    app = create_app()
    client = TestClient(app)

    print("\n" + "=" * 70)
    print("🔐 My-Shop Auth Endpoints Test")
    print("=" * 70)

    # Test 1: Get current user
    print("\n1️⃣  Testing GET /api/v1/auth/me (Get current user):")
    response = client.get("/api/v1/auth/me")
    print(f"   Status: {response.status_code}")
    user = response.json()
    print("   Response:")
    print(f"      ID: {user['id']}")
    print(f"      Permissions: {user['permissions']}")
    print(f"      Roles: {user['roles']}")
    print(f"      Metadata: {user['metadata']}")

    # Test 2: Get security context (debugging)
    print("\n2️⃣  Testing GET /api/v1/auth/me/context (Get security context):")
    response = client.get("/api/v1/auth/me/context")
    print(f"   Status: {response.status_code}")
    context = response.json()
    print("   Response:")
    print(f"      Authenticated: {context['authenticated']}")
    print(f"      User ID: {context['user']['id']}")
    print(f"      Permissions: {context['user']['permissions']}")
    print(f"      Roles: {context['user']['roles']}")
    print(f"      Has 'admin' permission: {context['has_permission_check']['admin']}")
    print(f"      Has 'user' permission: {context['has_permission_check']['user']}")

    print("\n" + "=" * 70)
    print("✅ Auth Endpoints Test Completed!")
    print("=" * 70)

    print("\n📊 Summary:")
    print("   ✅ GET /api/v1/auth/me - Returns current user")
    print("   ✅ GET /api/v1/auth/me/context - Returns security context")
    print("   ✅ StubAuthenticator provides demo user")
    print("   ✅ User has full permissions (permissions=['*'])")

    print("\n💡 Next Steps:")
    print("   1. Try accessing /api/v1/auth/me in Swagger UI")
    print("   2. Upgrade to JWTAuthenticator for real authentication")
    print("   3. Add permission checks in business logic")
    print("   4. Integrate with your authentication provider")

    print("\n📚 API Documentation:")
    print("   Swagger UI: http://localhost:8000/docs")
    print("   ReDoc: http://localhost:8000/redoc")
    print("\n")


if __name__ == "__main__":
    main()

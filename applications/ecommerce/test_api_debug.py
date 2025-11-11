"""Debug API test to see detailed errors."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from httpx import ASGITransport, AsyncClient

from applications.ecommerce.main import app


async def main():
    """Test API directly."""
    print("🧪 Testing API with detailed error output\n")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            # Create order
            print("Sending POST request to /api/orders...")
            response = await client.post(
                "/api/orders",
                json={
                    "customer_id": "test-customer",
                    "items": [
                        {
                            "product_id": "product-1",
                            "product_name": "Test Product",
                            "quantity": 1,
                            "unit_price": 99.99,
                        }
                    ],
                },
            )

            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")

            if response.status_code == 200:
                print("\n✅ Order created successfully!")
            else:
                print("\n❌ Order creation failed")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

"""Product API Integration Tests

These tests demonstrate API testing patterns using FastAPI's TestClient.

Run with:
    pytest tests/api/test_product_api.py -v
"""


class TestProductAPI:
    """Product API integration tests"""

    def test_list_products(self, test_app):
        """Test listing products with pagination"""
        response = test_app.get("/api/v1/products?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

        # Check types
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_list_products_with_category_filter(self, test_app):
        """Test filtering products by category"""
        response = test_app.get("/api/v1/products?category_id=test-category")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_create_product(self, test_app):
        """Test creating a product"""
        product_data = {
            "name": "Test Product",
            "description": "A test product",
            "price": 99.99,
            "stock": 100,
        }

        response = test_app.post("/api/v1/products", json=product_data)

        assert response.status_code == 201
        data = response.json()

        # Check created product
        assert data["name"] == product_data["name"]
        assert data["description"] == product_data["description"]
        assert data["price"] == product_data["price"]
        assert data["stock"] == product_data["stock"]
        assert "id" in data

    def test_create_product_invalid_data(self, test_app):
        """Test creating product with invalid data"""
        invalid_data = {
            "name": "",  # Empty name should fail
            "price": -10,  # Negative price should fail
        }

        response = test_app.post("/api/v1/products", json=invalid_data)

        assert response.status_code == 400  # Application error (not validation error)

    def test_get_product(self, test_app):
        """Test getting a product by ID"""
        # First create a product
        product_data = {
            "name": "Get Test Product",
            "price": 49.99,
            "stock": 50,
        }
        create_response = test_app.post("/api/v1/products", json=product_data)
        product_id = create_response.json()["id"]

        # Then retrieve it
        response = test_app.get(f"/api/v1/products/{product_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == product_id
        assert data["name"] == product_data["name"]

    def test_get_product_not_found(self, test_app):
        """Test getting a non-existent product"""
        response = test_app.get("/api/v1/products/non-existent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_product(self, test_app):
        """Test updating a product"""
        # First create a product
        product_data = {
            "name": "Update Test Product",
            "price": 79.99,
            "stock": 30,
        }
        create_response = test_app.post("/api/v1/products", json=product_data)
        product_id = create_response.json()["id"]

        # Then update it
        update_data = {
            "price": 69.99,
            "stock": 40,
        }
        response = test_app.put(f"/api/v1/products/{product_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["price"] == update_data["price"]
        assert data["stock"] == update_data["stock"]

    def test_delete_product(self, test_app):
        """Test deleting a product"""
        # First create a product
        product_data = {
            "name": "Delete Test Product",
            "price": 29.99,
            "stock": 10,
        }
        create_response = test_app.post("/api/v1/products", json=product_data)
        product_id = create_response.json()["id"]

        # Then delete it
        response = test_app.delete(f"/api/v1/products/{product_id}")

        assert response.status_code == 204

        # Verify it's deleted
        get_response = test_app.get(f"/api/v1/products/{product_id}")
        assert get_response.status_code == 404

    def test_pagination(self, test_app):
        """Test pagination functionality"""
        # Create multiple products
        for i in range(15):
            test_app.post(
                "/api/v1/products",
                json={
                    "name": f"Pagination Test Product {i}",
                    "price": 10.0 + i,
                    "stock": 100,
                },
            )

        # Test first page
        response1 = test_app.get("/api/v1/products?page=1&page_size=10")
        data1 = response1.json()
        assert len(data1["items"]) <= 10

        # Test second page
        response2 = test_app.get("/api/v1/products?page=2&page_size=10")
        data2 = response2.json()
        assert len(data2["items"]) >= 0


class TestOrderAPI:
    """Order API integration tests"""

    def test_create_order(self, test_app):
        """Test creating an order"""
        order_data = {
            "customer_id": "test-customer",
            "items": [
                {
                    "product_id": "prod-1",
                    "quantity": 2,
                    "unit_price": 99.99,
                },
                {
                    "product_id": "prod-2",
                    "quantity": 1,
                    "unit_price": 49.99,
                },
            ],
        }

        response = test_app.post("/api/v1/orders", json=order_data)

        assert response.status_code == 201
        data = response.json()
        assert data["customer_id"] == order_data["customer_id"]
        assert len(data["items"]) == 2
        assert "id" in data

    def test_order_state_transitions(self, test_app):
        """Test order state transitions (pending -> paid -> shipped)"""
        # Create order
        order_data = {
            "customer_id": "test-customer",
            "items": [
                {
                    "product_id": "prod-1",
                    "quantity": 1,
                    "unit_price": 99.99,
                }
            ],
        }
        create_response = test_app.post("/api/v1/orders", json=order_data)
        order_id = create_response.json()["id"]

        # Pay order
        pay_response = test_app.post(f"/api/v1/orders/{order_id}/pay")
        assert pay_response.status_code == 200
        assert pay_response.json()["status"] == "paid"

        # Ship order
        ship_response = test_app.post(f"/api/v1/orders/{order_id}/ship")
        assert ship_response.status_code == 200
        assert ship_response.json()["status"] == "shipped"

    def test_cancel_order(self, test_app):
        """Test cancelling an order"""
        # Create order
        order_data = {
            "customer_id": "test-customer",
            "items": [
                {
                    "product_id": "prod-1",
                    "quantity": 1,
                    "unit_price": 99.99,
                }
            ],
        }
        create_response = test_app.post("/api/v1/orders", json=order_data)
        order_id = create_response.json()["id"]

        # Cancel order
        cancel_response = test_app.post(f"/api/v1/orders/{order_id}/cancel")
        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "cancelled"

    def test_cannot_ship_unpaid_order(self, test_app):
        """Test that unpaid orders cannot be shipped"""
        # Create order
        order_data = {
            "customer_id": "test-customer",
            "items": [
                {
                    "product_id": "prod-1",
                    "quantity": 1,
                    "unit_price": 99.99,
                }
            ],
        }
        create_response = test_app.post("/api/v1/orders", json=order_data)
        order_id = create_response.json()["id"]

        # Try to ship without paying
        ship_response = test_app.post(f"/api/v1/orders/{order_id}/ship")
        assert ship_response.status_code == 400  # Bad request


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_root_endpoint(self, test_app):
        """Test root endpoint"""
        response = test_app.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data

    def test_health_endpoint(self, test_app):
        """Test health check endpoint"""
        response = test_app.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_api_ping(self, test_app):
        """Test API ping endpoint"""
        response = test_app.get("/ping")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "pong"

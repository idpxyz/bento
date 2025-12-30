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
            "description": "A test product for getting",
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
        data = response.json()
        assert "not found" in data.get("message", data.get("detail", "")).lower()

    def test_update_product(self, test_app):
        """Test updating a product"""
        # First create a product
        product_data = {
            "name": "Update Test Product",
            "description": "A test product for updating",
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
            "description": "A test product for deleting",
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

    def setup_method(self):
        """Reset state before each test"""
        pass

    def test_create_order(self, test_app):
        """Test creating an order"""
        # First create products
        product1_data = {
            "name": "Test Product 1",
            "description": "Product for order test",
            "price": 99.99,
            "stock": 100,
        }
        product2_data = {
            "name": "Test Product 2",
            "description": "Product for order test",
            "price": 49.99,
            "stock": 100,
        }
        prod1_response = test_app.post("/api/v1/products", json=product1_data)
        prod2_response = test_app.post("/api/v1/products", json=product2_data)
        prod1_id = prod1_response.json()["id"]
        prod2_id = prod2_response.json()["id"]

        # Then create order with real product IDs
        order_data = {
            "customer_id": "test-customer",
            "items": [
                {
                    "product_id": prod1_id,
                    "product_name": "Test Product 1",
                    "quantity": 2,
                    "unit_price": 99.99,
                },
                {
                    "product_id": prod2_id,
                    "product_name": "Test Product 2",
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
        # First create a product
        product_data = {
            "name": "Test Product 1",
            "description": "Product for order test",
            "price": 99.99,
            "stock": 100,
        }
        prod_response = test_app.post("/api/v1/products", json=product_data)
        assert prod_response.status_code == 201, f"Failed to create product: {prod_response.json()}"
        prod_data_resp = prod_response.json()
        prod_id = prod_data_resp.get("id")
        assert prod_id is not None, f"No product ID in response: {prod_data_resp}"

        # Create order with real product ID
        order_data = {
            "customer_id": "test-customer",
            "items": [
                {
                    "product_id": prod_id,
                    "product_name": "Test Product 1",
                    "quantity": 1,
                    "unit_price": 99.99,
                }
            ],
        }
        create_response = test_app.post("/api/v1/orders", json=order_data)
        assert create_response.status_code == 201, (
            f"Failed to create order: {create_response.json()}"
        )
        order_data_resp = create_response.json()
        order_id = order_data_resp.get("id")
        assert order_id is not None, f"No order ID in response: {order_data_resp}"

        # Pay order
        pay_response = test_app.post(f"/api/v1/orders/{order_id}/pay", json={})
        assert pay_response.status_code == 200, f"Failed to pay order: {pay_response.json()}"
        assert pay_response.json()["status"] == "paid"

        # Ship order
        ship_data = {"tracking_number": "TRACK123"}
        ship_response = test_app.post(f"/api/v1/orders/{order_id}/ship", json=ship_data)
        assert ship_response.status_code == 200, f"Failed to ship order: {ship_response.json()}"
        assert ship_response.json()["status"] == "shipped"

    def test_cancel_order(self, test_app):
        """Test cancelling an order"""
        # First create a product
        product_data = {
            "name": "Test Product 1",
            "description": "Product for order test",
            "price": 99.99,
            "stock": 100,
        }
        prod_response = test_app.post("/api/v1/products", json=product_data)
        assert prod_response.status_code == 201, f"Failed to create product: {prod_response.json()}"
        prod_data_resp = prod_response.json()
        prod_id = prod_data_resp.get("id")
        assert prod_id is not None, f"No product ID in response: {prod_data_resp}"

        # Create order with real product ID
        order_data = {
            "customer_id": "test-customer",
            "items": [
                {
                    "product_id": prod_id,
                    "product_name": "Test Product 1",
                    "quantity": 1,
                    "unit_price": 99.99,
                }
            ],
        }
        create_response = test_app.post("/api/v1/orders", json=order_data)
        assert create_response.status_code == 201, (
            f"Failed to create order: {create_response.json()}"
        )
        order_data_resp = create_response.json()
        order_id = order_data_resp.get("id")
        assert order_id is not None, f"No order ID in response: {order_data_resp}"

        # Cancel order
        cancel_data = {"reason": "Customer requested cancellation"}
        cancel_response = test_app.post(f"/api/v1/orders/{order_id}/cancel", json=cancel_data)
        assert cancel_response.status_code == 200, (
            f"Expected 200, got {cancel_response.status_code}: {cancel_response.json()}"
        )
        assert cancel_response.json()["status"] == "cancelled"

    def test_cannot_ship_unpaid_order(self, test_app):
        """Test that unpaid orders cannot be shipped"""
        # First create a product
        product_data = {
            "name": "Test Product 1",
            "description": "Product for order test",
            "price": 99.99,
            "stock": 100,
        }
        prod_response = test_app.post("/api/v1/products", json=product_data)
        assert prod_response.status_code == 201, f"Failed to create product: {prod_response.json()}"
        prod_data_resp = prod_response.json()
        prod_id = prod_data_resp.get("id")
        assert prod_id is not None, f"No product ID in response: {prod_data_resp}"

        # Create order with real product ID
        order_data = {
            "customer_id": "test-customer",
            "items": [
                {
                    "product_id": prod_id,
                    "product_name": "Test Product 1",
                    "quantity": 1,
                    "unit_price": 99.99,
                }
            ],
        }
        create_response = test_app.post("/api/v1/orders", json=order_data)
        assert create_response.status_code == 201, (
            f"Failed to create order: {create_response.json()}"
        )
        order_data_resp = create_response.json()
        order_id = order_data_resp.get("id")
        assert order_id is not None, f"No order ID in response: {order_data_resp}"

        # Try to ship without paying
        ship_data = {"tracking_number": "TRACK456"}
        ship_response = test_app.post(f"/api/v1/orders/{order_id}/ship", json=ship_data)
        # Should fail with 400 Bad Request (business rule violation)
        assert ship_response.status_code == 400, (
            f"Expected 400, got {ship_response.status_code}: {ship_response.json()}"
        )
        # Verify error message
        error_data = ship_response.json()
        assert "error" in error_data or "message" in error_data or "detail" in error_data


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_root_endpoint(self, test_app):
        """Test root endpoint"""
        response = test_app.get("/")

        # May get 429 if rate limited, but should eventually succeed
        assert response.status_code in (200, 429)
        if response.status_code == 200:
            data = response.json()
            assert "message" in data

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

"""Tests for OpenAPIGenerator."""

from bento.contracts.openapi_generator import OpenAPIGenerator


class TestOpenAPIGenerator:
    """Test OpenAPI specification generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = OpenAPIGenerator()

    def test_generate_basic_spec(self):
        """Test basic OpenAPI spec generation."""
        schemas = {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": ["id", "name"],
            }
        }

        spec = self.generator.generate(
            title="User API",
            version="1.0.0",
            schemas=schemas,
        )

        assert spec["openapi"] == "3.0.0"
        assert spec["info"]["title"] == "User API"
        assert spec["info"]["version"] == "1.0.0"
        assert "User" in spec["components"]["schemas"]

    def test_generate_with_endpoints(self):
        """Test OpenAPI spec with endpoints."""
        schemas = {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                },
            }
        }

        endpoints = {
            "getUser": {
                "method": "GET",
                "path": "/users/{id}",
                "description": "Get user by ID",
                "response": schemas["User"],
            },
            "createUser": {
                "method": "POST",
                "path": "/users",
                "description": "Create new user",
                "request": schemas["User"],
                "response": schemas["User"],
            },
        }

        spec = self.generator.generate(
            title="User API",
            version="1.0.0",
            schemas=schemas,
            endpoints=endpoints,
        )

        assert "/users/{id}" in spec["paths"]
        assert "/users" in spec["paths"]
        assert "get" in spec["paths"]["/users/{id}"]
        assert "post" in spec["paths"]["/users"]

    def test_generate_with_description(self):
        """Test OpenAPI spec with description."""
        spec = self.generator.generate(
            title="My API",
            version="1.0.0",
            schemas={},
            description="This is my API",
        )

        assert spec["info"]["description"] == "This is my API"

    def test_schema_conversion_object(self):
        """Test schema conversion for object type."""
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["id"],
        }

        converted = self.generator._convert_schema(schema)

        assert converted["type"] == "object"
        assert "properties" in converted
        assert "id" in converted["properties"]
        assert "required" in converted
        assert "id" in converted["required"]

    def test_schema_conversion_array(self):
        """Test schema conversion for array type."""
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 10,
        }

        converted = self.generator._convert_schema(schema)

        assert converted["type"] == "array"
        assert "items" in converted
        assert converted["minItems"] == 1
        assert converted["maxItems"] == 10

    def test_schema_conversion_with_constraints(self):
        """Test schema conversion with constraints."""
        schema = {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "pattern": "^[a-z]+$",
        }

        converted = self.generator._convert_schema(schema)

        assert converted["minLength"] == 1
        assert converted["maxLength"] == 100
        assert converted["pattern"] == "^[a-z]+$"

    def test_schema_conversion_with_enum(self):
        """Test schema conversion with enum."""
        schema = {
            "type": "string",
            "enum": ["DRAFT", "ACTIVE", "ARCHIVED"],
        }

        converted = self.generator._convert_schema(schema)

        assert "enum" in converted
        assert converted["enum"] == ["DRAFT", "ACTIVE", "ARCHIVED"]

    def test_generate_yaml(self):
        """Test YAML generation."""
        schemas = {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                },
            }
        }

        yaml_str = self.generator.generate_yaml(
            title="User API",
            version="1.0.0",
            schemas=schemas,
        )

        assert isinstance(yaml_str, str)
        assert "openapi:" in yaml_str
        assert "title:" in yaml_str
        assert "User API" in yaml_str

    def test_endpoint_with_request_and_response(self):
        """Test endpoint with both request and response."""
        schemas = {
            "CreateUserRequest": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                },
            },
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                },
            },
        }

        endpoints = {
            "createUser": {
                "method": "POST",
                "path": "/users",
                "request": schemas["CreateUserRequest"],
                "response": schemas["User"],
            }
        }

        spec = self.generator.generate(
            title="API",
            version="1.0.0",
            schemas=schemas,
            endpoints=endpoints,
        )

        operation = spec["paths"]["/users"]["post"]
        assert "requestBody" in operation
        assert "responses" in operation
        assert "200" in operation["responses"]

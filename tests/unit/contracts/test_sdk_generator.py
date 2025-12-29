"""Tests for SDKGenerator."""

from bento.contracts.sdk_generator import SDKGenerator


class TestSDKGenerator:
    """Test SDK code generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SDKGenerator()

    def test_generate_dataclass_simple(self):
        """Test simple dataclass generation."""
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["id", "name"],
        }

        code = self.generator.generate_dataclass("User", schema)

        assert "@dataclass" in code
        assert "class User:" in code
        assert "id: str" in code
        assert "name: str" in code
        assert "to_dict" in code
        assert "from_dict" in code

    def test_generate_dataclass_with_optional_fields(self):
        """Test dataclass with optional fields."""
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "email": {"type": "string"},
            },
            "required": ["id"],
        }

        code = self.generator.generate_dataclass("User", schema)

        assert "id: str" in code
        assert "Optional[str]" in code
        assert "email: Optional[str] = None" in code

    def test_generate_dataclass_with_array(self):
        """Test dataclass with array field."""
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["id"],
        }

        code = self.generator.generate_dataclass("Item", schema)

        assert "List[str]" in code
        assert "tags: Optional[List[str]]" in code

    def test_generate_module(self):
        """Test module generation with multiple classes."""
        schemas = {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": ["id"],
            },
            "Post": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                },
                "required": ["id"],
            },
        }

        code = self.generator.generate_module("models", schemas)

        assert "class User:" in code
        assert "class Post:" in code
        assert code.count("@dataclass") == 2

    def test_generate_client(self):
        """Test HTTP client generation."""
        endpoints = {
            "getUser": {
                "method": "GET",
                "path": "/users/{id}",
            },
            "createUser": {
                "method": "POST",
                "path": "/users",
            },
        }

        code = self.generator.generate_client(
            "UserClient",
            "https://api.example.com",
            endpoints,
        )

        assert "class UserClient:" in code
        assert "def get_user" in code
        assert "def create_user" in code
        assert "httpx.Client" in code

    def test_get_type_hint_string(self):
        """Test type hint generation for string."""
        schema = {"type": "string"}
        hint = self.generator._get_type_hint(schema)
        assert hint == "str"

    def test_get_type_hint_integer(self):
        """Test type hint generation for integer."""
        schema = {"type": "integer"}
        hint = self.generator._get_type_hint(schema)
        assert hint == "int"

    def test_get_type_hint_array(self):
        """Test type hint generation for array."""
        schema = {
            "type": "array",
            "items": {"type": "string"},
        }
        hint = self.generator._get_type_hint(schema)
        assert "List" in hint

    def test_endpoint_to_method_name(self):
        """Test endpoint name to method name conversion."""
        assert self.generator._endpoint_to_method_name("getUser") == "get_user"
        assert self.generator._endpoint_to_method_name("CreatePost") == "create_post"
        assert self.generator._endpoint_to_method_name("listUsers") == "list_users"

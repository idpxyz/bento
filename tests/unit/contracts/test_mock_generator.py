"""Tests for MockGenerator."""

from bento.contracts.mock_generator import MockGenerator


class TestMockGenerator:
    """Test mock data generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = MockGenerator(seed=42)

    def test_generate_string(self):
        """Test string generation."""
        schema = {"type": "string"}
        result = self.generator.generate(schema)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_integer(self):
        """Test integer generation."""
        schema = {"type": "integer", "minimum": 0, "maximum": 100}
        result = self.generator.generate(schema)
        assert isinstance(result, int)
        assert 0 <= result <= 100

    def test_generate_number(self):
        """Test number generation."""
        schema = {"type": "number", "minimum": 0.0, "maximum": 100.0}
        result = self.generator.generate(schema)
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    def test_generate_boolean(self):
        """Test boolean generation."""
        schema = {"type": "boolean"}
        result = self.generator.generate(schema)
        assert isinstance(result, bool)

    def test_generate_array(self):
        """Test array generation."""
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 5,
        }
        result = self.generator.generate(schema)
        assert isinstance(result, list)
        assert 1 <= len(result) <= 5
        assert all(isinstance(item, str) for item in result)

    def test_generate_object(self):
        """Test object generation."""
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["id", "name"],
        }
        result = self.generator.generate(schema)
        assert isinstance(result, dict)
        assert "id" in result
        assert "name" in result
        assert isinstance(result["id"], str)
        assert isinstance(result["name"], str)

    def test_generate_enum(self):
        """Test enum generation."""
        schema = {"type": "string", "enum": ["DRAFT", "ACTIVE", "ARCHIVED"]}
        result = self.generator.generate(schema)
        assert result in ["DRAFT", "ACTIVE", "ARCHIVED"]

    def test_generate_email(self):
        """Test email format generation."""
        schema = {"type": "string", "format": "email"}
        result = self.generator.generate(schema)
        assert isinstance(result, str)
        assert "@" in result
        assert "example.com" in result

    def test_generate_uuid(self):
        """Test UUID format generation."""
        schema = {"type": "string", "format": "uuid"}
        result = self.generator.generate(schema)
        assert isinstance(result, str)
        assert len(result) == 36  # UUID length

    def test_generate_batch(self):
        """Test batch generation."""
        schema = {"type": "integer", "minimum": 0, "maximum": 100}
        results = self.generator.generate_batch(schema, count=5)
        assert len(results) == 5
        assert all(isinstance(r, int) for r in results)

    def test_generate_nested_object(self):
        """Test nested object generation."""
        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                    },
                    "required": ["id"],
                },
            },
            "required": ["user"],
        }
        result = self.generator.generate(schema)
        assert isinstance(result, dict)
        assert "user" in result
        assert isinstance(result["user"], dict)
        assert "id" in result["user"]

    def test_reproducibility_with_seed(self):
        """Test that same seed produces same results."""
        schema = {"type": "string"}

        gen1 = MockGenerator(seed=42)
        result1 = gen1.generate(schema)

        gen2 = MockGenerator(seed=42)
        result2 = gen2.generate(schema)

        assert result1 == result2

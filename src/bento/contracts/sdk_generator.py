"""SDK Generator - Contracts-as-Code.

Generates Python SDK code from JSON schemas for type-safe client development.
Creates dataclasses with validation and serialization support.

Example:
    ```python
    from bento.contracts import SDKGenerator

    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "email": {"type": "string", "format": "email"},
        },
        "required": ["id", "name"],
    }

    generator = SDKGenerator()
    code = generator.generate_dataclass("User", schema)
    print(code)
    # → Python dataclass code with type hints and validation
    ```
"""

from __future__ import annotations

from typing import Any


class SDKGenerator:
    """Generates Python SDK code from JSON schemas.

    Creates type-safe dataclasses with validation and serialization support
    for client-side development.

    Example:
        ```python
        generator = SDKGenerator()

        # Generate dataclass
        code = generator.generate_dataclass("User", schema)

        # Generate complete module
        module = generator.generate_module("user_models", {"User": schema})
        ```
    """

    def generate_dataclass(
        self,
        class_name: str,
        schema: dict[str, Any],
    ) -> str:
        """Generate Python dataclass from schema.

        Args:
            class_name: Name of the dataclass
            schema: JSON schema definition

        Returns:
            Python dataclass code
        """
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        lines = [
            "from dataclasses import dataclass, field",
            "from typing import Optional, List, Dict, Any",
            "",
            "@dataclass",
            f"class {class_name}:",
            '    """Auto-generated dataclass from schema."""',
            "",
        ]

        # Generate fields
        for prop_name, prop_schema in properties.items():
            type_hint = self._get_type_hint(prop_schema)
            is_required = prop_name in required

            if is_required:
                lines.append(f"    {prop_name}: {type_hint}")
            else:
                lines.append(f"    {prop_name}: Optional[{type_hint}] = None")

        # Add methods
        lines.extend([
            "",
            "    def to_dict(self) -> Dict[str, Any]:",
            '        """Convert to dictionary."""',
            "        return {",
        ])

        for prop_name in properties:
            lines.append(f"            '{prop_name}': self.{prop_name},")

        lines.extend([
            "        }",
            "",
            "    @classmethod",
            "    def from_dict(cls, data: Dict[str, Any]) -> 'User':",
            '        """Create from dictionary."""',
            "        return cls(**data)",
        ])

        return "\n".join(lines)

    def generate_module(
        self,
        module_name: str,
        schemas: dict[str, dict[str, Any]],
    ) -> str:
        """Generate complete Python module with multiple dataclasses.

        Args:
            module_name: Name of the module
            schemas: Dict mapping class names to schemas

        Returns:
            Complete Python module code
        """
        lines = [
            '"""Auto-generated SDK module."""',
            "",
            "from dataclasses import dataclass, field",
            "from typing import Optional, List, Dict, Any",
            "",
        ]

        # Generate each dataclass
        for class_name, schema in schemas.items():
            class_code = self.generate_dataclass(class_name, schema)
            # Remove imports from individual classes
            class_lines = [
                line for line in class_code.split("\n")
                if not line.startswith("from ") and not line.startswith("import ")
            ]
            lines.extend(class_lines)
            lines.append("")

        return "\n".join(lines)

    def generate_client(
        self,
        class_name: str,
        base_url: str,
        endpoints: dict[str, dict[str, Any]],
    ) -> str:
        """Generate HTTP client code.

        Args:
            class_name: Name of the client class
            base_url: Base URL for API
            endpoints: Dict mapping endpoint names to configurations

        Returns:
            Python client code
        """
        lines = [
            "import httpx",
            "from typing import Optional, Dict, Any",
            "",
            f"class {class_name}:",
            '    """Auto-generated HTTP client."""',
            "",
            "    def __init__(self, base_url: str = None, headers: Dict[str, str] = None):",
            '        """Initialize client."""',
            f'        self.base_url = base_url or "{base_url}"',
            "        self.headers = headers or {}",
            "        self.client = httpx.Client(base_url=self.base_url, headers=self.headers)",
            "",
            "    def close(self):",
            '        """Close client connection."""',
            "        self.client.close()",
            "",
            "    async def aclose(self):",
            '        """Close async client connection."""',
            "        await self.client.aclose()",
            "",
        ]

        # Generate methods for each endpoint
        for endpoint_name, endpoint_config in endpoints.items():
            method = endpoint_config.get("method", "GET").upper()
            path = endpoint_config.get("path", f"/{endpoint_name}")
            request_schema = endpoint_config.get("request")
            response_schema = endpoint_config.get("response")

            method_name = self._endpoint_to_method_name(endpoint_name)
            request_type = "Dict[str, Any]" if request_schema else "None"
            response_type = "Dict[str, Any]" if response_schema else "None"

            lines.extend([
                f"    def {method_name}(self, data: {request_type} = None) -> {response_type}:",
                f'        """Call {endpoint_name} endpoint."""',
                f'        response = self.client.request("{method}", "{path}", json=data)',
                "        response.raise_for_status()",
                "        return response.json()",
                "",
            ])

        return "\n".join(lines)

    def _get_type_hint(self, schema: dict[str, Any]) -> str:
        """Get Python type hint from schema.

        Args:
            schema: JSON schema definition

        Returns:
            Python type hint string
        """
        schema_type = schema.get("type")

        if schema_type == "object":
            return "Dict[str, Any]"
        elif schema_type == "array":
            items_schema = schema.get("items", {})
            item_type = self._get_type_hint(items_schema)
            return f"List[{item_type}]"
        elif schema_type == "string":
            string_format = schema.get("format")
            if string_format == "date":
                return "str"  # Could use datetime.date
            elif string_format == "date-time":
                return "str"  # Could use datetime.datetime
            else:
                return "str"
        elif schema_type == "number":
            return "float"
        elif schema_type == "integer":
            return "int"
        elif schema_type == "boolean":
            return "bool"
        elif schema_type == "null":
            return "None"
        else:
            return "Any"

    def _endpoint_to_method_name(self, endpoint_name: str) -> str:
        """Convert endpoint name to method name.

        Args:
            endpoint_name: Endpoint name

        Returns:
            Method name in snake_case
        """
        # Convert camelCase or PascalCase to snake_case
        result = []
        for i, char in enumerate(endpoint_name):
            if char.isupper() and i > 0:
                result.append("_")
                result.append(char.lower())
            else:
                result.append(char.lower())
        return "".join(result)

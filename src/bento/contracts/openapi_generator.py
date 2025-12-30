"""OpenAPI Generator - Contracts-as-Code.

Generates OpenAPI 3.0 documentation from JSON schemas and endpoint definitions.
Creates complete API documentation with request/response examples.

Example:
    ```python
    from bento.contracts import OpenAPIGenerator

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

    endpoints = {
        "getUser": {
            "method": "GET",
            "path": "/users/{id}",
            "response": schemas["User"],
        }
    }

    generator = OpenAPIGenerator()
    spec = generator.generate(
        title="User API",
        version="1.0.0",
        schemas=schemas,
        endpoints=endpoints,
    )
    ```
"""

from __future__ import annotations

from typing import Any


class OpenAPIGenerator:
    """Generates OpenAPI 3.0 specification from schemas.

    Creates complete API documentation with request/response definitions,
    examples, and validation rules.

    Example:
        ```python
        generator = OpenAPIGenerator()

        spec = generator.generate(
            title="My API",
            version="1.0.0",
            schemas=schemas,
            endpoints=endpoints,
        )

        # Export to YAML or JSON
        import json
        with open("openapi.json", "w") as f:
            json.dump(spec, f, indent=2)
        ```
    """

    def generate(
        self,
        title: str,
        version: str,
        schemas: dict[str, dict[str, Any]],
        endpoints: dict[str, dict[str, Any]] | None = None,
        base_path: str = "/api/v1",
        description: str = "",
    ) -> dict[str, Any]:
        """Generate OpenAPI specification.

        Args:
            title: API title
            version: API version
            schemas: Dict mapping schema names to definitions
            endpoints: Dict mapping endpoint names to configurations
            base_path: Base path for all endpoints
            description: API description

        Returns:
            OpenAPI 3.0 specification dict
        """
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": title,
                "version": version,
            },
            "servers": [
                {
                    "url": base_path,
                    "description": "API server",
                }
            ],
            "components": {
                "schemas": self._generate_schemas(schemas),
            },
            "paths": self._generate_paths(endpoints or {}, schemas),
        }

        if description:
            spec["info"]["description"] = description

        return spec

    def _generate_schemas(
        self,
        schemas: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Generate OpenAPI schema definitions.

        Args:
            schemas: Dict mapping schema names to definitions

        Returns:
            OpenAPI components/schemas
        """
        result = {}

        for name, schema in schemas.items():
            result[name] = self._convert_schema(schema)

        return result

    def _generate_paths(
        self,
        endpoints: dict[str, dict[str, Any]],
        schemas: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Generate OpenAPI paths.

        Args:
            endpoints: Dict mapping endpoint names to configurations
            schemas: Available schemas for references

        Returns:
            OpenAPI paths
        """
        paths = {}

        for endpoint_name, endpoint_config in endpoints.items():
            method = endpoint_config.get("method", "GET").lower()
            path = endpoint_config.get("path", f"/{endpoint_name}")
            description = endpoint_config.get("description", endpoint_name)
            request_schema = endpoint_config.get("request")
            response_schema = endpoint_config.get("response")

            if path not in paths:
                paths[path] = {}

            operation = {
                "summary": description,
                "operationId": endpoint_name,
                "tags": [endpoint_config.get("tag", "default")],
            }

            # Add request body
            if request_schema:
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": self._convert_schema(request_schema),
                        }
                    },
                }

            # Add response
            if response_schema:
                operation["responses"] = {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": self._convert_schema(response_schema),
                            }
                        },
                    }
                }
            else:
                operation["responses"] = {
                    "200": {
                        "description": "Successful response",
                    }
                }

            paths[path][method] = operation

        return paths

    def _convert_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Convert JSON schema to OpenAPI schema.

        Args:
            schema: JSON schema definition

        Returns:
            OpenAPI schema definition
        """
        result = {}

        # Copy basic properties
        for key in ["type", "title", "description", "default", "example"]:
            if key in schema:
                result[key] = schema[key]

        # Handle constraints
        if "minimum" in schema:
            result["minimum"] = schema["minimum"]
        if "maximum" in schema:
            result["maximum"] = schema["maximum"]
        if "minLength" in schema:
            result["minLength"] = schema["minLength"]
        if "maxLength" in schema:
            result["maxLength"] = schema["maxLength"]
        if "pattern" in schema:
            result["pattern"] = schema["pattern"]
        if "enum" in schema:
            result["enum"] = schema["enum"]

        # Handle format
        if "format" in schema:
            result["format"] = schema["format"]

        # Handle object properties
        if schema.get("type") == "object":
            properties = schema.get("properties", {})
            result["properties"] = {
                name: self._convert_schema(prop_schema)
                for name, prop_schema in properties.items()
            }
            if "required" in schema:
                result["required"] = schema["required"]

        # Handle array items
        if schema.get("type") == "array":
            items = schema.get("items", {})
            result["items"] = self._convert_schema(items)
            if "minItems" in schema:
                result["minItems"] = schema["minItems"]
            if "maxItems" in schema:
                result["maxItems"] = schema["maxItems"]

        return result

    def generate_yaml(
        self,
        title: str,
        version: str,
        schemas: dict[str, dict[str, Any]],
        endpoints: dict[str, dict[str, Any]] | None = None,
        base_path: str = "/api/v1",
    ) -> str:
        """Generate OpenAPI specification as YAML string.

        Args:
            title: API title
            version: API version
            schemas: Dict mapping schema names to definitions
            endpoints: Dict mapping endpoint names to configurations
            base_path: Base path for all endpoints

        Returns:
            YAML string representation of OpenAPI spec
        """
        spec = self.generate(title, version, schemas, endpoints, base_path)
        return self._dict_to_yaml(spec)

    def _dict_to_yaml(self, data: Any, indent: int = 0) -> str:
        """Convert dict to YAML string (simplified).

        Args:
            data: Data to convert
            indent: Current indentation level

        Returns:
            YAML string
        """
        lines = []
        indent_str = "  " * indent

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{indent_str}{key}:")
                    lines.append(self._dict_to_yaml(value, indent + 1))
                else:
                    if isinstance(value, str):
                        lines.append(f'{indent_str}{key}: "{value}"')
                    elif value is None:
                        lines.append(f"{indent_str}{key}:")
                    else:
                        lines.append(f"{indent_str}{key}: {value}")
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    lines.append(f"{indent_str}- ")
                    yaml_item = self._dict_to_yaml(item, indent + 1)
                    # Remove leading indent for first line
                    yaml_lines = yaml_item.split("\n")
                    lines.append(yaml_lines[0])
                    lines.extend(yaml_lines[1:])
                else:
                    if isinstance(item, str):
                        lines.append(f'{indent_str}- "{item}"')
                    else:
                        lines.append(f"{indent_str}- {item}")

        return "\n".join(lines)

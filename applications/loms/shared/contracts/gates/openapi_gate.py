"""
OpenAPI Contract Gate - Startup validation.

Validates OpenAPI contracts at application startup.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from loms.shared.contracts.gates.openapi_loader import find_openapi_files


def validate_openapi_contracts(contracts_root: Path, expected_version: str = "1.0.0") -> list[Path]:
    """
    Validate OpenAPI contracts at startup.

    Args:
        contracts_root: Path to contracts directory
        expected_version: Expected API version

    Returns:
        List of validated OpenAPI files

    Raises:
        RuntimeError: If contracts are invalid or missing
    """
    files = find_openapi_files(contracts_root)
    if not files:
        raise RuntimeError("OpenAPI contract not found under contracts_root")

    for p in files:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "openapi" not in data:
            raise RuntimeError(f"Invalid OpenAPI document: {p}")
        info = data.get("info") or {}
        ver = str(info.get("version", "")).strip()
        if ver and ver != expected_version:
            raise RuntimeError(f"OpenAPI version mismatch in {p}: {ver} != {expected_version}")
    return files

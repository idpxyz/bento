from __future__ import annotations

import re
from pathlib import Path


def find_openapi_files(contracts_root: Path) -> list[Path]:
    candidates: list[Path] = []
    for p in contracts_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}:
            name = p.name.lower()
            if "openapi" in name or "swagger" in name:
                candidates.append(p)

    if candidates:
        return sorted(set(candidates))

    for p in contracts_root.rglob("*.y*ml"):
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"\bopenapi\s*:\s*['\"]?\d", txt):
            candidates.append(p)

    return sorted(set(candidates))

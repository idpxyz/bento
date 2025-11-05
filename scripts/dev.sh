#!/usr/bin/env bash
set -e
uv venv || true
source .venv/bin/activate
uv pip install -e .[dev]
uvicorn examples.minimal_app.main:app --reload

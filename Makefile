.PHONY: fmt lint test run dev

fmt:
	ruff check --fix . && ruff format .

lint:
	ruff check . && mypy .

test:
	pytest

run:
	uv run examples/minimal_app/main.py

dev:
	uvicorn examples.minimal_app.main:app --reload

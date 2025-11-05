# Bento Framework — Starter

A minimal, production-friendly scaffold for a Domain-Driven Design framework with hexagonal architecture, ready for FastAPI + SQLAlchemy + event outbox.

## Quick start

```bash
# with uv (recommended) or pip
uv venv && . .venv/bin/activate
uv pip install -e .[dev]
uv run examples/minimal_app/main.py
# or python -m examples.minimal_app.main
```

## What you get
- `src/` core packages (domain, application, messaging, persistence, etc.)
- `runtime/` composition root (DI, wiring)
- `examples/minimal_app` runnable FastAPI demo
- `deploy/docker/compose.dev.yaml` one-command infra (Postgres, Redis, Redpanda/Kafka, MinIO)

See `docs/` for conventions and ADRs.


## Added in this pack
- Async SQLAlchemy UnitOfWork + Outbox table
- Redis/Kafka/MinIO/OpenSearch thin adapters
- GitHub Actions CI + stricter import-linter rules
- `bento gen` for aggregate/usecase/event

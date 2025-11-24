# Bento Framework — Starter

A minimal, production-friendly scaffold for a Domain-Driven Design framework with hexagonal architecture, ready for FastAPI + SQLAlchemy + event outbox.

## Quick start

### 1. Install dependencies

```bash
# with uv (recommended)
uv venv && . .venv/bin/activate
uv pip install -e .[dev]
```

### 2. Run a demo application

#### Minimal demo

```bash
uv run examples/minimal_app/main.py
# or: python -m examples.minimal_app.main
```

#### my-shop (full DDD e-commerce example)

```bash
cd applications/my-shop

# run API server
uv run uvicorn main:app --reload

# run tests
uv run pytest -v
```

## What you get
- `src/` core packages (domain, application, messaging, persistence, etc.)
- `runtime/` composition root (DI, wiring)
- `examples/minimal_app` runnable FastAPI demo
- `deploy/docker/compose.dev.yaml` one-command infra (Postgres, Redis, Redpanda/Kafka, MinIO)

## ✨ Key Features

### 🚀 Repository Enhancement (NEW!)
**29 built-in repository methods** to supercharge your data access layer:
- ✅ **Batch operations** - `get_by_ids()`, `delete_by_ids()`
- ✅ **Uniqueness checks** - `is_unique()`, `find_by_field()`
- ✅ **Aggregations** - `sum_field()`, `avg_field()`, `min/max_field()`
- ✅ **Sorting & pagination** - `find_top_n()`, `find_paginated()`
- ✅ **Conditional updates** - `update_by_spec()`, `delete_by_spec()`
- ✅ **Group by queries** - `group_by_field()`, `group_by_date()`
- ✅ **Soft delete management** - `find_trashed()`, `restore_by_spec()`
- ✅ **Random sampling** - `find_random_n()`, `sample_percentage()`

All repositories automatically inherit these methods - **zero configuration required**!

📖 **Docs**: [Repository Mixins Guide](./docs/infrastructure/REPOSITORY_MIXINS_GUIDE.md) | [Quick Reference](./docs/infrastructure/REPOSITORY_MIXINS_QUICK_REF.md)

### 🔄 Cascade Operations
Automatic cascade save/delete for aggregate relationships with declarative configuration.

📖 **Docs**: [Cascade Usage Guide](./docs/infrastructure/CASCADE_USAGE.md)

### 🎯 Rich Infrastructure
- **Interceptor Chain** - Audit, cache, soft delete, optimistic locking
- **Specification Pattern** - Fluent query builders with type safety
- **Event-Driven Architecture** - Domain events + outbox pattern
- **Auto Mapping** - DTO ↔ Domain ↔ PO transformation

See `docs/` for detailed conventions and guides, including:

- Architecture & evaluation: `docs/architecture/Bento 评估 - 1124.md`
- Order flow (end-to-end): `docs/architecture/ORDER_FLOW.md`
- Pagination guide: `docs/architecture/PAGINATION_GUIDE.md`
- Cache serialization: `docs/architecture/CACHE_SERIALIZATION.md`
- Cache configuration & interceptor: `docs/infrastructure/cache/CACHE_CONFIGURATION_GUIDE.md`
- Stable APIs for 1.0: `docs/architecture/STABLE_API_1_0.md`


## Added in this pack
- Async SQLAlchemy UnitOfWork + Outbox table
- Redis/Kafka/MinIO/OpenSearch thin adapters
- GitHub Actions CI + stricter import-linter rules
- `bento gen` for aggregate/usecase/event

## License

**Version 0.2.0 and later:**

Copyright © 2025 idp.xyz. All Rights Reserved.

This software is proprietary and confidential. Unauthorized copying,
modification, distribution, or use of this software is strictly prohibited.

For licensing inquiries, please contact: licensing@idp.xyz

**Previous versions (v0.1.x):**

Licensed under MIT License.

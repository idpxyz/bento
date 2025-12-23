# Migrations (placeholder)

后续引入 Alembic 时，建议在 `env.py` 中引用：
`from app.shared.infra.db.model_registry import get_metadata`

并将 `target_metadata = get_metadata()`。

"""Alembic environment configuration for my-shop."""

from logging.config import fileConfig

# Import Base to ensure all models are registered
from bento.persistence import Base

# Import all models to register them with SQLAlchemy
from bento.persistence.outbox.record import OutboxRecord  # noqa: F401
from sqlalchemy import engine_from_config, pool

from alembic import context
from contexts.catalog.infrastructure.models.category_po import CategoryPO  # noqa: F401
from contexts.catalog.infrastructure.models.product_po import ProductPO  # noqa: F401
from contexts.identity.infrastructure.models.user_po import UserPO  # noqa: F401
from contexts.ordering.infrastructure.models.order_po import OrderPO  # noqa: F401
from contexts.ordering.infrastructure.models.orderitem_po import OrderItemPO  # noqa: F401

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

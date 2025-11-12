from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251111_3_add_audit_version_fields"
down_revision = "20251111_2_init_orders_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add audit and version fields to orders table
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("created_by", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("updated_by", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("deleted_by", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("version")
        batch_op.drop_column("deleted_by")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("updated_by")
        batch_op.drop_column("created_by")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")

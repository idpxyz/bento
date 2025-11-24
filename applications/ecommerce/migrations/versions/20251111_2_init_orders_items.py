from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251111_2_init_orders_items"
down_revision = "20251111_1_add_order_discounts_tax_lines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Orders table
    op.create_table(
        "orders",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("discount_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("shipping_address_line1", sa.String(), nullable=True),
        sa.Column("shipping_city", sa.String(), nullable=True),
        sa.Column("shipping_country", sa.String(), nullable=True),
        sa.Column("payment_method", sa.String(), nullable=True),
        sa.Column("shipment_carrier", sa.String(), nullable=True),
        sa.Column("payment_card_last4", sa.String(), nullable=True),
        sa.Column("payment_card_brand", sa.String(), nullable=True),
        sa.Column("payment_paypal_payer_id", sa.String(), nullable=True),
        sa.Column("shipment_tracking_no", sa.String(), nullable=True),
        sa.Column("shipment_service", sa.String(), nullable=True),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_payment_method", "orders", ["payment_method"])
    op.create_index("ix_orders_shipment_carrier", "orders", ["shipment_carrier"])
    op.create_index("ix_orders_currency", "orders", ["currency"])

    # Order items table
    op.create_table(
        "order_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("order_id", sa.String(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("product_id", sa.String(), nullable=False),
        sa.Column("product_name", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("kind", sa.String(), nullable=False, server_default="simple"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_index("ix_order_items_product_id", "order_items", ["product_id"])
    op.create_index("ix_order_items_kind", "order_items", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_order_items_kind", table_name="order_items")
    op.drop_index("ix_order_items_product_id", table_name="order_items")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_currency", table_name="orders")
    op.drop_index("ix_orders_shipment_carrier", table_name="orders")
    op.drop_index("ix_orders_payment_method", table_name="orders")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_table("orders")

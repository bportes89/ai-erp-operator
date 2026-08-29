"""money as numeric"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.alter_column("operations", "total", type_=sa.Numeric(12, 2), existing_type=sa.Float())
        op.alter_column("operation_items", "quantity", type_=sa.Numeric(12, 2), existing_type=sa.Float())
        op.alter_column("operation_items", "unit_price", type_=sa.Numeric(12, 2), existing_type=sa.Float())
        op.alter_column("operation_items", "total", type_=sa.Numeric(12, 2), existing_type=sa.Float())
        return
    with op.batch_alter_table("operations") as batch:
        batch.alter_column("total", type_=sa.Numeric(12, 2), existing_type=sa.Float())
    with op.batch_alter_table("operation_items") as batch:
        batch.alter_column("quantity", type_=sa.Numeric(12, 2), existing_type=sa.Float())
        batch.alter_column("unit_price", type_=sa.Numeric(12, 2), existing_type=sa.Float())
        batch.alter_column("total", type_=sa.Numeric(12, 2), existing_type=sa.Float())


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.alter_column("operations", "total", type_=sa.Float(), existing_type=sa.Numeric(12, 2))
        op.alter_column("operation_items", "quantity", type_=sa.Float(), existing_type=sa.Numeric(12, 2))
        op.alter_column("operation_items", "unit_price", type_=sa.Float(), existing_type=sa.Numeric(12, 2))
        op.alter_column("operation_items", "total", type_=sa.Float(), existing_type=sa.Numeric(12, 2))
        return
    with op.batch_alter_table("operations") as batch:
        batch.alter_column("total", type_=sa.Float(), existing_type=sa.Numeric(12, 2))
    with op.batch_alter_table("operation_items") as batch:
        batch.alter_column("quantity", type_=sa.Float(), existing_type=sa.Numeric(12, 2))
        batch.alter_column("unit_price", type_=sa.Float(), existing_type=sa.Numeric(12, 2))
        batch.alter_column("total", type_=sa.Float(), existing_type=sa.Numeric(12, 2))
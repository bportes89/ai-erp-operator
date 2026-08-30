"""process recipes"""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.create_table(
            "process_recipes",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column("operation_type", sa.String(60), nullable=False),
            sa.Column("field_aliases", sa.JSON(), nullable=True),
            sa.Column("required_fields", sa.JSON(), nullable=True),
            sa.Column("approval_threshold", sa.Numeric(12, 2), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_process_recipes_organization_id", "process_recipes", ["organization_id"])
        op.add_column(
            "operations",
            sa.Column("recipe_id", sa.String(), sa.ForeignKey("process_recipes.id"), nullable=True),
        )
        op.create_index("ix_operations_recipe_id", "operations", ["recipe_id"])
        return
    with op.batch_alter_table("operations") as batch:
        batch.add_column(
            sa.Column("recipe_id", sa.String(), sa.ForeignKey("process_recipes.id"), nullable=True)
        )
    op.create_table(
        "process_recipes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("operation_type", sa.String(60), nullable=False),
        sa.Column("field_aliases", sa.JSON(), nullable=True),
        sa.Column("required_fields", sa.JSON(), nullable=True),
        sa.Column("approval_threshold", sa.Numeric(12, 2), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_process_recipes_organization_id", "process_recipes", ["organization_id"])


def downgrade():
    op.drop_table("process_recipes")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("ix_operations_recipe_id", table_name="operations")
        op.drop_column("operations", "recipe_id")
        return
    with op.batch_alter_table("operations") as batch:
        batch.drop_column("recipe_id")
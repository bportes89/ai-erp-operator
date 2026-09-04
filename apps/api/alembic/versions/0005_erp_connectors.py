"""erp connectors per organization"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "erp_connectors",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("token", sa.String(255), nullable=True),
        sa.Column("auth_header", sa.String(120), nullable=False),
        sa.Column("auth_scheme", sa.String(80), nullable=False),
        sa.Column("create_path", sa.String(200), nullable=False),
        sa.Column("verify_path", sa.String(200), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("item_fields", sa.String(500), nullable=False),
        sa.Column("external_id_path", sa.String(120), nullable=False),
        sa.Column("timeout", sa.Integer(), nullable=False),
        sa.Column("retries", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_erp_connectors_organization_id", "erp_connectors", ["organization_id"])


def downgrade():
    op.drop_index("ix_erp_connectors_organization_id", table_name="erp_connectors")
    op.drop_table("erp_connectors")
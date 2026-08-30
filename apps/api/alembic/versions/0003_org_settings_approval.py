"""org settings + pending_approval status"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.add_column("organizations", sa.Column("settings", sa.JSON(), nullable=True))
        op.execute(
            "ALTER TYPE operationstatus ADD VALUE IF NOT EXISTS 'pending_approval'"
        )
        return
    with op.batch_alter_table("organizations") as batch:
        batch.add_column(sa.Column("settings", sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_column("organizations", "settings")
        return
    with op.batch_alter_table("organizations") as batch:
        batch.drop_column("settings")
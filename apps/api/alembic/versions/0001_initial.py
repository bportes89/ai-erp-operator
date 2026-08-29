"""initial production schema"""

from alembic import op

from app.models import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Tables are created by metadata during the alpha; replace with explicit operations before first customer migration.
    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade():
    Base.metadata.drop_all(op.get_bind())
"""Add resource id to backing repo

Revision ID: c53623db6b65
Revises: e24445a6fabb
Create Date: 2019-07-31 16:02:46.940040

"""

# revision identifiers, used by Alembic.
revision = 'c53623db6b65'
down_revision = 'e24445a6fabb'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("backing_repo", sa.Column("resource_id", sa.Integer))
    op.alter_column("backing_repo", "webhook_id", nullable=True)


def downgrade():
    op.drop_column("backing_repo", "resource_id")
    op.alter_column("backing_repo", "webhook_id", nullable=False)

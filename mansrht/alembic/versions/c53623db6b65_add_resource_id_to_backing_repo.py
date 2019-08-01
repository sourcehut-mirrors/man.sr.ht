"""Add resource id to backing repo

Revision ID: c53623db6b65
Revises: e24445a6fabb
Create Date: 2019-07-31 16:02:46.940040

"""

# revision identifiers, used by Alembic.
revision = 'c53623db6b65'
down_revision = '7c8fb3fcd76a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("backing_repo", sa.Column("resource_id", sa.Integer))


def downgrade():
    op.drop_column("backing_repo", "resource_id")

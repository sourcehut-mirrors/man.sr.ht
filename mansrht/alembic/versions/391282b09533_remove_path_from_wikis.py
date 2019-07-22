"""Remove path from wikis

Revision ID: 391282b09533
Revises: 7c8fb3fcd76a
Create Date: 2019-07-29 09:21:43.328964

"""

# revision identifiers, used by Alembic.
revision = '391282b09533'
down_revision = '7c8fb3fcd76a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column("wiki", "path")
    op.alter_column("wiki", "repo_id", nullable=False)


def downgrade():
    op.add_column("wiki", sa.Column("path", sa.Unicode(1024)))
    op.alter_column("wiki", "repo_id", nullable=True)

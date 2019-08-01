"""Add repo webhooks to user

Revision ID: e24445a6fabb
Revises: 391282b09533
Create Date: 2019-07-31 16:02:19.155311

"""

# revision identifiers, used by Alembic.
revision = 'e24445a6fabb'
down_revision = '391282b09533'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("user", sa.Column("repo_update_webhook", sa.Integer))
    op.add_column("user", sa.Column("repo_delete_webhook", sa.Integer))


def downgrade():
    op.drop_column("user", "repo_update_webhook")
    op.drop_column("user", "repo_delete_webhook")

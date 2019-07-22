"""Migrate to use backing repo

Revision ID: 7c8fb3fcd76a
Revises: fc291f9a4808
Create Date: 2019-07-22 13:47:16.799213

"""

# revision identifiers, used by Alembic.
revision = '7c8fb3fcd76a'
down_revision = 'fc291f9a4808'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table("root_wiki",
            sa.Column("id", sa.Integer,
                sa.ForeignKey("wiki.id"), primary_key=True, nullable=False))
    op.create_table("backing_repo",
            sa.Column("id", sa.Integer, primary_key=True, nullable=False),
            sa.Column("new", sa.Boolean, nullable=False),
            sa.Column("name", sa.Unicode(256), nullable=False),
            sa.Column("ref", sa.Unicode(1024), nullable=False),
            sa.Column("commit_sha", sa.Unicode(256)),
            sa.Column("commit_author", sa.Unicode(256)),
            sa.Column("commit_email", sa.Unicode(256)),
            sa.Column("commit_time", sa.Unicode(256)),
            sa.Column("commit_message", sa.Unicode(1024)),
            sa.Column("tree_sha", sa.Unicode(256)),
            sa.Column("webhook_id", sa.Integer, nullable=False))
    op.add_column("wiki", sa.Column("repo_id", sa.Integer,
                sa.ForeignKey("backing_repo.id")))


def downgrade():
    op.drop_column("wiki", "repo_id")
    op.drop_table("root_wiki")
    op.drop_table("backing_repo")

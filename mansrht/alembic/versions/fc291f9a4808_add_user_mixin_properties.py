"""Add user mixin properties

Revision ID: fc291f9a4808
Revises: 03db50cf589f
Create Date: 2018-12-30 16:04:43.907400

"""

# revision identifiers, used by Alembic.
revision = 'fc291f9a4808'
down_revision = '03db50cf589f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("user", sa.Column("url", sa.String(256)))
    op.add_column("user", sa.Column("location", sa.Unicode(256)))
    op.add_column("user", sa.Column("bio", sa.Unicode(4096)))


def downgrade():
    op.delete_column("user", "url")
    op.delete_column("user", "location")
    op.delete_column("user", "bio")

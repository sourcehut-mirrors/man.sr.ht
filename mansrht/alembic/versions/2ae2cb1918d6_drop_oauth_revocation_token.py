"""Drop oauth_revocation_token

Revision ID: 2ae2cb1918d6
Revises: 4a25aadeac6f
Create Date: 2024-10-31 13:01:18.118942

"""

# revision identifiers, used by Alembic.
revision = '2ae2cb1918d6'
down_revision = '4a25aadeac6f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    ALTER TABLE "user" DROP COLUMN oauth_revocation_token;
    """)


def downgrade():
    op.execute("""
    ALTER TABLE "user"
    ADD COLUMN oauth_revocation_token character varying(256);
    """)

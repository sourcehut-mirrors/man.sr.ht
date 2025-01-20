"""Update user constraints

Revision ID: 9dbb1c9c8e75
Revises: 35d47ef308bc
Create Date: 2025-01-22 15:47:49.562716

"""

# revision identifiers, used by Alembic.
revision = '9dbb1c9c8e75'
down_revision = '35d47ef308bc'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    ALTER TABLE "user"
    ALTER COLUMN username SET NOT NULL;

    ALTER TABLE "user"
    ADD CONSTRAINT user_email_key
    UNIQUE (email);
    """)


def downgrade():
    op.execute("""
    ALTER TABLE "user"
    ALTER COLUMN username DROP NOT NULL;

    ALTER TABLE "user"
    DROP CONSTRIANT user_email_key
    """)

"""Convert user_type to pg enum

Revision ID: c305fbce2ce5
Revises: 2ae2cb1918d6
Create Date: 2024-11-08 09:33:28.744611

"""

# revision identifiers, used by Alembic.
revision = 'c305fbce2ce5'
down_revision = '2ae2cb1918d6'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    CREATE TYPE user_type AS ENUM (
        'UNCONFIRMED',
        'ACTIVE_NON_PAYING',
        'ACTIVE_FREE',
        'ACTIVE_PAYING',
        'ACTIVE_DELINQUENT',
        'ADMIN',
        'UNKNOWN',
        'SUSPENDED'
    );

    ALTER TABLE "user" ADD COLUMN user_type2 user_type;

    UPDATE "user" SET user_type2 = UPPER(user_type)::user_type;

    ALTER TABLE "user" DROP COLUMN user_type;
    ALTER TABLE "user" RENAME COLUMN user_type2 TO user_type;
    ALTER TABLE "user" ALTER COLUMN user_type SET NOT NULL;
    """)


def downgrade():
    op.execute("""
    ALTER TABLE "user" ADD COLUMN user_type2 character varying;
    UPDATE "user" SET user_type2 = LOWER(user_type::character varying);
    ALTER TABLE "user" DROP COLUMN user_type;
    ALTER TABLE "user" RENAME COLUMN user_type2 TO user_type;
    ALTER TABLE "user" ALTER COLUMN user_type SET NOT NULL;
    DROP TYPE user_type;
    """)

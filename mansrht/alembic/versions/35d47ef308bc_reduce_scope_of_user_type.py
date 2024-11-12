"""Reduce scope of user_type

Revision ID: 35d47ef308bc
Revises: c305fbce2ce5
Create Date: 2024-11-12 13:34:28.087029

"""

# revision identifiers, used by Alembic.
revision = '35d47ef308bc'
down_revision = 'c305fbce2ce5'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    CREATE TYPE user_type_new AS ENUM (
        'PENDING',
        'USER',
        'ADMIN',
        'SUSPENDED'
    );

    ALTER TABLE "user"
    ADD COLUMN user_type_new user_type_new;

    UPDATE "user"
    SET user_type_new = CASE
        WHEN user_type IN (
            'ACTIVE_NON_PAYING',
            'ACTIVE_FREE',
            'ACTIVE_PAYING',
            'ACTIVE_DELINQUENT'
        ) THEN 'USER'
        WHEN user_type = 'UNCONFIRMED' THEN 'PENDING'
        WHEN user_type = 'ADMIN' THEN 'ADMIN'
        WHEN user_type = 'SUSPENDED' THEN 'SUSPENDED'
        ELSE NULL
        END::user_type_new;

    ALTER TABLE "user" ALTER COLUMN user_type_new SET NOT NULL;
    ALTER TABLE "user" DROP COLUMN user_type;
    ALTER TABLE "user" RENAME user_type_new TO user_type;

    DROP TYPE user_type;
    ALTER TYPE user_type_new RENAME TO user_type;
    """)


def downgrade():
    assert False, "This migration is not reversible!"

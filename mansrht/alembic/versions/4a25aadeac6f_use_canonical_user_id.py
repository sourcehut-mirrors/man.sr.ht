"""Use canonical user ID

Revision ID: 4a25aadeac6f
Revises: 74fb41c265f8
Create Date: 2022-07-14 18:51:14.756975

"""

# revision identifiers, used by Alembic.
revision = '4a25aadeac6f'
down_revision = '74fb41c265f8'

from alembic import op
import sqlalchemy as sa


# These tables all have a column referencing "user"(id)
tables = [
    ("wiki", "owner_id"),
]

def upgrade():
    # Drop foreign key constraints and update user IDs
    for (table, col) in tables:
        op.execute(f"""
        ALTER TABLE {table} DROP CONSTRAINT {table}_{col}_fkey;
        UPDATE {table} t SET {col} = u.remote_id FROM "user" u WHERE u.id = t.{col};
        """)

    # Update primary key
    op.execute("""
    ALTER TABLE "user" DROP CONSTRAINT user_pkey;
    ALTER TABLE "user" DROP CONSTRAINT user_remote_id_key;
    ALTER TABLE "user" RENAME COLUMN id TO old_id;
    ALTER TABLE "user" RENAME COLUMN remote_id TO id;
    ALTER TABLE "user" ADD PRIMARY KEY (id);
    ALTER TABLE "user" ADD UNIQUE (old_id);
    """)

    # Add foreign key constraints
    for (table, col) in tables:
        op.execute(f"""
        ALTER TABLE {table} ADD CONSTRAINT {table}_{col}_fkey FOREIGN KEY ({col}) REFERENCES "user"(id) ON DELETE CASCADE;
        """)


def downgrade():
    # Drop foreign key constraints and update user IDs
    for (table, col) in tables:
        op.execute(f"""
        ALTER TABLE {table} DROP CONSTRAINT {table}_{col}_fkey;
        UPDATE {table} t SET {col} = u.old_id FROM "user" u WHERE u.id = t.{col};
        """)

    # Update primary key
    op.execute("""
    ALTER TABLE "user" DROP CONSTRAINT user_pkey;
    ALTER TABLE "user" DROP CONSTRAINT user_old_id_key;
    ALTER TABLE "user" RENAME COLUMN id TO remote_id;
    ALTER TABLE "user" RENAME COLUMN old_id TO id;
    ALTER TABLE "user" ADD PRIMARY KEY (id);
    ALTER TABLE "user" ADD UNIQUE (remote_id);
    """)

    # Add foreign key constraints
    for (table, col) in tables:
        op.execute(f"""
        ALTER TABLE {table} ADD CONSTRAINT {table}_{col}_fkey FOREIGN KEY ({col}) REFERENCES "user"(id) ON DELETE CASCADE;
        """)

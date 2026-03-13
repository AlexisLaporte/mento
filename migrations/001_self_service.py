"""Migrate to self-service multi-tenant model.

- Add owner_email to memento_projects
- Create memento_members table
- Migrate data from per-project memento_<slug>_users tables
- Drop old tables and initial_admin column
"""

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()


def run():
    conn = psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://localhost:5432/memento'))
    cur = conn.cursor()

    # 1. Add owner_email column if missing
    cur.execute("""
        ALTER TABLE memento_projects ADD COLUMN IF NOT EXISTS owner_email TEXT DEFAULT ''
    """)

    # 2. Create memento_members table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memento_members (
            project_slug TEXT REFERENCES memento_projects(slug) ON DELETE CASCADE,
            email TEXT NOT NULL,
            name TEXT,
            picture TEXT,
            role TEXT NOT NULL DEFAULT 'member',
            created_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (project_slug, email)
        )
    """)

    # 3. Get all existing projects
    cur.execute("SELECT slug FROM memento_projects")
    slugs = [row[0] for row in cur.fetchall()]

    for slug in slugs:
        safe = slug.lower().replace(' ', '_').replace('-', '_')
        old_table = f"memento_{safe}_users"

        # Check if old table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = %s
            )
        """, (old_table,))
        if not cur.fetchone()[0]:
            print(f"  {old_table} does not exist, skipping")
            continue

        # Migrate users to memento_members
        cur.execute(f"""
            INSERT INTO memento_members (project_slug, email, name, picture, role, created_at)
            SELECT %s, email, name, picture, role, created_at FROM {old_table}
            ON CONFLICT DO NOTHING
        """, (slug,))
        count = cur.rowcount
        print(f"  Migrated {count} users from {old_table}")

        # Set owner_email = first admin found
        cur.execute(f"""
            SELECT email FROM {old_table} WHERE role = 'admin' ORDER BY created_at LIMIT 1
        """)
        admin_row = cur.fetchone()
        if admin_row:
            cur.execute(
                "UPDATE memento_projects SET owner_email = %s WHERE slug = %s",
                (admin_row[0], slug),
            )
            print(f"  Set owner of '{slug}' to {admin_row[0]}")

        # Drop old table
        cur.execute(f"DROP TABLE {old_table}")
        print(f"  Dropped {old_table}")

    # 4. Drop initial_admin column if it exists
    cur.execute("""
        ALTER TABLE memento_projects DROP COLUMN IF EXISTS initial_admin
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete.")


if __name__ == '__main__':
    run()

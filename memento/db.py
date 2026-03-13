"""Database access — projects and members."""

import os

import psycopg2

from .config import ProjectConfig


def connect():
    return psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://localhost:5432/memento'))


# ─── Schema ──────────────────────────────────────────────────────────────────

def ensure_schema():
    """Create tables if they don't exist."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS memento_projects (
                    slug TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    repo_full_name TEXT NOT NULL,
                    installation_id BIGINT NOT NULL,
                    owner_email TEXT NOT NULL DEFAULT '',
                    docs_paths TEXT[] DEFAULT '{docs}',
                    allowed_files TEXT[] DEFAULT '{}',
                    allowed_domains TEXT[] DEFAULT '{}',
                    color TEXT DEFAULT '#6366F1',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
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
        conn.commit()


def _row_to_config(row) -> ProjectConfig:
    return ProjectConfig(
        slug=row[0], title=row[1], repo_full_name=row[2],
        installation_id=row[3], owner_email=row[4] or '',
        docs_paths=row[5] or ['docs'], allowed_files=row[6] or [],
        allowed_domains=row[7] or [], color=row[8] or '#6366F1',
    )


_PROJECT_COLS = """slug, title, repo_full_name, installation_id,
    owner_email, docs_paths, allowed_files, allowed_domains, color"""


# ─── Projects CRUD ───────────────────────────────────────────────────────────

def load_projects() -> dict[str, ProjectConfig]:
    """Load all projects."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PROJECT_COLS} FROM memento_projects ORDER BY created_at")
            return {row[0]: _row_to_config(row) for row in cur.fetchall()}


def get_project(slug: str) -> ProjectConfig | None:
    """Load a single project by slug."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PROJECT_COLS} FROM memento_projects WHERE slug = %s", (slug,))
            row = cur.fetchone()
            return _row_to_config(row) if row else None


def load_projects_for_user(email: str) -> dict[str, ProjectConfig]:
    """Projects where user is a member OR email domain is allowed."""
    domain = email.split('@')[-1]
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT {_PROJECT_COLS} FROM memento_projects p
                WHERE EXISTS (
                    SELECT 1 FROM memento_members m
                    WHERE m.project_slug = p.slug AND m.email = %s AND m.role != 'blocked'
                ) OR %s = ANY(p.allowed_domains)
                ORDER BY p.created_at
            """, (email, domain))
            return {row[0]: _row_to_config(row) for row in cur.fetchall()}


def create_project(slug: str, title: str, repo_full_name: str,
                   installation_id: int, owner_email: str, **kwargs):
    """Insert a new project and add owner as admin member."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO memento_projects (slug, title, repo_full_name, installation_id,
                    owner_email, docs_paths, allowed_files, allowed_domains, color)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                slug, title, repo_full_name, installation_id, owner_email,
                kwargs.get('docs_paths', ['docs']),
                kwargs.get('allowed_files', []),
                kwargs.get('allowed_domains', []),
                kwargs.get('color', '#6366F1'),
            ))
            # Auto-add owner as admin
            cur.execute("""
                INSERT INTO memento_members (project_slug, email, role)
                VALUES (%s, %s, 'admin')
                ON CONFLICT DO NOTHING
            """, (slug, owner_email))
        conn.commit()


def update_project(slug: str, **kwargs):
    """Update project fields."""
    allowed = {'title', 'repo_full_name', 'installation_id', 'docs_paths',
               'allowed_files', 'allowed_domains', 'color'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    set_clause = ', '.join(f'{k} = %s' for k in updates)
    values = list(updates.values()) + [slug]
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE memento_projects SET {set_clause} WHERE slug = %s", values)
        conn.commit()


def delete_project(slug: str):
    """Delete a project (CASCADE deletes members)."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM memento_projects WHERE slug = %s", (slug,))
        conn.commit()


# ─── Members CRUD ────────────────────────────────────────────────────────────

def member_exists(project_slug: str, email: str) -> bool:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM memento_members WHERE project_slug = %s AND email = %s",
                (project_slug, email),
            )
            return cur.fetchone() is not None


def get_member(project_slug: str, email: str) -> dict | None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email, name, picture, role FROM memento_members WHERE project_slug = %s AND email = %s",
                (project_slug, email),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {"email": row[0], "name": row[1], "picture": row[2], "role": row[3]}


def upsert_member(project_slug: str, email: str, name: str, picture: str) -> str:
    """Insert or update member, return role."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO memento_members (project_slug, email, name, picture)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (project_slug, email) DO UPDATE SET name = %s, picture = %s
                RETURNING role
            """, (project_slug, email, name, picture, name, picture))
            row = cur.fetchone()
        conn.commit()
    return row[0] if row else 'member'


def list_members(project_slug: str) -> list[dict]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT email, name, picture, role, created_at
                FROM memento_members WHERE project_slug = %s ORDER BY created_at
            """, (project_slug,))
            return [
                {"email": r[0], "name": r[1], "picture": r[2], "role": r[3], "created_at": str(r[4])}
                for r in cur.fetchall()
            ]


def invite_member(project_slug: str, email: str, name: str = ""):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO memento_members (project_slug, email, name, role)
                VALUES (%s, %s, %s, 'member')
                ON CONFLICT DO NOTHING
            """, (project_slug, email, name))
        conn.commit()


def set_member_role(project_slug: str, email: str, role: str) -> bool:
    if role not in ('blocked', 'member', 'admin'):
        return False
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE memento_members SET role = %s WHERE project_slug = %s AND email = %s",
                (role, project_slug, email),
            )
        conn.commit()
    return True


def delete_member(project_slug: str, email: str):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM memento_members WHERE project_slug = %s AND email = %s",
                (project_slug, email),
            )
        conn.commit()

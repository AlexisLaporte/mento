"""Google OAuth + role-based access for Memento.

Roles: blocked (no access), member (default), admin (manage users).
Users stored in PostgreSQL per-project tables: memento_<slug>_users.
Auth identity is global (one Google login), access control is per-project.
Dev mode (MEMENTO_DEV=1): skip auth entirely, auto-login as admin.
"""

import os
from functools import wraps

from flask import Blueprint, g, redirect, request, session, url_for, jsonify

auth_bp = Blueprint('auth', __name__)

_dev_mode = False
_db_module = None
oauth = None


def _db():
    return _db_module.connect(os.getenv('DATABASE_URL', 'postgresql://localhost:5432/memento'))


def get_table_name(slug: str) -> str:
    safe = slug.lower().replace(' ', '_').replace('-', '_')
    return f"memento_{safe}_users"


def _ensure_tables(table_name: str, initial_admin: str = ""):
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    email TEXT PRIMARY KEY,
                    name TEXT,
                    picture TEXT,
                    role TEXT NOT NULL DEFAULT 'member',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            if initial_admin:
                cur.execute(f"""
                    INSERT INTO {table_name} (email, name, role)
                    VALUES (%s, 'Admin', 'admin')
                    ON CONFLICT (email) DO NOTHING
                """, (initial_admin,))
        conn.commit()


def _upsert_user(table_name: str, email: str, name: str, picture: str) -> str:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO {table_name} (email, name, picture)
                VALUES (%s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET name = %s, picture = %s
                RETURNING role
            """, (email, name, picture, name, picture))
            row = cur.fetchone()
        conn.commit()
    return row[0] if row else 'member'


def _list_users(table_name: str) -> list[dict]:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT email, name, picture, role, created_at FROM {table_name} ORDER BY created_at")
            return [
                {"email": r[0], "name": r[1], "picture": r[2], "role": r[3], "created_at": str(r[4])}
                for r in cur.fetchall()
            ]


def _set_role(table_name: str, email: str, role: str) -> bool:
    if role not in ('blocked', 'member', 'admin'):
        return False
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE {table_name} SET role = %s WHERE email = %s", (role, email))
        conn.commit()
    return True


def _user_exists(table_name: str, email: str) -> bool:
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT 1 FROM {table_name} WHERE email = %s", (email,))
            return cur.fetchone() is not None


def _invite_user(table_name: str, email: str, name: str = ""):
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO {table_name} (email, name, role)
                VALUES (%s, %s, 'member')
                ON CONFLICT (email) DO NOTHING
            """, (email, name))
        conn.commit()


# ─── Auth init ────────────────────────────────────────────────────────────────

def init_auth(app):
    """Initialize auth globally. No per-project config — tables created lazily."""
    global _dev_mode
    _dev_mode = os.getenv('MEMENTO_DEV', '') == '1'

    if _dev_mode:
        return

    import psycopg2
    from authlib.integrations.flask_client import OAuth
    global _db_module, oauth
    _db_module = psycopg2

    oauth = OAuth()
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_OAUTH_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_OAUTH_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )


# ─── Decorators ───────────────────────────────────────────────────────────────

def requires_access(f):
    """Require authenticated + authorized user for the current project."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if _dev_mode:
            return f(*args, **kwargs)

        user = session.get('user')
        if not user:
            if request.is_json or request.path.startswith(f'/{g.project}/api/'):
                return jsonify({"error": "Authentication required"}), 401
            session['next'] = request.url
            return redirect(url_for('auth.login'))

        email = user['email']
        config = g.config
        domain = email.split('@')[-1]
        table_name = get_table_name(g.project)

        # Check access: allowed domain, allowed email, or existing user
        allowed = (
            domain in config.auth.allowed_domains
            or email in config.auth.allowed_emails
            or _user_exists(table_name, email)
        )
        if not allowed:
            domains_str = ', '.join(f'@{d}' for d in config.auth.allowed_domains) or 'invited accounts'
            return f'''<!DOCTYPE html>
<html><head><title>Access denied</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
<div class="text-center">
<p class="text-red-500 font-medium mb-2">Access denied</p>
<p class="text-gray-500 text-sm mb-4">{email} is not authorized for {config.branding.title}.<br>Only {domains_str} are allowed.</p>
<a href="/" class="text-indigo-600 hover:underline text-sm">Back</a>
</div></body></html>''', 403

        # Ensure table exists and upsert user
        _ensure_tables(table_name, config.auth.initial_admin)
        role = _upsert_user(table_name, email, user['name'], user.get('picture', ''))
        g.user_role = role

        if role == 'blocked':
            color = config.branding.color
            return f'''<!DOCTYPE html>
<html><head><title>Access pending</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
<div class="text-center">
<p class="text-gray-500 mb-2">Your access is pending approval.</p>
<p class="text-gray-400 text-sm mb-4">Contact an administrator.</p>
<a href="{url_for('auth.logout')}" class="hover:underline text-sm" style="color:{color}">Logout</a>
</div></body></html>''', 403

        return f(*args, **kwargs)
    return decorated


def requires_admin(f):
    """Require admin role for the current project."""
    @wraps(f)
    @requires_access
    def decorated(*args, **kwargs):
        if not _dev_mode and g.user_role != 'admin':
            return jsonify({"error": "Admin required"}), 403
        return f(*args, **kwargs)
    return decorated


# ─── Routes ───────────────────────────────────────────────────────────────────

@auth_bp.route('/login')
def login():
    if _dev_mode:
        session['user'] = {'email': 'dev@local', 'name': 'Dev', 'picture': ''}
        next_url = request.args.get('next', '/')
        return redirect(next_url)
    # Preserve next URL from requires_access if not overridden by query param
    next_url = request.args.get('next') or session.get('next', '/')
    session['next'] = next_url
    redirect_uri = url_for('auth.callback', _external=True)
    prompt = 'select_account' if session.pop('force_prompt', False) else None
    kwargs = {}
    if prompt:
        kwargs['prompt'] = prompt
    return oauth.google.authorize_redirect(redirect_uri, **kwargs)


@auth_bp.route('/callback')
def callback():
    token = oauth.google.authorize_access_token()
    userinfo = token.get('userinfo', {})
    email = userinfo.get('email', '')
    name = userinfo.get('name', '')
    picture = userinfo.get('picture', '')
    session['user'] = {'email': email, 'name': name, 'picture': picture}
    next_url = session.pop('next', '/')
    return redirect(next_url)


@auth_bp.route('/logout')
def logout():
    session.clear()
    session['force_prompt'] = True
    return redirect('/')

"""Google OAuth + role-based access for Memento.

Roles: blocked (no access), member (default), admin (manage users).
Users stored in PostgreSQL `users` table (per-instance, prefixed by app name).
Dev mode (MEMENTO_DEV=1): skip auth entirely, auto-login as admin.
"""

import os
from functools import wraps

from flask import Blueprint, redirect, request, session, url_for, jsonify

auth_bp = Blueprint('auth', __name__)

# Set at init_auth() time from config
_config = None
_table_name = "memento_users"
_dev_mode = False


_db_module = None
oauth = None


def _db():
    return _db_module.connect(os.getenv('DATABASE_URL', 'postgresql://localhost:5432/memento'))


def _ensure_tables():
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {_table_name} (
                    email TEXT PRIMARY KEY,
                    name TEXT,
                    picture TEXT,
                    role TEXT NOT NULL DEFAULT 'member',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            if _config and _config.auth.initial_admin:
                cur.execute(f"""
                    INSERT INTO {_table_name} (email, name, role)
                    VALUES (%s, 'Admin', 'admin')
                    ON CONFLICT (email) DO NOTHING
                """, (_config.auth.initial_admin,))
        conn.commit()


def _upsert_user(email, name, picture):
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO {_table_name} (email, name, picture)
                VALUES (%s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET name = %s, picture = %s
                RETURNING role
            """, (email, name, picture, name, picture))
            row = cur.fetchone()
        conn.commit()
    return row[0] if row else 'member'


def _list_users():
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT email, name, picture, role, created_at FROM {_table_name} ORDER BY created_at")
            return [
                {"email": r[0], "name": r[1], "picture": r[2], "role": r[3], "created_at": str(r[4])}
                for r in cur.fetchall()
            ]


def _set_role(email, role):
    if role not in ('blocked', 'member', 'admin'):
        return False
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE {_table_name} SET role = %s WHERE email = %s", (role, email))
        conn.commit()
    return True


def _user_exists(email):
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT 1 FROM {_table_name} WHERE email = %s", (email,))
            return cur.fetchone() is not None


def _invite_user(email, name=None):
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO {_table_name} (email, name, role)
                VALUES (%s, %s, 'member')
                ON CONFLICT (email) DO NOTHING
            """, (email, name or ''))
        conn.commit()


# ─── Auth init ────────────────────────────────────────────────────────────────

def init_auth(app, config):
    """Initialize auth. In dev mode, skip OAuth + DB entirely."""
    global _config, _table_name, _dev_mode
    _config = config
    _dev_mode = os.getenv('MEMENTO_DEV', '') == '1'

    if _dev_mode:
        return

    import psycopg2  # noqa: deferred import — not needed in dev mode
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

    safe_name = config.name.lower().replace(' ', '_').replace('-', '_')
    _table_name = f"memento_{safe_name}_users"
    _ensure_tables()


# ─── Decorators ───────────────────────────────────────────────────────────────

def requires_access(f):
    """Require authenticated + non-blocked user. No-op in dev mode."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if _dev_mode:
            return f(*args, **kwargs)
        user = session.get('user')
        if not user:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"error": "Authentication required"}), 401
            session['next'] = request.url
            return redirect('/')
        if user.get('role') == 'blocked':
            color = _config.branding.color if _config else '#6366F1'
            return f'''<!DOCTYPE html>
<html><head><title>Access pending</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
<div class="text-center">
<p class="text-gray-500 mb-2">Your access is pending approval.</p>
<p class="text-gray-400 text-sm mb-4">Contact an administrator.</p>
<a href="/auth/logout" class="hover:underline text-sm" style="color:{color}">Logout</a>
</div></body></html>''', 403
        return f(*args, **kwargs)
    return decorated


def requires_admin(f):
    """Require admin role."""
    @wraps(f)
    @requires_access
    def decorated(*args, **kwargs):
        if session.get('user', {}).get('role') != 'admin':
            return jsonify({"error": "Admin required"}), 403
        return f(*args, **kwargs)
    return decorated


def get_user_email():
    user = session.get('user')
    return user['email'] if user else None


# ─── Routes ───────────────────────────────────────────────────────────────────

@auth_bp.route('/login')
def login():
    if _dev_mode:
        session['user'] = {'email': 'dev@local', 'name': 'Dev', 'picture': '', 'role': 'admin'}
        return redirect('/')
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
    domain = email.split('@')[-1] if email else ''

    allowed_domains = _config.auth.allowed_domains if _config else []
    allowed_emails = _config.auth.allowed_emails if _config else []

    if domain not in allowed_domains and email not in allowed_emails and not _user_exists(email):
        session.clear()
        title = _config.branding.title if _config else 'Memento'
        domains_str = ', '.join(f'@{d}' for d in allowed_domains) or 'invited accounts'
        return f'''<!DOCTYPE html>
<html><head><title>Access denied</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
<div class="text-center">
<p class="text-red-500 font-medium mb-2">Access denied</p>
<p class="text-gray-500 text-sm mb-4">{email} is not authorized.<br>Only {domains_str} are allowed.</p>
<a href="/" class="text-indigo-600 hover:underline text-sm">Back</a>
</div></body></html>''', 403

    name = userinfo.get('name', '')
    picture = userinfo.get('picture', '')
    role = _upsert_user(email, name, picture)
    session['user'] = {'email': email, 'name': name, 'picture': picture, 'role': role}
    next_url = session.pop('next', '/')
    return redirect(next_url)


@auth_bp.route('/logout')
def logout():
    session.clear()
    session['force_prompt'] = True
    return redirect(url_for('auth.login'))


@auth_bp.route('/admin')
@requires_admin
def admin():
    users = _list_users()
    color = _config.branding.color if _config else '#6366F1'
    title = _config.branding.title if _config else 'Memento'
    rows = ''
    for u in users:
        role_cls = {
            'admin': 'bg-purple-100 text-purple-700',
            'member': 'bg-green-100 text-green-700',
            'blocked': 'bg-red-100 text-red-700',
        }.get(u['role'], 'bg-gray-100 text-gray-600')
        options = ''.join(
            f'<option value="{r}" {"selected" if r == u["role"] else ""}>{r}</option>'
            for r in ('blocked', 'member', 'admin')
        )
        rows += f'''<tr class="border-t border-gray-100">
            <td class="px-4 py-3 text-sm">{u['email']}</td>
            <td class="px-4 py-3 text-sm text-gray-600">{u['name'] or ''}</td>
            <td class="px-4 py-3"><span class="text-xs px-2 py-0.5 rounded-full {role_cls}">{u['role']}</span></td>
            <td class="px-4 py-3">
                <form method="post" action="/auth/admin/{u['email']}/role" class="flex gap-2 items-center">
                    <select name="role" class="text-xs border rounded px-2 py-1">{options}</select>
                    <button class="text-xs text-white px-2 py-1 rounded hover:opacity-90" style="background:{color}">Save</button>
                </form>
            </td>
        </tr>'''

    return f'''<!DOCTYPE html>
<html><head><title>Admin - {title}</title><script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>body {{ font-family: 'Inter', system-ui, sans-serif; }}</style></head>
<body class="bg-gray-50 min-h-screen p-8">
<div class="max-w-3xl mx-auto">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-lg font-semibold text-gray-900">User Management</h1>
        <a href="/" class="text-sm hover:underline" style="color:{color}">Back to docs</a>
    </div>
    <div class="bg-white rounded-lg shadow-sm overflow-hidden mb-6">
        <table class="w-full">
            <thead class="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr><th class="px-4 py-2 text-left">Email</th><th class="px-4 py-2 text-left">Name</th>
                <th class="px-4 py-2 text-left">Role</th><th class="px-4 py-2 text-left">Action</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    <div class="bg-white rounded-lg shadow-sm p-4">
        <h2 class="text-sm font-semibold text-gray-900 mb-3">Invite user</h2>
        <form method="post" action="/auth/admin/invite" class="flex gap-2 items-end">
            <div><label class="text-xs text-gray-500">Email</label>
            <input name="email" type="email" required placeholder="user@example.com" class="block text-sm border rounded px-3 py-1.5 w-64"></div>
            <div><label class="text-xs text-gray-500">Name (optional)</label>
            <input name="name" type="text" placeholder="First Last" class="block text-sm border rounded px-3 py-1.5 w-48"></div>
            <button class="text-sm text-white px-4 py-1.5 rounded hover:opacity-90" style="background:{color}">Invite</button>
        </form>
    </div>
</div></body></html>'''


@auth_bp.route('/admin/invite', methods=['POST'])
@requires_admin
def admin_invite():
    email = request.form.get('email', '').strip().lower()
    name = request.form.get('name', '').strip()
    if email:
        _invite_user(email, name)
    return redirect(url_for('auth.admin'))


@auth_bp.route('/admin/<path:email>/role', methods=['POST'])
@requires_admin
def admin_set_role(email):
    role = request.form.get('role')
    _set_role(email, role)
    return redirect(url_for('auth.admin'))

"""Auth0 OAuth + role-based access for Memento.

Roles: blocked (no access), member (default), admin (manage users).
Members stored in memento_members table (unified).
Auth identity via Auth0, access control per-project.
Dev mode (MEMENTO_DEV=1): skip auth entirely, auto-login as admin.
"""

import os
from functools import wraps

from flask import Blueprint, abort, g, redirect, request, session, url_for, jsonify

from . import db

auth_bp = Blueprint('auth', __name__)

_dev_mode = False
oauth = None


# ─── Auth init ────────────────────────────────────────────────────────────────

def init_auth(app):
    """Initialize Auth0 OAuth globally."""
    global _dev_mode
    _dev_mode = os.getenv('MEMENTO_DEV', '') == '1'

    if _dev_mode:
        return

    from authlib.integrations.flask_client import OAuth
    global oauth

    auth0_domain = os.getenv('AUTH0_DOMAIN')
    oauth = OAuth()
    oauth.init_app(app)
    oauth.register(
        name='auth0',
        client_id=os.getenv('AUTH0_CLIENT_ID'),
        client_secret=os.getenv('AUTH0_CLIENT_SECRET'),
        server_metadata_url=f'https://{auth0_domain}/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid profile email'},
    )


# ─── Decorators ───────────────────────────────────────────────────────────────

def requires_auth(f):
    """Require authenticated user (any project)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if _dev_mode:
            return f(*args, **kwargs)
        user = session.get('user')
        if not user:
            session['next'] = request.url
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


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

        # Check access: domain allowlist or explicit membership
        allowed = (
            domain in config.allowed_domains
            or db.member_exists(g.project, email)
        )
        if not allowed:
            return f'''<!DOCTYPE html>
<html><head><title>Access denied</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
<div class="text-center">
<p class="text-red-500 font-medium mb-2">Access denied</p>
<p class="text-gray-500 text-sm mb-4">{email} is not authorized for {config.title}.<br>Ask an admin to invite you.</p>
<a href="/" class="text-indigo-600 hover:underline text-sm">Back</a>
</div></body></html>''', 403

        # Upsert member and get role
        role = db.upsert_member(g.project, email, user['name'], user.get('picture', ''))
        g.user_role = role

        if role == 'blocked':
            return f'''<!DOCTYPE html>
<html><head><title>Access pending</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
<div class="text-center">
<p class="text-gray-500 mb-2">Your access is pending approval.</p>
<a href="{url_for('auth.logout')}" class="hover:underline text-sm" style="color:{config.color}">Logout</a>
</div></body></html>''', 403

        return f(*args, **kwargs)
    return decorated


def requires_admin(f):
    """Require admin role or project owner."""
    @wraps(f)
    @requires_access
    def decorated(*args, **kwargs):
        if _dev_mode:
            return f(*args, **kwargs)
        email = session['user']['email']
        is_admin = g.user_role == 'admin' or g.config.owner_email == email
        if not is_admin:
            return jsonify({"error": "Admin required"}), 403
        return f(*args, **kwargs)
    return decorated


def requires_super_admin(f):
    """Require super admin (global Memento admin)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if _dev_mode:
            return f(*args, **kwargs)
        user = session.get('user')
        if not user:
            session['next'] = request.url
            return redirect(url_for('auth.login'))
        admins = [e.strip() for e in os.getenv('MEMENTO_SUPER_ADMINS', '').split(',') if e.strip()]
        if user['email'] not in admins:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def has_project_access(slug: str, config, email: str) -> bool:
    """Check if a user has access to a project (for the project selector)."""
    domain = email.split('@')[-1]
    if domain in config.allowed_domains:
        return True
    if _dev_mode:
        return False
    return db.member_exists(slug, email)


# ─── Routes ───────────────────────────────────────────────────────────────────

@auth_bp.route('/login')
def login():
    if _dev_mode:
        session['user'] = {'email': 'dev@local', 'name': 'Dev', 'picture': ''}
        next_url = request.args.get('next', '/')
        return redirect(next_url)
    next_url = request.args.get('next') or session.get('next', '/')
    session['next'] = next_url
    redirect_uri = url_for('auth.callback', _external=True)
    return oauth.auth0.authorize_redirect(redirect_uri)


@auth_bp.route('/callback')
def callback():
    token = oauth.auth0.authorize_access_token()
    userinfo = token.get('userinfo', {})
    session['user'] = {
        'email': userinfo.get('email', ''),
        'name': userinfo.get('name', ''),
        'picture': userinfo.get('picture', ''),
    }
    next_url = session.pop('next', '/')
    return redirect(next_url)


@auth_bp.route('/logout')
def logout():
    auth0_domain = os.getenv('AUTH0_DOMAIN')
    client_id = os.getenv('AUTH0_CLIENT_ID')
    return_to = request.host_url.rstrip('/')
    session.clear()
    if _dev_mode:
        return redirect('/')
    return redirect(
        f'https://{auth0_domain}/v2/logout?client_id={client_id}&returnTo={return_to}'
    )

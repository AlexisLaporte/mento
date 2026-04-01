"""Auth0 OAuth + role-based access for Mento.

Roles: blocked (no access), member (default), admin (manage users).
Members stored in memento_members table (unified).
Auth identity via Auth0, access control per-project via explicit membership.
"""

import os
from functools import wraps
from urllib.parse import urljoin, urlparse

import httpx
from flask import Blueprint, abort, g, jsonify, redirect, request, session, url_for

from . import db

auth_bp = Blueprint('auth', __name__)

oauth = None


# ─── Auth init ────────────────────────────────────────────────────────────────

def init_auth(app):
    """Initialize Auth0 OAuth globally."""
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


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


# ─── Decorators ───────────────────────────────────────────────────────────────

def requires_auth(f):
    """Require authenticated user (any project)."""
    @wraps(f)
    def decorated(*args, **kwargs):
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
        # Public projects: allow anonymous read access
        if getattr(g, 'config', None) and g.config.is_public:
            user = session.get('user')
            if user and db.member_exists(g.project, user['email']):
                g.user_role = db.upsert_member(g.project, user['email'], user['name'], user.get('picture', ''))
            else:
                g.user_role = 'viewer'
            return f(*args, **kwargs)

        user = session.get('user')
        if not user:
            if request.is_json or request.path.startswith(f'/{g.project}/api/'):
                return jsonify({"error": "Authentication required"}), 401
            session['next'] = request.url
            return redirect(url_for('auth.login'))

        email = user['email']
        config = g.config

        if not db.member_exists(g.project, email):
            return jsonify({"error": f"{email} is not a member of {config.title}"}), 403

        # Upsert member and get role
        role = db.upsert_member(g.project, email, user['name'], user.get('picture', ''))
        g.user_role = role

        if role == 'blocked':
            return jsonify({"error": "Your access is pending approval"}), 403

        return f(*args, **kwargs)
    return decorated


def requires_admin(f):
    """Require admin role or project owner."""
    @wraps(f)
    @requires_access
    def decorated(*args, **kwargs):
        email = session['user']['email']
        is_admin = g.user_role == 'admin' or g.config.owner_email == email
        if not is_admin:
            return jsonify({"error": "Admin required"}), 403
        return f(*args, **kwargs)
    return decorated


def requires_super_admin(f):
    """Require super admin (global Mento admin)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get('user')
        if not user:
            session['next'] = request.url
            return redirect(url_for('auth.login'))
        admins = [e.strip() for e in os.getenv('MEMENTO_SUPER_ADMINS', '').split(',') if e.strip()]
        if user['email'] not in admins:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ─── Routes ───────────────────────────────────────────────────────────────────

@auth_bp.route('/login')
def login():
    next_url = request.args.get('next') or session.get('next', '/')
    if not _is_safe_url(next_url):
        next_url = '/'
    session['next'] = next_url
    redirect_uri = url_for('auth.callback', _external=True)
    return oauth.auth0.authorize_redirect(redirect_uri)


@auth_bp.route('/callback')
def callback():
    # GitHub App installation redirect — not an Auth0 callback
    if request.args.get('setup_action'):
        return redirect('/new')
    token = oauth.auth0.authorize_access_token()
    userinfo = token.get('userinfo', {})
    email = userinfo.get('email', '')
    name = userinfo.get('name', '')
    picture = userinfo.get('picture', '')
    session['user'] = {'email': email, 'name': name, 'picture': picture}
    db.upsert_user(email, name, picture, auth0_sub=userinfo.get('sub', ''))
    next_url = session.pop('next', '/')
    if not _is_safe_url(next_url):
        next_url = '/'
    return redirect(next_url)


@auth_bp.route('/github')
@requires_auth
def github_connect():
    """Redirect to GitHub OAuth to get a user-to-server token."""
    client_id = os.getenv('GITHUB_APP_CLIENT_ID')
    redirect_uri = url_for('auth.github_callback', _external=True)
    return redirect(
        f'https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}'
    )


@auth_bp.route('/github/callback')
@requires_auth
def github_callback():
    """Exchange GitHub OAuth code for user access token."""
    code = request.args.get('code')
    if not code:
        return redirect('/new')
    resp = httpx.post(
        'https://github.com/login/oauth/access_token',
        data={
            'client_id': os.getenv('GITHUB_APP_CLIENT_ID'),
            'client_secret': os.getenv('GITHUB_APP_CLIENT_SECRET'),
            'code': code,
        },
        headers={'Accept': 'application/json'},
    )
    token = resp.json().get('access_token')
    if token:
        session['github_token'] = token
    return redirect('/new')


@auth_bp.route('/logout')
def logout():
    auth0_domain = os.getenv('AUTH0_DOMAIN')
    client_id = os.getenv('AUTH0_CLIENT_ID')
    return_to = request.host_url.rstrip('/')
    session.clear()
    return redirect(
        f'https://{auth0_domain}/v2/logout?client_id={client_id}&returnTo={return_to}'
    )

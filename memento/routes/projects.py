"""Project listing, self-service creation, and user info (JSON APIs)."""

import os
import re

import httpx
from flask import Blueprint, jsonify, request, session

from .. import db, repo
from ..auth import requires_auth
from ..github_app import github_api

projects_bp = Blueprint('projects', __name__)

_GITHUB_APP_NAME = os.getenv('GITHUB_APP_NAME', 'memento-document')


def _github_headers() -> dict:
    """Headers for GitHub API calls using the user's OAuth token."""
    token = session.get('github_token', '')
    return {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'}


def _list_installations() -> list[dict]:
    """List GitHub App installations accessible to the current user."""
    token = session.get('github_token')
    if not token:
        return []
    try:
        resp = httpx.get(
            'https://api.github.com/user/installations',
            headers=_github_headers(),
        )
        if resp.status_code != 200:
            return []
        return [
            {'id': inst['id'], 'account': inst['account']['login'], 'avatar': inst['account']['avatar_url']}
            for inst in resp.json().get('installations', [])
        ]
    except Exception:
        return []


def _list_repos_for_installation(installation_id: int) -> list[dict]:
    """List repos accessible to the user for a specific installation."""
    token = session.get('github_token')
    if not token:
        return []
    try:
        resp = httpx.get(
            f'https://api.github.com/user/installations/{installation_id}/repositories',
            headers=_github_headers(),
            params={'per_page': '100'},
        )
        if resp.status_code != 200:
            return []
        return [
            {'full_name': r['full_name'], 'name': r['name'], 'private': r['private']}
            for r in resp.json().get('repositories', [])
        ]
    except Exception:
        return []


@projects_bp.route('/api/me')
def api_me():
    user = session.get('user')
    if not user:
        return jsonify({"authenticated": False})
    admins = [e.strip() for e in os.getenv('MEMENTO_SUPER_ADMINS', '').split(',') if e.strip()]
    return jsonify({
        "authenticated": True,
        "email": user['email'],
        "name": user['name'],
        "picture": user.get('picture', ''),
        "is_super_admin": user['email'] in admins,
        "github_connected": bool(session.get('github_token')),
    })


@projects_bp.route('/api/projects')
@requires_auth
def api_list_projects():
    user = session['user']
    email = user['email']
    projects = db.load_projects_for_user(email)
    return jsonify([{
        "slug": slug,
        "title": c.title,
        "color": c.color,
        "repo_full_name": c.repo_full_name,
        "is_owner": c.owner_email == email,
    } for slug, c in projects.items()])


@projects_bp.route('/api/projects', methods=['POST'])
@requires_auth
def api_create_project():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    user = session['user']
    slug = data.get('slug', '').strip().lower().replace(' ', '-')
    title = data.get('title', '').strip()
    repo_full_name = data.get('repo', '').strip()

    if not slug or not title or not repo_full_name:
        return jsonify({"error": "slug, title, and repo are required"}), 400

    # Validate slug: only lowercase alphanumeric and hyphens
    if not re.match(r'^[a-z0-9-]+$', slug):
        return jsonify({"error": "Slug can only contain lowercase letters, numbers, and hyphens"}), 400

    # Validate repo_full_name: owner/repo format
    if not re.match(r'^[a-zA-Z0-9-._]+/[a-zA-Z0-9-._]+$', repo_full_name):
        return jsonify({"error": "Invalid repository format (expected owner/repo)"}), 400

    if db.get_project(slug):
        return jsonify({"error": "Project slug already exists"}), 409

    # Find the installation that has access
    owner = repo_full_name.split('/')[0]
    installations = _list_installations()
    installation_id = None
    for inst in installations:
        if inst['account'].lower() == owner.lower():
            installation_id = inst['id']
            break

    if not installation_id:
        return jsonify({"error": f"GitHub App not installed on {owner}"}), 400

    docs_paths = data.get('docs_paths', ['docs'])
    if isinstance(docs_paths, str):
        docs_paths = [p.strip() for p in docs_paths.split(',') if p.strip()]
    color = data.get('color', '#6366F1').strip()

    # Resolve default branch from GitHub (one-time call)
    try:
        repo_info = github_api(installation_id, f'/repos/{repo_full_name}')
        default_branch = repo_info.get('default_branch', 'main')
    except Exception:
        default_branch = 'main'

    db.create_project(
        slug=slug, title=title, repo_full_name=repo_full_name,
        installation_id=installation_id, owner_email=user['email'],
        docs_paths=docs_paths, color=color, default_branch=default_branch,
    )

    # Clone repo locally
    try:
        repo.clone_repo(slug, repo_full_name, installation_id, default_branch)
    except Exception:
        pass  # Project created in DB, clone can be retried via sync

    return jsonify({"slug": slug})


@projects_bp.route('/api/installations')
@requires_auth
def api_installations():
    return jsonify(_list_installations())


@projects_bp.route('/api/installations/<int:installation_id>/repos')
@requires_auth
def api_installation_repos(installation_id):
    return jsonify(_list_repos_for_installation(installation_id))


@projects_bp.route('/api/github-app-name')
@requires_auth
def api_github_app_name():
    return jsonify({"name": _GITHUB_APP_NAME})

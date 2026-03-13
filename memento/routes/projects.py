"""Self-service project creation."""

import os

from flask import Blueprint, abort, jsonify, redirect, request, session

from .. import db
from ..auth import requires_auth
from ..github_app import get_app_jwt, get_installation_token, github_api

projects_bp = Blueprint('projects', __name__)

_GITHUB_APP_NAME = os.getenv('GITHUB_APP_NAME', 'memento-document')
_INSTALL_URL = f'https://github.com/apps/{_GITHUB_APP_NAME}/installations/new'


def _find_installation_for_repo(repo_full_name: str) -> int | None:
    """Find the GitHub App installation_id that has access to a given repo."""
    import httpx
    try:
        jwt_token = get_app_jwt()
        resp = httpx.get(
            'https://api.github.com/app/installations',
            headers={'Authorization': f'Bearer {jwt_token}', 'Accept': 'application/vnd.github+json'},
        )
        if resp.status_code != 200:
            return None
        for inst in resp.json():
            token = get_installation_token(inst['id'])
            check = httpx.get(
                f'https://api.github.com/repos/{repo_full_name}',
                headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'},
            )
            if check.status_code == 200:
                return inst['id']
    except Exception:
        pass
    return None


@projects_bp.route('/new')
@requires_auth
def new_project_page():
    return f'''<!DOCTYPE html>
<html><head><title>New project — Memento</title><script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>body {{ font-family: 'Inter', system-ui, sans-serif; }}</style></head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
<div class="w-full max-w-lg p-8">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-lg font-semibold text-gray-900">New project</h1>
        <a href="/" class="text-sm text-gray-500 hover:text-gray-700">Cancel</a>
    </div>
    <form method="post" action="/api/projects" class="bg-white rounded-lg shadow-sm p-6 space-y-4">
        <div>
            <label class="text-xs text-gray-500">Slug (URL identifier)</label>
            <input name="slug" required placeholder="my-project" pattern="[a-z0-9-]+"
                   class="block w-full text-sm border rounded px-3 py-2 mt-1">
        </div>
        <div>
            <label class="text-xs text-gray-500">Title</label>
            <input name="title" required placeholder="My Project"
                   class="block w-full text-sm border rounded px-3 py-2 mt-1">
        </div>
        <div>
            <label class="text-xs text-gray-500">GitHub Repository</label>
            <input name="repo" required placeholder="owner/repo"
                   class="block w-full text-sm border rounded px-3 py-2 mt-1">
            <p class="text-xs text-gray-400 mt-1">
                The <a href="{_INSTALL_URL}" target="_blank" class="text-indigo-600 hover:underline">Memento GitHub App</a>
                must be installed on this repo.
                <a href="{_INSTALL_URL}" target="_blank" class="text-indigo-600 hover:underline">Install it here</a>.
            </p>
        </div>
        <div>
            <label class="text-xs text-gray-500">Color</label>
            <input name="color" value="#6366F1" type="color" class="block h-9 w-20 border rounded mt-1">
        </div>
        <div>
            <label class="text-xs text-gray-500">Docs paths (comma-separated)</label>
            <input name="docs_paths" value="docs" class="block w-full text-sm border rounded px-3 py-2 mt-1">
        </div>
        <div id="error" class="hidden text-sm text-red-500"></div>
        <button class="w-full text-sm text-white py-2 rounded bg-indigo-600 hover:bg-indigo-700">Create project</button>
    </form>
</div></body></html>'''


@projects_bp.route('/api/projects', methods=['POST'])
@requires_auth
def create_project_route():
    user = session['user']
    slug = request.form.get('slug', '').strip().lower().replace(' ', '-')
    title = request.form.get('title', '').strip()
    repo_raw = request.form.get('repo', '').strip()
    # Accept full URLs like https://github.com/owner/repo
    repo_full_name = repo_raw.replace('https://github.com/', '').replace('http://github.com/', '').strip('/')

    if not slug or not title or not repo_full_name or '/' not in repo_full_name:
        abort(400)

    if db.get_project(slug):
        abort(409)

    installation_id = _find_installation_for_repo(repo_full_name)
    if not installation_id:
        return f'''<!DOCTYPE html>
<html><head><title>Error</title><script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>body {{ font-family: 'Inter', system-ui, sans-serif; }}</style></head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
<div class="text-center max-w-md">
    <p class="text-red-500 font-medium mb-2">GitHub App not installed</p>
    <p class="text-sm text-gray-500 mb-4">
        The Memento GitHub App does not have access to <strong>{repo_full_name}</strong>.<br>
        Please <a href="{_INSTALL_URL}" class="text-indigo-600 hover:underline">install it</a> on your repo first.
    </p>
    <a href="/new" class="text-sm text-indigo-600 hover:underline">Back</a>
</div></body></html>''', 400

    docs_paths = [p.strip() for p in request.form.get('docs_paths', 'docs').split(',') if p.strip()]
    color = request.form.get('color', '#6366F1').strip()

    db.create_project(
        slug=slug, title=title, repo_full_name=repo_full_name,
        installation_id=installation_id, owner_email=user['email'],
        docs_paths=docs_paths, color=color,
    )
    return redirect(f'/{slug}/')

"""Self-service project creation."""

from flask import Blueprint, abort, jsonify, redirect, request, session

from .. import db
from ..auth import requires_auth
from ..github_app import get_available_repos

projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/new')
@requires_auth
def new_project_page():
    repos = get_available_repos()
    repo_options = ''.join(
        f'<option value="{r["full_name"]}|{r["installation_id"]}">{r["full_name"]}</option>'
        for r in repos
    )

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
            <select name="repo" required class="block w-full text-sm border rounded px-3 py-2 mt-1">
                <option value="">Select a repo...</option>
                {repo_options}
            </select>
        </div>
        <div>
            <label class="text-xs text-gray-500">Color</label>
            <input name="color" value="#6366F1" type="color" class="block h-9 w-20 border rounded mt-1">
        </div>
        <div>
            <label class="text-xs text-gray-500">Docs paths (comma-separated)</label>
            <input name="docs_paths" value="docs" class="block w-full text-sm border rounded px-3 py-2 mt-1">
        </div>
        <button class="w-full text-sm text-white py-2 rounded bg-indigo-600 hover:bg-indigo-700">Create project</button>
    </form>
</div></body></html>'''


@projects_bp.route('/api/repos')
@requires_auth
def api_repos():
    return jsonify(get_available_repos())


@projects_bp.route('/api/projects', methods=['POST'])
@requires_auth
def create_project_route():
    user = session['user']
    slug = request.form.get('slug', '').strip().lower().replace(' ', '-')
    title = request.form.get('title', '').strip()
    repo_raw = request.form.get('repo', '')

    if not slug or not title or '|' not in repo_raw:
        abort(400)

    if db.get_project(slug):
        abort(409)

    repo_full_name, installation_id = repo_raw.rsplit('|', 1)
    docs_paths = [p.strip() for p in request.form.get('docs_paths', 'docs').split(',') if p.strip()]
    color = request.form.get('color', '#6366F1').strip()

    db.create_project(
        slug=slug, title=title, repo_full_name=repo_full_name,
        installation_id=int(installation_id), owner_email=user['email'],
        docs_paths=docs_paths, color=color,
    )
    return redirect(f'/{slug}/')

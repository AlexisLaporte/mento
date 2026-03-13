"""Global admin — super admin oversight + GitHub App webhook."""

import hashlib
import hmac
import os

from flask import Blueprint, abort, jsonify, redirect, request

from ..auth import requires_super_admin
from .. import db

global_admin_bp = Blueprint('global_admin', __name__)


# ─── Super Admin UI ──────────────────────────────────────────────────────────

@global_admin_bp.route('/admin')
@requires_super_admin
def admin_page():
    projects = db.load_projects()

    rows = ''
    for slug, p in projects.items():
        rows += f'''<tr class="border-t border-gray-100">
            <td class="px-4 py-3 text-sm font-mono">{slug}</td>
            <td class="px-4 py-3 text-sm font-semibold" style="color:{p.color}">{p.title}</td>
            <td class="px-4 py-3 text-sm text-gray-500">{p.repo_full_name}</td>
            <td class="px-4 py-3 text-sm text-gray-400">{p.owner_email}</td>
            <td class="px-4 py-3 flex gap-2">
                <a href="/{slug}/settings" class="text-xs text-indigo-600 hover:underline">Settings</a>
                <a href="/{slug}/" class="text-xs text-gray-500 hover:underline">View</a>
                <form method="post" action="/admin/projects/{slug}/delete" class="inline"
                      onsubmit="return confirm('Delete {slug}?')">
                    <button class="text-xs text-red-500 hover:underline">Delete</button>
                </form>
            </td>
        </tr>'''

    return f'''<!DOCTYPE html>
<html><head><title>Memento Admin</title><script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>body {{ font-family: 'Inter', system-ui, sans-serif; }}</style></head>
<body class="bg-gray-50 min-h-screen p-8">
<div class="max-w-4xl mx-auto">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-lg font-semibold text-gray-900">Memento — All Projects</h1>
        <a href="/" class="text-sm text-indigo-600 hover:underline">Back</a>
    </div>
    <div class="bg-white rounded-lg shadow-sm overflow-hidden">
        <table class="w-full">
            <thead class="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr><th class="px-4 py-2 text-left">Slug</th><th class="px-4 py-2 text-left">Title</th>
                <th class="px-4 py-2 text-left">Repo</th><th class="px-4 py-2 text-left">Owner</th>
                <th class="px-4 py-2 text-left">Actions</th></tr>
            </thead>
            <tbody>{rows if rows else '<tr><td colspan="5" class="px-4 py-6 text-sm text-gray-400 text-center">No projects</td></tr>'}</tbody>
        </table>
    </div>
</div></body></html>'''


@global_admin_bp.route('/admin/projects/<slug>/delete', methods=['POST'])
@requires_super_admin
def delete_project_route(slug):
    db.delete_project(slug)
    return redirect('/admin')


# ─── Webhook ─────────────────────────────────────────────────────────────────

@global_admin_bp.route('/api/webhook/github', methods=['POST'])
def webhook():
    """Handle GitHub App webhook events."""
    secret = os.getenv('GITHUB_APP_WEBHOOK_SECRET', '')
    if secret:
        signature = request.headers.get('X-Hub-Signature-256', '')
        expected = 'sha256=' + hmac.new(
            secret.encode(), request.data, hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            abort(403)

    event = request.headers.get('X-GitHub-Event', '')
    payload = request.get_json()

    if event == 'installation' and payload:
        action = payload.get('action')
        if action == 'created':
            # Log new installation, don't auto-create projects
            pass

    return jsonify({"ok": True})

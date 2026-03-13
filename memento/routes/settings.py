"""Per-project settings: user management + project config."""

from flask import Blueprint, g, redirect, request, session, url_for

from .. import db
from ..auth import requires_admin

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/settings')
@requires_admin
def settings_page():
    project = g.project
    config = g.config
    color = config.color
    users = db.list_members(project)
    is_owner = _is_owner()

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
                <form method="post" action="/{project}/settings/{u['email']}/role" class="flex gap-2 items-center">
                    <select name="role" class="text-xs border rounded px-2 py-1">{options}</select>
                    <button class="text-xs text-white px-2 py-1 rounded hover:opacity-90" style="background:{color}">Save</button>
                </form>
            </td>
        </tr>'''

    # Project settings form (owner/admin)
    settings_form = f'''
    <div class="bg-white rounded-lg shadow-sm p-4 mb-6">
        <h2 class="text-sm font-semibold text-gray-900 mb-3">Project settings</h2>
        <form method="post" action="/{project}/settings" class="space-y-3">
            <div class="grid grid-cols-2 gap-3">
                <div><label class="text-xs text-gray-500">Title</label>
                <input name="title" value="{config.title}" class="block text-sm border rounded px-3 py-1.5 w-full"></div>
                <div><label class="text-xs text-gray-500">Color</label>
                <input name="color" type="color" value="{config.color}" class="block h-8 w-16 border rounded"></div>
            </div>
            <div><label class="text-xs text-gray-500">Docs paths (comma-separated)</label>
            <input name="docs_paths" value="{','.join(config.docs_paths)}" class="block text-sm border rounded px-3 py-1.5 w-full"></div>
            <div><label class="text-xs text-gray-500">Allowed root files (comma-separated)</label>
            <input name="allowed_files" value="{','.join(config.allowed_files)}" class="block text-sm border rounded px-3 py-1.5 w-full"></div>
            <div><label class="text-xs text-gray-500">Allowed domains (comma-separated, auto-access)</label>
            <input name="allowed_domains" value="{','.join(config.allowed_domains)}" class="block text-sm border rounded px-3 py-1.5 w-full"></div>
            <button class="text-sm text-white px-4 py-1.5 rounded hover:opacity-90" style="background:{color}">Save settings</button>
        </form>
    </div>'''

    # Delete button (owner only)
    delete_btn = ''
    if is_owner:
        delete_btn = f'''
    <div class="bg-white rounded-lg shadow-sm p-4 border border-red-200">
        <h2 class="text-sm font-semibold text-red-600 mb-2">Danger zone</h2>
        <form method="post" action="/{project}/settings/delete"
              onsubmit="return confirm('Delete project {project}? This cannot be undone.')">
            <button class="text-xs text-white bg-red-500 px-3 py-1.5 rounded hover:bg-red-600">Delete project</button>
        </form>
    </div>'''

    return f'''<!DOCTYPE html>
<html><head><title>Settings - {config.title}</title><script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>body {{ font-family: 'Inter', system-ui, sans-serif; }}</style></head>
<body class="bg-gray-50 min-h-screen p-8">
<div class="max-w-3xl mx-auto">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-lg font-semibold text-gray-900">Settings</h1>
        <a href="/{project}/" class="text-sm hover:underline" style="color:{color}">Back to docs</a>
    </div>
    {settings_form}
    <div class="bg-white rounded-lg shadow-sm overflow-hidden mb-6">
        <h2 class="text-sm font-semibold text-gray-900 px-4 py-3">Members</h2>
        <table class="w-full">
            <thead class="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr><th class="px-4 py-2 text-left">Email</th><th class="px-4 py-2 text-left">Name</th>
                <th class="px-4 py-2 text-left">Role</th><th class="px-4 py-2 text-left">Action</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    <div class="bg-white rounded-lg shadow-sm p-4 mb-6">
        <h2 class="text-sm font-semibold text-gray-900 mb-3">Invite user</h2>
        <form method="post" action="/{project}/settings/invite" class="flex gap-2 items-end">
            <div><label class="text-xs text-gray-500">Email</label>
            <input name="email" type="email" required placeholder="user@example.com" class="block text-sm border rounded px-3 py-1.5 w-64"></div>
            <div><label class="text-xs text-gray-500">Name (optional)</label>
            <input name="name" type="text" placeholder="First Last" class="block text-sm border rounded px-3 py-1.5 w-48"></div>
            <button class="text-sm text-white px-4 py-1.5 rounded hover:opacity-90" style="background:{color}">Invite</button>
        </form>
    </div>
    {delete_btn}
</div></body></html>'''


@settings_bp.route('/settings', methods=['POST'])
@requires_admin
def update_settings():
    project = g.project
    title = request.form.get('title', '').strip()
    color = request.form.get('color', '').strip()
    docs_paths = [p.strip() for p in request.form.get('docs_paths', '').split(',') if p.strip()]
    allowed_files = [f.strip() for f in request.form.get('allowed_files', '').split(',') if f.strip()]
    allowed_domains = [d.strip() for d in request.form.get('allowed_domains', '').split(',') if d.strip()]

    db.update_project(project,
        title=title or g.config.title,
        color=color or g.config.color,
        docs_paths=docs_paths or ['docs'],
        allowed_files=allowed_files,
        allowed_domains=allowed_domains,
    )
    return redirect(url_for('settings.settings_page', project=project))


@settings_bp.route('/settings/delete', methods=['POST'])
@requires_admin
def delete_project():
    if not _is_owner():
        return "Only the project owner can delete", 403
    db.delete_project(g.project)
    return redirect('/')


@settings_bp.route('/settings/invite', methods=['POST'])
@requires_admin
def invite():
    email = request.form.get('email', '').strip().lower()
    name = request.form.get('name', '').strip()
    if email:
        db.invite_member(g.project, email, name)
        from ..email import send_invite_email
        invited_by = session.get('user', {}).get('email', 'an admin')
        send_invite_email(email, name, g.config.title, g.project, invited_by)
    return redirect(url_for('settings.settings_page', project=g.project))


@settings_bp.route('/settings/<path:email>/role', methods=['POST'])
@requires_admin
def set_role(email):
    role = request.form.get('role')
    db.set_member_role(g.project, email, role)
    return redirect(url_for('settings.settings_page', project=g.project))


def _is_owner() -> bool:
    user = session.get('user')
    if not user:
        return False
    return user['email'] == g.config.owner_email

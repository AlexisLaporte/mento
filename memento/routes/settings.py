"""Per-project settings: user management + project config (JSON APIs)."""

from flask import Blueprint, g, jsonify, request, session

from .. import db
from ..auth import requires_admin

settings_bp = Blueprint('settings', __name__)


def _is_owner() -> bool:
    user = session.get('user')
    if not user:
        return False
    return user['email'] == g.config.owner_email


@settings_bp.route('/api/settings')
@requires_admin
def api_get_settings():
    config = g.config
    members = db.list_members(g.project)
    return jsonify({
        "project": {
            "slug": config.slug,
            "title": config.title,
            "color": config.color,
            "repo_full_name": config.repo_full_name,
            "docs_paths": config.docs_paths,
            "allowed_files": config.allowed_files,
            "owner_email": config.owner_email,
            "custom_domain": config.custom_domain,
            "is_public": config.is_public,
        },
        "members": members,
        "is_owner": _is_owner(),
        "mcp_url": "https://mcp.mento.cc/mcp",
    })


@settings_bp.route('/api/settings', methods=['PUT'])
@requires_admin
def api_update_settings():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    db.update_project(g.project,
        title=data.get('title', g.config.title),
        color=data.get('color', g.config.color),
        docs_paths=data.get('docs_paths', g.config.docs_paths),
        allowed_files=data.get('allowed_files', g.config.allowed_files),
        custom_domain=data.get('custom_domain', g.config.custom_domain),
        is_public=data.get('is_public', g.config.is_public),
    )
    return jsonify({"ok": True})


@settings_bp.route('/api/settings', methods=['DELETE'])
@requires_admin
def api_delete_project():
    if not _is_owner():
        return jsonify({"error": "Only the project owner can delete"}), 403
    db.delete_project(g.project)
    return jsonify({"ok": True})


@settings_bp.route('/api/members/<path:email>/role', methods=['PUT'])
@requires_admin
def api_set_role(email):
    data = request.get_json()
    if not data or 'role' not in data:
        return jsonify({"error": "role required"}), 400
    ok = db.set_member_role(g.project, email, data['role'])
    if not ok:
        return jsonify({"error": "Invalid role"}), 400
    return jsonify({"ok": True})


@settings_bp.route('/api/members/invite', methods=['POST'])
@requires_admin
def api_invite():
    data = request.get_json()
    if not data or not data.get('email'):
        return jsonify({"error": "email required"}), 400
    email = data['email'].strip().lower()
    name = data.get('name', '').strip()
    db.invite_member(g.project, email, name)
    from ..email import send_invite_email
    invited_by = session.get('user', {}).get('email', 'an admin')
    send_invite_email(email, name, g.config.title, g.project, invited_by)
    return jsonify({"ok": True})

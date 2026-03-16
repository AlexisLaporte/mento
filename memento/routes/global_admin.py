"""Global admin — super admin oversight + GitHub App webhook."""

import hashlib
import hmac
import os

from flask import Blueprint, abort, jsonify, request

from ..auth import requires_super_admin
from .. import db, repo

global_admin_bp = Blueprint('global_admin', __name__)


# ─── Super Admin API ─────────────────────────────────────────────────────────

@global_admin_bp.route('/api/admin/projects')
@requires_super_admin
def api_admin_projects():
    projects = db.load_projects()
    return jsonify([{
        "slug": slug,
        "title": p.title,
        "color": p.color,
        "repo_full_name": p.repo_full_name,
        "owner_email": p.owner_email,
    } for slug, p in projects.items()])


@global_admin_bp.route('/api/admin/projects/<slug>', methods=['DELETE'])
@requires_super_admin
def api_admin_delete_project(slug):
    repo.delete_repo(slug)
    db.delete_project(slug)
    return jsonify({"ok": True})


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
            pass

    if event == 'push' and payload:
        repo_full_name = payload.get('repository', {}).get('full_name', '')
        if repo_full_name:
            from ..routes.docs import _cache
            for config in db.get_projects_by_repo(repo_full_name):
                repo.pull_repo(config.slug, config.installation_id)
                # Invalidate doc cache for this project
                expired = [k for k in _cache if k.startswith(f'tree:{config.slug}') or k.startswith(f'doc:{config.slug}:')]
                for k in expired:
                    del _cache[k]

    return jsonify({"ok": True})


@global_admin_bp.route('/api/webhook/marketplace', methods=['POST'])
def marketplace_webhook():
    """Handle GitHub Marketplace events (purchase, cancellation, plan change)."""
    import logging
    log = logging.getLogger(__name__)

    secret = os.getenv('GITHUB_MARKETPLACE_WEBHOOK_SECRET', '')
    if secret:
        signature = request.headers.get('X-Hub-Signature-256', '')
        expected = 'sha256=' + hmac.new(
            secret.encode(), request.data, hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            abort(403)

    payload = request.get_json()
    action = payload.get('action', '') if payload else ''
    log.info("Marketplace event: %s", action)

    return jsonify({"ok": True})

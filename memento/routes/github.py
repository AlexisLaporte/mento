"""GitHub issues viewer routes — uses GitHub App installation tokens."""

from flask import Blueprint, g, jsonify, request
from httpx import HTTPStatusError

from ..auth import requires_access
from ..github_app import github_api

github_bp = Blueprint('github', __name__)


def _github_get(path: str, params: dict | None = None) -> dict | list:
    """GitHub API GET using installation token."""
    return github_api(
        g.config.installation_id,
        f'/repos/{g.config.repo_full_name}/{path}',
        params,
    )


@github_bp.route('/api/issues')
@requires_access
def api_issues():
    """List issues with optional filters: state, labels, milestone."""
    if not g.config.repo_full_name:
        return jsonify({"error": "GitHub repo not configured"}), 400

    params = {
        "state": request.args.get("state", "open"),
        "per_page": request.args.get("per_page", "30"),
        "sort": request.args.get("sort", "updated"),
        "direction": "desc",
    }
    if request.args.get("labels"):
        params["labels"] = request.args["labels"]
    if request.args.get("milestone"):
        params["milestone"] = request.args["milestone"]

    try:
        issues = _github_get("issues", params)
    except HTTPStatusError as e:
        return jsonify({"error": f"GitHub API error: {e.response.status_code}"}), 502

    result = []
    for issue in issues:
        if issue.get("pull_request"):
            continue
        result.append({
            "number": issue["number"],
            "title": issue["title"],
            "state": issue["state"],
            "labels": [{"name": l["name"], "color": l["color"]} for l in issue.get("labels", [])],
            "assignee": issue["assignee"]["login"] if issue.get("assignee") else None,
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
            "comments": issue.get("comments", 0),
            "url": issue["html_url"],
            "milestone": issue["milestone"]["title"] if issue.get("milestone") else None,
        })

    return jsonify(result)


@github_bp.route('/api/labels')
@requires_access
def api_labels():
    if not g.config.repo_full_name:
        return jsonify([])
    try:
        labels = _github_get("labels", {"per_page": "100"})
        return jsonify([{"name": l["name"], "color": l["color"]} for l in labels])
    except HTTPStatusError:
        return jsonify([])


@github_bp.route('/api/milestones')
@requires_access
def api_milestones():
    if not g.config.repo_full_name:
        return jsonify([])
    try:
        milestones = _github_get("milestones", {"state": "open", "per_page": "20"})
        return jsonify([{"number": m["number"], "title": m["title"]} for m in milestones])
    except HTTPStatusError:
        return jsonify([])

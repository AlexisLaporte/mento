"""GitHub issues viewer routes."""

import os

import httpx
from flask import Blueprint, jsonify, request

from ..auth import requires_access

github_bp = Blueprint('github', __name__)

_repo = ""
_token_env = "GITHUB_TOKEN"


def init_github(config):
    global _repo, _token_env
    _repo = config.github.repo
    _token_env = config.github.token_env


def _github_get(path: str, params: dict | None = None) -> dict | list:
    """Make an authenticated GET request to GitHub API."""
    token = os.getenv(_token_env, "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = httpx.get(
        f"https://api.github.com/repos/{_repo}/{path}",
        headers=headers,
        params=params or {},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


@github_bp.route('/api/issues')
@requires_access
def api_issues():
    """List issues with optional filters: state, labels, milestone."""
    if not _repo:
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
    except httpx.HTTPStatusError as e:
        return jsonify({"error": f"GitHub API error: {e.response.status_code}"}), 502

    # Simplify response
    result = []
    for issue in issues:
        if issue.get("pull_request"):
            continue  # Skip PRs
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
    """List repo labels for filter UI."""
    if not _repo:
        return jsonify([])
    try:
        labels = _github_get("labels", {"per_page": "100"})
        return jsonify([{"name": l["name"], "color": l["color"]} for l in labels])
    except httpx.HTTPStatusError:
        return jsonify([])


@github_bp.route('/api/milestones')
@requires_access
def api_milestones():
    """List repo milestones for filter UI."""
    if not _repo:
        return jsonify([])
    try:
        milestones = _github_get("milestones", {"state": "open", "per_page": "20"})
        return jsonify([{"number": m["number"], "title": m["title"]} for m in milestones])
    except httpx.HTTPStatusError:
        return jsonify([])

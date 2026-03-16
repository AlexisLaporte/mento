"""MCP remote server — exposes Mento docs to claude.ai."""

import base64
import os

from dotenv import load_dotenv

load_dotenv()

from fastmcp import FastMCP

from .config import ProjectConfig
from .db import get_member, get_project, load_projects_for_user, member_exists
from . import repo as git_repo
from .github_app import github_api
from .mcp_auth import create_auth_provider, get_user_email
from .routes.docs import _build_tree, _is_allowed, _parse_frontmatter

mcp = FastMCP(
    name="Mento",
    instructions="Access documentation and GitHub issues for projects hosted on Mento.",
    auth=create_auth_provider(),
)

def _check_access(email: str, slug: str) -> ProjectConfig:
    """Verify user has access to project, return config."""
    config = get_project(slug)
    if not config:
        raise ValueError(f"Project '{slug}' not found")
    if not member_exists(slug, email):
        raise ValueError(f"Access denied to '{slug}'")
    if git_repo.repo_exists(slug):
        config.default_branch = git_repo.resolve_default_branch(slug)
    return config


def _check_write_access(email: str, slug: str) -> ProjectConfig:
    """Verify user has admin access to project (required for write operations)."""
    config = _check_access(email, slug)
    member = get_member(slug, email)
    is_admin = (member and member['role'] == 'admin') or config.owner_email == email
    if not is_admin:
        raise ValueError(f"Write access denied: admin role required on '{slug}'")
    return config


@mcp.tool
def list_projects() -> list[dict]:
    """List documentation projects the current user has access to."""
    email = get_user_email()
    projects = load_projects_for_user(email)
    return [
        {"slug": slug, "title": c.title, "repo": c.repo_full_name}
        for slug, c in projects.items()
    ]


@mcp.tool
def get_doc_tree(project_slug: str) -> list[dict]:
    """Get the documentation file tree for a project."""
    email = get_user_email()
    config = _check_access(email, project_slug)
    items = git_repo.list_files(project_slug)
    return _build_tree(items, config.docs_paths, config.allowed_files)


@mcp.tool
def read_doc(project_slug: str, path: str) -> dict:
    """Read a documentation file. Returns raw markdown content."""
    email = get_user_email()
    config = _check_access(email, project_slug)
    if not _is_allowed(path, config.docs_paths, config.allowed_files):
        raise ValueError(f"Path '{path}' is not accessible")
    raw = git_repo.read_file(project_slug, path)
    content = raw.decode('utf-8', errors='replace')
    fm, body = _parse_frontmatter(content)
    return {"path": path, "frontmatter": fm, "content": body}


@mcp.tool
def list_issues(
    project_slug: str, state: str = "open", labels: str = "",
) -> list[dict]:
    """List GitHub issues for a project. Filter by state (open/closed) and labels."""
    email = get_user_email()
    config = _check_access(email, project_slug)
    params = {"state": state, "per_page": "30", "sort": "updated", "direction": "desc"}
    if labels:
        params["labels"] = labels
    issues = github_api(
        config.installation_id,
        f'/repos/{config.repo_full_name}/issues',
        params,
    )
    return [
        {
            "number": i["number"], "title": i["title"], "state": i["state"],
            "labels": [l["name"] for l in i.get("labels", [])],
            "assignee": i["assignee"]["login"] if i.get("assignee") else None,
            "created_at": i["created_at"], "url": i["html_url"],
        }
        for i in issues if not i.get("pull_request")
    ]


@mcp.tool
def create_doc(
    project_slug: str,
    path: str,
    content: str,
    message: str = "",
    branch: str = "",
) -> dict:
    """Create a new documentation file in the repository.

    Args:
        project_slug: Project identifier.
        path: File path in the repo (e.g. "docs/guide.md").
        content: File content (plain text / markdown).
        message: Commit message. Defaults to "Create <path>".
        branch: Target branch. Defaults to the repo's default branch.

    Returns:
        Dict with path, sha, and commit info.
    """
    email = get_user_email()
    config = _check_write_access(email, project_slug)
    if not _is_allowed(path, config.docs_paths, config.allowed_files):
        raise ValueError(f"Path '{path}' is not within allowed docs paths")
    target_branch = branch or config.default_branch
    commit_message = message or f"Create {path}"

    encoded = base64.b64encode(content.encode('utf-8')).decode('ascii')
    result = github_api(
        config.installation_id,
        f'/repos/{config.repo_full_name}/contents/{path}',
        method='PUT',
        json_body={
            'message': commit_message,
            'content': encoded,
            'branch': target_branch,
        },
    )
    return {
        "path": path,
        "sha": result['content']['sha'],
        "commit_sha": result['commit']['sha'],
        "commit_message": commit_message,
        "branch": target_branch,
    }


@mcp.tool
def update_doc(
    project_slug: str,
    path: str,
    content: str,
    message: str = "",
    branch: str = "",
) -> dict:
    """Update an existing documentation file in the repository.

    Automatically fetches the current file SHA required by GitHub.

    Args:
        project_slug: Project identifier.
        path: File path in the repo (e.g. "docs/guide.md").
        content: New file content (plain text / markdown).
        message: Commit message. Defaults to "Update <path>".
        branch: Target branch. Defaults to the repo's default branch.

    Returns:
        Dict with path, sha, and commit info.
    """
    email = get_user_email()
    config = _check_write_access(email, project_slug)
    if not _is_allowed(path, config.docs_paths, config.allowed_files):
        raise ValueError(f"Path '{path}' is not within allowed docs paths")
    target_branch = branch or config.default_branch
    commit_message = message or f"Update {path}"

    # Fetch current file to get its SHA (required for update)
    existing = github_api(
        config.installation_id,
        f'/repos/{config.repo_full_name}/contents/{path}',
    )
    current_sha = existing['sha']

    encoded = base64.b64encode(content.encode('utf-8')).decode('ascii')
    result = github_api(
        config.installation_id,
        f'/repos/{config.repo_full_name}/contents/{path}',
        method='PUT',
        json_body={
            'message': commit_message,
            'content': encoded,
            'sha': current_sha,
            'branch': target_branch,
        },
    )
    return {
        "path": path,
        "sha": result['content']['sha'],
        "previous_sha": current_sha,
        "commit_sha": result['commit']['sha'],
        "commit_message": commit_message,
        "branch": target_branch,
    }


# ASGI app for uvicorn
app = mcp.http_app()


def main():
    port = int(os.getenv('MCP_PORT', '5003'))
    mcp.run(transport="http", host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()

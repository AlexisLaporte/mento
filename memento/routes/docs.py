"""Documentation file tree and markdown viewer — reads from GitHub Contents API."""

import base64

import markdown
import yaml
from flask import Blueprint, g, jsonify, render_template
from httpx import HTTPStatusError

from ..auth import requires_access
from ..github_app import github_api

docs_bp = Blueprint('docs', __name__)

_md = markdown.Markdown(extensions=[
    'tables',
    'fenced_code',
    'codehilite',
    'toc',
    'pymdownx.tasklist',
    'pymdownx.magiclink',
], extension_configs={
    'codehilite': {'css_class': 'highlight', 'guess_lang': False},
})


# ─── Route: project index ────────────────────────────────────────────────────

@docs_bp.route('/')
@docs_bp.route('/<path:doc_path>')
@requires_access
def index(doc_path=None):
    return render_template('index.html', config=g.config, project_slug=g.project)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _is_allowed(path: str, docs_paths: list[str], allowed_files: list[str]) -> bool:
    """Check if a path is under docs_paths or is an allowed root file."""
    parts = path.split('/')
    if not parts:
        return False
    if parts[0] in docs_paths:
        return True
    if len(parts) == 1 and parts[0] in allowed_files:
        return True
    return False


def _build_tree(items: list[dict], docs_paths: list[str], allowed_files: list[str]) -> list[dict]:
    """Build a nested tree from GitHub git/trees flat list."""
    # Filter to allowed paths and markdown files (+ directories)
    filtered = []
    for item in items:
        if not _is_allowed(item['path'], docs_paths, allowed_files):
            continue
        if item['type'] == 'blob':
            if item['path'].lower().endswith(('.md', '.markdown')):
                filtered.append(item)
        elif item['type'] == 'tree':
            filtered.append(item)

    # Build nested structure
    root: list[dict] = []
    dirs: dict[str, dict] = {}

    # First pass: create all directory nodes
    for item in filtered:
        if item['type'] == 'tree':
            name = item['path'].split('/')[-1]
            node = {"name": name, "path": item['path'], "type": "dir", "children": []}
            dirs[item['path']] = node

    # Second pass: add files and wire up children
    for item in filtered:
        name = item['path'].split('/')[-1]
        if item['type'] == 'blob':
            file_node = {"name": name, "path": item['path'], "type": "file"}
            parent_path = '/'.join(item['path'].split('/')[:-1])
            if parent_path in dirs:
                dirs[parent_path]['children'].append(file_node)
            else:
                root.append(file_node)
        elif item['type'] == 'tree':
            parent_path = '/'.join(item['path'].split('/')[:-1])
            if parent_path in dirs:
                dirs[parent_path]['children'].append(dirs[item['path']])
            else:
                root.append(dirs[item['path']])

    # Remove empty directories
    def prune(nodes: list[dict]) -> list[dict]:
        result = []
        for node in nodes:
            if node['type'] == 'dir':
                node['children'] = prune(node['children'])
                if node['children']:
                    result.append(node)
            else:
                result.append(node)
        return result

    # Sort: dirs first, then alpha
    def sort_tree(nodes: list[dict]) -> list[dict]:
        nodes.sort(key=lambda n: (n['type'] != 'dir', n['name'].lower()))
        for n in nodes:
            if n['type'] == 'dir':
                sort_tree(n['children'])
        return nodes

    return sort_tree(prune(root))


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from markdown text."""
    if not text.startswith('---'):
        return {}, text
    end = text.find('---', 3)
    if end == -1:
        return {}, text
    try:
        fm = yaml.safe_load(text[3:end]) or {}
    except Exception:
        fm = {}
    body = text[end + 3:].lstrip('\n')
    return fm, body


def _render_markdown(text: str) -> str:
    _md.reset()
    return _md.convert(text)


# ─── API Routes ──────────────────────────────────────────────────────────────

@docs_bp.route('/api/tree')
@requires_access
def api_tree():
    config = g.config
    if not config.repo_full_name or not config.installation_id:
        return jsonify([])

    try:
        tree_data = github_api(
            config.installation_id,
            f'/repos/{config.repo_full_name}/git/trees/{config.default_branch}',
            params={'recursive': '1'},
        )
    except HTTPStatusError as e:
        return jsonify({"error": f"GitHub API error: {e.response.status_code}"}), 502

    nodes = _build_tree(tree_data.get('tree', []), config.docs_paths, config.allowed_files)
    return jsonify(nodes)


@docs_bp.route('/api/doc/<path:doc_path>')
@requires_access
def api_doc(doc_path: str):
    config = g.config

    if not config.repo_full_name or not config.installation_id:
        return jsonify({"error": "Repo not configured"}), 400

    if not _is_allowed(doc_path, config.docs_paths, config.allowed_files):
        return jsonify({"error": "Not found"}), 404

    try:
        data = github_api(
            config.installation_id,
            f'/repos/{config.repo_full_name}/contents/{doc_path}',
        )
    except HTTPStatusError as e:
        if e.response.status_code == 404:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"error": f"GitHub API error: {e.response.status_code}"}), 502

    content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
    fm, body = _parse_frontmatter(content)
    html = _render_markdown(body)

    return jsonify({"path": doc_path, "frontmatter": fm, "html": html})

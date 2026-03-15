"""Documentation file tree and markdown viewer — reads from GitHub Contents API."""

import base64
import re

import markdown
import yaml
from flask import Blueprint, g, jsonify, request
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
    'toc': {'toc_depth': '2-4'},
})

# Supported file extensions beyond markdown
_SUPPORTED_EXTENSIONS = (
    '.md', '.markdown',
    '.txt', '.text', '.csv', '.json', '.yaml', '.yml', '.toml', '.xml',
    '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.rb', '.sh', '.bash',
    '.html', '.css', '.sql', '.dockerfile', '.makefile',
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp',
    '.pdf',
)

_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp')
_TEXT_EXTENSIONS = (
    '.txt', '.text', '.csv', '.json', '.yaml', '.yml', '.toml', '.xml',
    '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.rb', '.sh', '.bash',
    '.html', '.css', '.sql', '.dockerfile', '.makefile',
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _is_allowed(path: str, docs_paths: list[str], allowed_files: list[str]) -> bool:
    """Check if a path is under docs_paths or is an allowed root file."""
    if '/' in docs_paths:
        return True
    parts = path.split('/')
    if not parts:
        return False
    if parts[0] in docs_paths:
        return True
    if len(parts) == 1 and parts[0] in allowed_files:
        return True
    return False


def _file_kind(path: str) -> str:
    """Return the kind of file: 'markdown', 'image', 'text', 'pdf', or 'unknown'."""
    lower = path.lower()
    if lower.endswith(('.md', '.markdown')):
        return 'markdown'
    if lower.endswith(_IMAGE_EXTENSIONS):
        return 'image'
    if lower.endswith('.pdf'):
        return 'pdf'
    if lower.endswith(_TEXT_EXTENSIONS):
        return 'text'
    return 'unknown'


def _build_tree(items: list[dict], docs_paths: list[str], allowed_files: list[str]) -> list[dict]:
    """Build a nested tree from GitHub git/trees flat list."""
    filtered = []
    for item in items:
        if not _is_allowed(item['path'], docs_paths, allowed_files):
            continue
        if item['type'] == 'blob':
            if item['path'].lower().endswith(_SUPPORTED_EXTENSIONS):
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
            kind = _file_kind(item['path'])
            file_node = {"name": name, "path": item['path'], "type": "file", "kind": kind}
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


def _flatten_tree(nodes: list[dict]) -> list[dict]:
    """Flatten a nested tree into a list of file nodes (in display order)."""
    result = []
    for node in nodes:
        if node['type'] == 'file':
            result.append(node)
        elif node['type'] == 'dir' and node.get('children'):
            result.extend(_flatten_tree(node['children']))
    return result


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


def _render_markdown(text: str) -> tuple[str, str]:
    """Render markdown to HTML and return (html, toc_html)."""
    _md.reset()
    html = _md.convert(text)
    toc = getattr(_md, 'toc', '')
    return html, toc


def _extract_headings(html: str) -> list[dict]:
    """Extract headings from rendered HTML for TOC."""
    pattern = re.compile(r'<h([2-4])\s*(?:id="([^"]*)")?\s*[^>]*>(.*?)</h\1>', re.IGNORECASE | re.DOTALL)
    headings = []
    for match in pattern.finditer(html):
        level = int(match.group(1))
        heading_id = match.group(2) or ''
        text = re.sub(r'<[^>]+>', '', match.group(3)).strip()
        headings.append({'level': level, 'id': heading_id, 'text': text})
    return headings


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

    kind = _file_kind(doc_path)

    try:
        data = github_api(
            config.installation_id,
            f'/repos/{config.repo_full_name}/contents/{doc_path}',
        )
    except HTTPStatusError as e:
        if e.response.status_code == 404:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"error": f"GitHub API error: {e.response.status_code}"}), 502

    if kind == 'image':
        # Return download URL for images
        return jsonify({
            "path": doc_path,
            "kind": "image",
            "download_url": data.get('download_url', ''),
            "size": data.get('size', 0),
        })

    if kind == 'pdf':
        return jsonify({
            "path": doc_path,
            "kind": "pdf",
            "download_url": data.get('download_url', ''),
            "size": data.get('size', 0),
        })

    # Text-based content (markdown or plain text)
    raw = base64.b64decode(data['content'])
    content = raw.decode('utf-8', errors='replace')

    if kind == 'markdown':
        fm, body = _parse_frontmatter(content)
        html, toc_html = _render_markdown(body)
        headings = _extract_headings(html)
        return jsonify({
            "path": doc_path,
            "kind": "markdown",
            "frontmatter": fm,
            "html": html,
            "toc": headings,
        })

    # Plain text / code files
    return jsonify({
        "path": doc_path,
        "kind": "text",
        "content": content,
        "size": len(raw),
    })


@docs_bp.route('/api/search')
@requires_access
def api_search():
    """Search doc filenames and content in the repo."""
    config = g.config
    q = request.args.get('q', '').strip()
    if not q or not config.repo_full_name or not config.installation_id:
        return jsonify([])

    # Get tree for filename search
    try:
        tree_data = github_api(
            config.installation_id,
            f'/repos/{config.repo_full_name}/git/trees/{config.default_branch}',
            params={'recursive': '1'},
        )
    except HTTPStatusError:
        return jsonify([])

    q_lower = q.lower()
    results = []

    for item in tree_data.get('tree', []):
        if item['type'] != 'blob':
            continue
        if not _is_allowed(item['path'], config.docs_paths, config.allowed_files):
            continue
        if not item['path'].lower().endswith(_SUPPORTED_EXTENSIONS):
            continue
        name = item['path'].split('/')[-1]
        if q_lower in name.lower() or q_lower in item['path'].lower():
            results.append({
                'path': item['path'],
                'name': name,
                'kind': _file_kind(item['path']),
            })

    # Limit results
    return jsonify(results[:20])

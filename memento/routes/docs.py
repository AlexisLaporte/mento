"""Documentation file tree and markdown viewer — reads from GitHub Contents API."""

import base64
import re
import time

import markdown
import nh3
import yaml
from flask import Blueprint, Response, g, jsonify, request
from httpx import HTTPStatusError

import httpx

from ..auth import requires_access
from ..github_app import get_installation_token, github_api


# ─── TTL Cache ────────────────────────────────────────────────────────────────

_cache: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 60  # seconds


def _cache_get(key: str) -> object | None:
    entry = _cache.get(key)
    if entry and entry[0] > time.monotonic():
        return entry[1]
    _cache.pop(key, None)
    return None


def _cache_set(key: str, value: object) -> None:
    _cache[key] = (time.monotonic() + _CACHE_TTL, value)
    # Evict old entries if cache grows too large
    if len(_cache) > 500:
        now = time.monotonic()
        expired = [k for k, (t, _) in _cache.items() if t <= now]
        for k in expired:
            del _cache[k]

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
    """Render markdown to HTML, sanitize, and return (html, toc_html)."""
    _md.reset()
    raw_html = _md.convert(text)
    html = nh3.clean(
        raw_html,
        tags=nh3.ALLOWED_TAGS | {
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'p', 'pre', 'code', 'blockquote', 'hr', 'br',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'ul', 'ol', 'li', 'dl', 'dt', 'dd',
            'img', 'div', 'span', 'details', 'summary',
            'input', 'del', 'ins', 'sup', 'sub',
        },
        attributes={
            '*': {'id', 'class', 'style'},
            'a': {'href', 'title', 'target'},
            'img': {'src', 'alt', 'title', 'width', 'height'},
            'input': {'type', 'checked', 'disabled'},
            'td': {'colspan', 'rowspan', 'align'},
            'th': {'colspan', 'rowspan', 'align'},
            'code': {'class'},
        },
    )
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

    cache_key = f'tree:{config.slug}'
    cached = _cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    try:
        tree_data = github_api(
            config.installation_id,
            f'/repos/{config.repo_full_name}/git/trees/{config.default_branch}',
            params={'recursive': '1'},
        )
    except HTTPStatusError as e:
        return jsonify({"error": f"GitHub API error: {e.response.status_code}"}), 502

    nodes = _build_tree(tree_data.get('tree', []), config.docs_paths, config.allowed_files)
    _cache_set(cache_key, nodes)
    return jsonify(nodes)


@docs_bp.route('/api/doc/<path:doc_path>')
@requires_access
def api_doc(doc_path: str):
    config = g.config

    if not config.repo_full_name or not config.installation_id:
        return jsonify({"error": "Repo not configured"}), 400

    if not _is_allowed(doc_path, config.docs_paths, config.allowed_files):
        return jsonify({"error": "Not found"}), 404

    cache_key = f'doc:{config.slug}:{doc_path}'
    cached = _cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

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

    if kind in ('image', 'pdf'):
        slug = config.slug
        result = {
            "path": doc_path,
            "kind": kind,
            "download_url": f'/{slug}/api/raw/{doc_path}',
            "size": data.get('size', 0),
        }
        _cache_set(cache_key, result)
        return jsonify(result)

    # Text-based content (markdown or plain text)
    raw = base64.b64decode(data['content'])
    content = raw.decode('utf-8', errors='replace')

    if kind == 'markdown':
        fm, body = _parse_frontmatter(content)
        html, toc_html = _render_markdown(body)
        headings = _extract_headings(html)
        result = {
            "path": doc_path,
            "kind": "markdown",
            "frontmatter": fm,
            "html": html,
            "toc": headings,
        }
        _cache_set(cache_key, result)
        return jsonify(result)

    # Plain text / code files
    result = {
        "path": doc_path,
        "kind": "text",
        "content": content,
        "size": len(raw),
    }
    _cache_set(cache_key, result)
    return jsonify(result)


_CONTENT_TYPES = {
    '.pdf': 'application/pdf',
    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.gif': 'image/gif', '.svg': 'image/svg+xml', '.webp': 'image/webp',
    '.ico': 'image/x-icon', '.bmp': 'image/bmp',
}


@docs_bp.route('/api/raw/<path:doc_path>')
@requires_access
def api_raw(doc_path: str):
    """Proxy binary files (PDF, images) from GitHub with correct Content-Type."""
    config = g.config
    if not config.repo_full_name or not config.installation_id:
        return jsonify({"error": "Repo not configured"}), 400
    if not _is_allowed(doc_path, config.docs_paths, config.allowed_files):
        return jsonify({"error": "Not found"}), 404

    ext = '.' + doc_path.rsplit('.', 1)[-1].lower() if '.' in doc_path else ''
    content_type = _CONTENT_TYPES.get(ext, 'application/octet-stream')

    try:
        data = github_api(
            config.installation_id,
            f'/repos/{config.repo_full_name}/contents/{doc_path}',
        )
    except HTTPStatusError as e:
        if e.response.status_code == 404:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"error": f"GitHub API error: {e.response.status_code}"}), 502

    if data.get('content'):
        raw = base64.b64decode(data['content'])
    elif data.get('download_url'):
        # Large files (>1MB): GitHub Contents API omits base64 content
        token = get_installation_token(config.installation_id)
        resp = httpx.get(data['download_url'], headers={'Authorization': f'Bearer {token}'}, follow_redirects=True)
        resp.raise_for_status()
        raw = resp.content
    else:
        return jsonify({"error": "File content unavailable"}), 502

    return Response(raw, content_type=content_type, headers={
        'Content-Disposition': 'inline',
        'Cache-Control': 'private, max-age=300',
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

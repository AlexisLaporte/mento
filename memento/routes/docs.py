"""Documentation file tree and markdown viewer — reads from local git clone."""

import re
import time

import markdown
import nh3
import yaml
from flask import Blueprint, Response, g, jsonify, request

from ..auth import requires_access
from .. import repo as git_repo


# ─── TTL Cache ────────────────────────────────────────────────────────────────

_cache: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 30  # seconds (filesystem is fast, short TTL to avoid os.walk spam)


def _cache_get(key: str) -> object | None:
    entry = _cache.get(key)
    if entry and entry[0] > time.monotonic():
        return entry[1]
    _cache.pop(key, None)
    return None


def _cache_set(key: str, value: object) -> None:
    _cache[key] = (time.monotonic() + _CACHE_TTL, value)
    if len(_cache) > 500:
        now = time.monotonic()
        for k in [k for k, (t, _) in _cache.items() if t <= now]:
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

_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp')
_TEXT_EXTENSIONS = (
    '.txt', '.text', '.csv', '.json', '.yaml', '.yml', '.toml', '.xml',
    '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.rb', '.sh', '.bash',
    '.html', '.css', '.sql', '.dockerfile', '.makefile',
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _is_allowed(path: str, docs_paths: list[str], allowed_files: list[str]) -> bool:
    """Check if a path is under docs_paths or is an allowed root file."""
    # Normalize path and prevent directory traversal
    path = path.replace('\\', '/')
    if '..' in path.split('/'):
        return False

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
    lower = path.lower()
    if lower.endswith(('.md', '.markdown')):
        return 'markdown'
    if lower.endswith(_IMAGE_EXTENSIONS):
        return 'image'
    if lower.endswith('.pdf'):
        return 'pdf'
    if lower.endswith(('.docx',)):
        return 'docx'
    if lower.endswith(_TEXT_EXTENSIONS):
        return 'text'
    return 'binary'


def _build_tree(items: list[dict], docs_paths: list[str], allowed_files: list[str]) -> list[dict]:
    """Build a nested tree from flat file list."""
    filtered = []
    for item in items:
        if not _is_allowed(item['path'], docs_paths, allowed_files):
            continue
        filtered.append(item)

    root: list[dict] = []
    dirs: dict[str, dict] = {}

    for item in filtered:
        if item['type'] == 'tree':
            name = item['path'].split('/')[-1]
            node = {"name": name, "path": item['path'], "type": "dir", "children": []}
            dirs[item['path']] = node

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

    def sort_tree(nodes: list[dict]) -> list[dict]:
        nodes.sort(key=lambda n: (n['type'] != 'dir', n['name'].lower()))
        for n in nodes:
            if n['type'] == 'dir':
                sort_tree(n['children'])
        return nodes

    return sort_tree(prune(root))


def _flatten_tree(nodes: list[dict]) -> list[dict]:
    result = []
    for node in nodes:
        if node['type'] == 'file':
            result.append(node)
        elif node['type'] == 'dir' and node.get('children'):
            result.extend(_flatten_tree(node['children']))
    return result


def _parse_frontmatter(text: str) -> tuple[dict, str]:
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
    if not config.repo_full_name:
        return jsonify([])

    cache_key = f'tree:{config.slug}'
    cached = _cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    if not git_repo.repo_exists(config.slug):
        return jsonify({"error": "Repository not synced yet"}), 503

    items = git_repo.list_files(config.slug)
    nodes = _build_tree(items, config.docs_paths, config.allowed_files)
    _cache_set(cache_key, nodes)
    return jsonify(nodes)


@docs_bp.route('/api/doc/<path:doc_path>')
@requires_access
def api_doc(doc_path: str):
    config = g.config
    if not config.repo_full_name:
        return jsonify({"error": "Repo not configured"}), 400

    if not _is_allowed(doc_path, config.docs_paths, config.allowed_files):
        return jsonify({"error": "Not found"}), 404

    cache_key = f'doc:{config.slug}:{doc_path}'
    cached = _cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    kind = _file_kind(doc_path)

    try:
        raw = git_repo.read_file(config.slug, doc_path)
    except FileNotFoundError:
        return jsonify({"error": "Not found"}), 404

    if kind in ('image', 'pdf', 'docx', 'binary'):
        result = {
            "path": doc_path,
            "kind": kind,
            "download_url": f'/{config.slug}/api/raw/{doc_path}',
            "size": len(raw),
        }
        _cache_set(cache_key, result)
        return jsonify(result)

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
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}


@docs_bp.route('/api/raw/<path:doc_path>')
@requires_access
def api_raw(doc_path: str):
    """Serve binary files (PDF, images) from local clone."""
    config = g.config
    if not config.repo_full_name:
        return jsonify({"error": "Repo not configured"}), 400
    if not _is_allowed(doc_path, config.docs_paths, config.allowed_files):
        return jsonify({"error": "Not found"}), 404

    ext = '.' + doc_path.rsplit('.', 1)[-1].lower() if '.' in doc_path else ''
    content_type = _CONTENT_TYPES.get(ext, 'application/octet-stream')

    try:
        raw = git_repo.read_file(config.slug, doc_path)
    except FileNotFoundError:
        return jsonify({"error": "Not found"}), 404

    return Response(raw, content_type=content_type, headers={
        'Content-Disposition': 'inline',
        'Cache-Control': 'private, max-age=300',
    })


@docs_bp.route('/api/search')
@requires_access
def api_search():
    """Search doc filenames in the repo."""
    config = g.config
    q = request.args.get('q', '').strip()
    if not q or not config.repo_full_name:
        return jsonify([])

    if not git_repo.repo_exists(config.slug):
        return jsonify([])

    items = git_repo.list_files(config.slug)
    q_lower = q.lower()
    results = []

    for item in items:
        if item['type'] != 'blob':
            continue
        if not _is_allowed(item['path'], config.docs_paths, config.allowed_files):
            continue
        name = item['path'].split('/')[-1]
        if q_lower in name.lower() or q_lower in item['path'].lower():
            results.append({
                'path': item['path'],
                'name': name,
                'kind': _file_kind(item['path']),
            })

    return jsonify(results[:20])

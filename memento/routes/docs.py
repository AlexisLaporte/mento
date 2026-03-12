"""Documentation file tree and markdown viewer routes."""

import re
from pathlib import Path

import markdown
from flask import Blueprint, jsonify

from ..auth import requires_access

docs_bp = Blueprint('docs', __name__)

# Set at register time from config
_base_path: Path = Path('.')
_docs_paths: list[str] = ['docs']
_allowed_files: list[str] = []

# Markdown renderer with extensions
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


def init_docs(config):
    global _base_path, _docs_paths, _allowed_files
    _base_path = Path(config.base_path).resolve()
    _docs_paths = config.docs_paths
    _allowed_files = config.allowed_files


def _safe_path(relative: str) -> Path | None:
    """Resolve a relative path under base, return None if traversal detected."""
    target = (_base_path / relative).resolve()
    if not str(target).startswith(str(_base_path)):
        return None
    rel = target.relative_to(_base_path)
    parts = rel.parts
    if not parts:
        return None
    root = parts[0]
    # Allow docs_paths directories and allowed_files at root
    if root in _docs_paths:
        return target
    if len(parts) == 1 and root in _allowed_files:
        return target
    return None


def _build_tree() -> list[dict]:
    """Build a JSON-serializable file tree for configured paths."""
    tree = []
    # Add docs directories
    for root_name in sorted(_docs_paths):
        root_path = _base_path / root_name
        if not root_path.is_dir():
            continue
        node = _dir_node(root_path)
        if node:
            tree.append(node)
    # Add allowed root files
    for filename in sorted(_allowed_files):
        fp = _base_path / filename
        if fp.is_file():
            tree.append({
                "name": filename,
                "path": filename,
                "type": "file",
            })
    return tree


def _dir_node(dir_path: Path) -> dict | None:
    """Recursively build a directory node."""
    children = []
    try:
        for entry in sorted(dir_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            if entry.name.startswith('.'):
                continue
            if entry.is_dir():
                child = _dir_node(entry)
                if child:
                    children.append(child)
            elif entry.suffix.lower() in ('.md', '.markdown'):
                children.append({
                    "name": entry.name,
                    "path": str(entry.relative_to(_base_path)),
                    "type": "file",
                })
    except PermissionError:
        return None
    if not children:
        return None
    return {
        "name": dir_path.name,
        "path": str(dir_path.relative_to(_base_path)),
        "type": "dir",
        "children": children,
    }


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from markdown text."""
    if not text.startswith('---'):
        return {}, text
    end = text.find('---', 3)
    if end == -1:
        return {}, text
    import yaml
    try:
        fm = yaml.safe_load(text[3:end]) or {}
    except Exception:
        fm = {}
    body = text[end + 3:].lstrip('\n')
    return fm, body


def _render_markdown(text: str) -> str:
    """Render markdown to HTML."""
    _md.reset()
    return _md.convert(text)


# ─── API Routes ───────────────────────────────────────────────────────────────

@docs_bp.route('/api/tree')
@requires_access
def api_tree():
    return jsonify(_build_tree())


@docs_bp.route('/api/doc/<path:doc_path>')
@requires_access
def api_doc(doc_path: str):
    target = _safe_path(doc_path)
    if not target or not target.is_file():
        return jsonify({"error": "Not found"}), 404

    text = target.read_text(errors='replace')
    fm, body = _parse_frontmatter(text)
    html = _render_markdown(body)

    return jsonify({
        "path": doc_path,
        "frontmatter": fm,
        "html": html,
    })

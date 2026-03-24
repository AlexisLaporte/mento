"""Local git clone management — clone, pull, and serve repo files from disk."""

import logging
import os
import shutil
import subprocess

from .github_app import get_installation_token

log = logging.getLogger(__name__)

REPOS_DIR = os.getenv('MEMENTO_REPOS_DIR', '/opt/memento/repos')


def repo_path(slug: str) -> str:
    return os.path.join(REPOS_DIR, slug)


def repo_exists(slug: str) -> bool:
    return os.path.isdir(os.path.join(repo_path(slug), '.git'))


def clone_repo(slug: str, repo_full_name: str, installation_id: int, branch: str = 'main') -> None:
    """Shallow clone a repo. Raises RuntimeError on failure."""
    token = get_installation_token(installation_id)
    dest = repo_path(slug)
    os.makedirs(REPOS_DIR, exist_ok=True)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    repo_url = f'https://github.com/{repo_full_name}.git'
    result = subprocess.run(
        ['git', '-c', f'url.https://x-access-token:{token}@github.com/.insteadOf=https://github.com/',
         'clone', '--depth', '1', '--single-branch', '--branch', branch,
         repo_url, dest],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f'git clone failed: {result.stderr.strip()}')
    log.info('Cloned %s → %s', repo_full_name, dest)


def pull_repo(slug: str, installation_id: int) -> None:
    """Pull latest changes. Silent on failure (repo may already be up to date)."""
    path = repo_path(slug)
    if not os.path.isdir(path):
        return
    token = get_installation_token(installation_id)
    result = subprocess.run(
        ['git', '-C', path,
         '-c', f'url.https://x-access-token:{token}@github.com/.insteadOf=https://github.com/',
         'pull', '--ff-only'],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode == 0:
        log.info('Pulled %s', slug)
    else:
        log.warning('Pull failed for %s: %s', slug, result.stderr.strip())


def delete_repo(slug: str) -> None:
    path = repo_path(slug)
    if os.path.exists(path):
        shutil.rmtree(path)
        log.info('Deleted repo %s', slug)


def list_files(slug: str) -> list[dict]:
    """Walk repo directory, return flat list matching GitHub git/trees format."""
    root = repo_path(slug)
    items: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip .git
        dirnames[:] = [d for d in dirnames if d != '.git']
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir != '.':
            items.append({'path': rel_dir, 'type': 'tree'})
        for fname in filenames:
            rel_path = fname if rel_dir == '.' else f'{rel_dir}/{fname}'
            items.append({'path': rel_path, 'type': 'blob'})
    return items


def read_file(slug: str, path: str) -> bytes:
    """Read raw bytes from repo. Raises FileNotFoundError if missing."""
    base = os.path.realpath(repo_path(slug))
    full = os.path.realpath(os.path.join(base, path))

    # Prevent path traversal (including sibling directory attacks)
    if os.path.commonpath([base, full]) != base:
        raise FileNotFoundError(f'Invalid path: {path}')

    with open(full, 'rb') as f:
        return f.read()


def resolve_default_branch(slug: str) -> str:
    path = repo_path(slug)
    if not os.path.isdir(path):
        return 'main'
    result = subprocess.run(
        ['git', '-C', path, 'symbolic-ref', '--short', 'HEAD'],
        capture_output=True, text=True, timeout=5,
    )
    return result.stdout.strip() or 'main'


def sync_all_projects() -> None:
    """Clone all projects that don't have a local clone yet."""
    from .db import load_projects
    projects = load_projects()
    for slug, config in projects.items():
        if repo_exists(slug):
            log.info('Already cloned: %s', slug)
            continue
        if not config.repo_full_name or not config.installation_id:
            log.warning('Skipping %s: no repo configured', slug)
            continue
        try:
            clone_repo(slug, config.repo_full_name, config.installation_id, config.default_branch or 'main')
        except Exception as e:
            log.error('Failed to clone %s: %s', slug, e)


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1 and sys.argv[1] == 'sync':
        sync_all_projects()
    else:
        print('Usage: python -m memento.repo sync')

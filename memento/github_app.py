"""GitHub App authentication — JWT signing and installation token management."""

import os
import time

import httpx
import jwt

_private_key = None
_installation_tokens: dict[int, tuple[str, float]] = {}


def _get_private_key() -> str:
    global _private_key
    if not _private_key:
        path = os.getenv('GITHUB_APP_PRIVATE_KEY_PATH', '')
        if not path:
            raise RuntimeError('GITHUB_APP_PRIVATE_KEY_PATH not set')
        with open(path) as f:
            _private_key = f.read()
    return _private_key


def get_app_jwt() -> str:
    """JWT signed with the App's private key (10 min TTL)."""
    now = int(time.time())
    payload = {'iat': now - 60, 'exp': now + 600, 'iss': os.getenv('GITHUB_APP_ID')}
    return jwt.encode(payload, _get_private_key(), algorithm='RS256')


def get_installation_token(installation_id: int) -> str:
    """Installation access token (cached 50 min, valid 1h)."""
    cached = _installation_tokens.get(installation_id)
    if cached and cached[1] > time.time():
        return cached[0]

    resp = httpx.post(
        f'https://api.github.com/app/installations/{installation_id}/access_tokens',
        headers={
            'Authorization': f'Bearer {get_app_jwt()}',
            'Accept': 'application/vnd.github+json',
        },
    )
    resp.raise_for_status()
    token = resp.json()['token']
    _installation_tokens[installation_id] = (token, time.time() + 3000)
    return token


def github_api(installation_id: int, path: str, params: dict | None = None) -> dict | list:
    """Authenticated GET to GitHub API using installation token."""
    token = get_installation_token(installation_id)
    resp = httpx.get(
        f'https://api.github.com{path}',
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
        },
        params=params or {},
        follow_redirects=True,
    )
    resp.raise_for_status()
    return resp.json()


def get_available_repos() -> list[dict]:
    """Fetch repos accessible via all GitHub App installations."""
    try:
        jwt_token = get_app_jwt()
        resp = httpx.get(
            'https://api.github.com/app/installations',
            headers={'Authorization': f'Bearer {jwt_token}', 'Accept': 'application/vnd.github+json'},
        )
        if resp.status_code != 200:
            return []

        repos = []
        for inst in resp.json():
            token = get_installation_token(inst['id'])
            repos_resp = httpx.get(
                'https://api.github.com/installation/repositories',
                headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'},
                params={'per_page': '100'},
            )
            if repos_resp.status_code == 200:
                for repo in repos_resp.json().get('repositories', []):
                    repos.append({
                        'full_name': repo['full_name'],
                        'name': repo['name'],
                        'installation_id': inst['id'],
                    })
        return repos
    except Exception:
        return []

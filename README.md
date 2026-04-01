# Mento

Mento is a multi-project documentation portal backed by GitHub repositories.
It serves project docs from local clones, handles Auth0 authentication, manages project membership, and exposes an MCP server for remote document access and edits.

## What It Does

- Hosts documentation for multiple projects under a single app.
- Syncs docs from GitHub repositories through a GitHub App installation.
- Restricts access per project with member, admin, and super-admin roles.
- Supports custom domains and public/private project visibility.
- Exposes an MCP HTTP server for reading and updating docs.

## Repository Layout

- `memento/`: Flask app, MCP server, GitHub integration, auth, and routes.
- `frontend/`: React/Vite frontend.
- `migrations/`: database migration assets.
- `.github/workflows/deploy.yml`: deploy-on-push workflow for `master`.

## Runtime Services

- App server: Flask app on `PORT` (default `5002`)
- MCP server: FastMCP HTTP server on `MCP_PORT` (default `5003`)
- Database: PostgreSQL via `DATABASE_URL`
- Local repo cache: filesystem path at `MEMENTO_REPOS_DIR`

## Required Environment

Core:

- `DATABASE_URL`
- `SECRET_KEY`
- `MEMENTO_HOST`
- `MEMENTO_REPOS_DIR`

Auth0:

- `AUTH0_DOMAIN`
- `AUTH0_CLIENT_ID`
- `AUTH0_CLIENT_SECRET`
- `AUTH0_MCP_AUDIENCE` for MCP auth

GitHub App:

- `GITHUB_APP_ID`
- `GITHUB_APP_PRIVATE_KEY_PATH`
- `GITHUB_APP_CLIENT_ID`
- `GITHUB_APP_CLIENT_SECRET`
- `GITHUB_APP_WEBHOOK_SECRET`
- `GITHUB_MARKETPLACE_WEBHOOK_SECRET`
- `GITHUB_APP_NAME`

Email:

- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `MEMENTO_BASE_URL`

Optional:

- `MEMENTO_SUPER_ADMINS`
- `MCP_BASE_URL`
- `PORT`
- `MCP_PORT`

## Local Development

Install backend dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

Run the three local processes:

```bash
python3 -m memento.app
python3 -m memento.mcp_server
cd frontend && npm run dev
```

## Deployment

This repo currently deploys from pushes to `master` via [deploy.yml](/data/projects/mento/.github/workflows/deploy.yml).
The workflow connects to the target server over SSH and runs a `deploy` command remotely.

Infrastructure, host-specific config, and process-manager glue should be treated as deployment concerns, not core application code.

## Security Notes

- `master` should stay protected and receive changes through pull requests.
- Repository file reads are constrained to the configured project repo path.
- Auth redirects are validated before post-login redirect.
- GitHub webhook endpoints validate signatures when secrets are configured.

## Current Gaps

- There is no CI workflow for tests or lint checks yet.
- The frontend `README` is still the default Vite template and has not been rewritten.

"""Flask application factory for Memento — multi-project docs portal."""

import os

from dotenv import load_dotenv
from flask import Flask, abort, g, redirect, request, session
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static',
        static_url_path='/static',
    )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'memento-dev-secret')

    dev_mode = os.getenv('MEMENTO_DEV', '') == '1'
    _branch_cache: dict[str, str] = {}

    # Ensure DB schema
    from .db import ensure_schema
    ensure_schema()

    # Auth (global)
    from .auth import auth_bp, has_project_access, init_auth
    init_auth(app)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Per-project blueprints
    from .routes.docs import docs_bp
    from .routes.github import github_bp
    from .routes.settings import settings_bp
    app.register_blueprint(docs_bp, url_prefix='/<project>')
    app.register_blueprint(github_bp, url_prefix='/<project>')
    app.register_blueprint(settings_bp, url_prefix='/<project>')

    # Global: admin, projects, webhook
    from .routes.global_admin import global_admin_bp
    from .routes.projects import projects_bp
    app.register_blueprint(global_admin_bp)
    app.register_blueprint(projects_bp)

    # Extract project from URL and resolve config
    @app.url_value_preprocessor
    def resolve_project(endpoint, values):
        if values:
            project = values.pop('project', None)
            if project:
                from .db import get_project
                config = get_project(project)
                if not config:
                    if dev_mode:
                        config = _dev_config(project)
                    else:
                        abort(404)
                # Resolve default branch (cached)
                if config.repo_full_name and config.installation_id:
                    if project not in _branch_cache:
                        try:
                            from .github_app import github_api
                            repo_info = github_api(config.installation_id, f'/repos/{config.repo_full_name}')
                            _branch_cache[project] = repo_info.get('default_branch', 'main')
                        except Exception:
                            _branch_cache[project] = 'main'
                    config.default_branch = _branch_cache[project]
                g.project = project
                g.config = config

    # Dev mode: auto-login
    if dev_mode:
        @app.before_request
        def dev_auto_login():
            if not session.get('user'):
                session['user'] = {
                    'email': 'dev@local', 'name': 'Dev', 'picture': '',
                }
                g.user_role = 'admin'

    # Root route: project dashboard
    @app.route('/')
    def root():
        user = session.get('user')
        if not dev_mode and not user:
            return _welcome_page()

        from .db import load_projects, load_projects_for_user
        if dev_mode:
            projects = load_projects()
        else:
            projects = load_projects_for_user(user['email'])

        if len(projects) == 1:
            return redirect(f'/{next(iter(projects))}/')
        return _dashboard_page(projects, user)

    @app.context_processor
    def inject_globals():
        return {
            'config': getattr(g, 'config', None),
            'project_slug': getattr(g, 'project', None),
            'user_role': getattr(g, 'user_role', None),
        }

    return app


def _dev_config(project: str):
    from .config import ProjectConfig
    return ProjectConfig(slug=project, title=project.capitalize())


def _welcome_page():
    return '''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Memento — Documentation portal for your team</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<style>body { font-family: 'Inter', system-ui, sans-serif; }</style>
</head>
<body class="bg-gray-50 min-h-screen">

<!-- Nav -->
<nav class="max-w-4xl mx-auto flex justify-between items-center px-6 py-6">
    <span class="text-lg font-bold text-gray-900 tracking-tight">Memento</span>
    <a href="/auth/login?next=/" class="text-sm font-medium text-white bg-indigo-500 px-4 py-2 rounded-lg hover:bg-indigo-600 transition">Sign in</a>
</nav>

<!-- Hero -->
<section class="max-w-4xl mx-auto px-6 pt-16 pb-20 text-center">
    <h1 class="text-4xl font-bold text-gray-900 mb-4">Your docs, always accessible</h1>
    <p class="text-lg text-gray-500 max-w-2xl mx-auto mb-8">
        Memento turns your GitHub markdown into a clean documentation portal.
        Invite your team, control access, and let AI read your docs too.
    </p>
    <a href="/auth/login?next=/" class="inline-flex items-center gap-2 text-sm font-medium text-white bg-indigo-500 px-6 py-3 rounded-lg hover:bg-indigo-600 transition">
        Get started
    </a>
</section>

<!-- Features -->
<section class="max-w-4xl mx-auto px-6 pb-20">
    <div class="grid md:grid-cols-3 gap-6">
        <div class="bg-white rounded-xl p-6 shadow-sm">
            <div class="text-2xl mb-3">&#128194;</div>
            <h3 class="font-semibold text-gray-900 mb-1">GitHub-powered</h3>
            <p class="text-sm text-gray-500">Connect a GitHub repo and Memento renders your markdown docs with a clean UI. No build step, no config files.</p>
        </div>
        <div class="bg-white rounded-xl p-6 shadow-sm">
            <div class="text-2xl mb-3">&#128101;</div>
            <h3 class="font-semibold text-gray-900 mb-1">Team access control</h3>
            <p class="text-sm text-gray-500">Invite members by email, allow entire domains, and manage roles. Each project has its own permissions.</p>
        </div>
        <div class="bg-white rounded-xl p-6 shadow-sm">
            <div class="text-2xl mb-3">&#129302;</div>
            <h3 class="font-semibold text-gray-900 mb-1">AI-ready via MCP</h3>
            <p class="text-sm text-gray-500">Connect Claude AI to your docs with one URL. Your team can query documentation directly from claude.ai.</p>
        </div>
    </div>
</section>

<!-- How it works -->
<section class="max-w-4xl mx-auto px-6 pb-20">
    <h2 class="text-xl font-bold text-gray-900 mb-6 text-center">How it works</h2>
    <div class="grid md:grid-cols-4 gap-4">
        <div class="text-center">
            <div class="w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 font-bold text-sm flex items-center justify-center mx-auto mb-2">1</div>
            <p class="text-sm text-gray-600">Sign in and create a project</p>
        </div>
        <div class="text-center">
            <div class="w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 font-bold text-sm flex items-center justify-center mx-auto mb-2">2</div>
            <p class="text-sm text-gray-600">Pick a GitHub repo with markdown docs</p>
        </div>
        <div class="text-center">
            <div class="w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 font-bold text-sm flex items-center justify-center mx-auto mb-2">3</div>
            <p class="text-sm text-gray-600">Invite your team by email or domain</p>
        </div>
        <div class="text-center">
            <div class="w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 font-bold text-sm flex items-center justify-center mx-auto mb-2">4</div>
            <p class="text-sm text-gray-600">Browse docs on the web or via Claude AI</p>
        </div>
    </div>
</section>

<!-- Footer -->
<footer class="max-w-4xl mx-auto px-6 py-8 border-t border-gray-200 text-center">
    <p class="text-xs text-gray-400">Memento &mdash; open source on <a href="https://github.com/AlexisLaporte/memento" class="hover:text-gray-600 underline" target="_blank">GitHub</a></p>
</footer>

</body></html>'''


def _dashboard_page(configs, user):
    cards = ''
    for slug, config in configs.items():
        cards += f'''
        <a href="/{slug}/" class="block border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow bg-white">
            <div class="font-semibold text-lg" style="color:{config.color}">{config.title}</div>
            <p class="text-sm text-gray-500 mt-1">{config.repo_full_name}</p>
        </a>'''

    user_info = ''
    if user:
        email = user.get('email', '')
        user_info = f'''
        <div class="flex items-center gap-3">
            <span class="text-sm text-gray-400">{email}</span>
            <a href="/auth/logout" class="text-sm text-gray-400 hover:text-gray-600">Logout</a>
        </div>'''

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Memento</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
body {{ font-family: 'Inter', system-ui, sans-serif; background: #f8fafc; margin: 0; min-height: 100vh; padding: 2rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }}
</style></head>
<body>
<div class="max-w-3xl mx-auto" style="max-width:800px;margin:0 auto">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem">
        <h1 style="color:#374151;font-size:1.25rem;font-weight:600;margin:0">Memento</h1>
        {user_info}
    </div>
    <div class="grid">{cards if cards else '<p style="color:#9ca3af;font-size:0.875rem">No projects yet.</p>'}</div>
    <div style="margin-top:1.5rem">
        <a href="/new" style="display:inline-flex;align-items:center;gap:0.5rem;padding:0.5rem 1rem;background:#6366f1;color:#fff;border-radius:0.375rem;font-size:0.875rem;text-decoration:none">
            + New project
        </a>
    </div>
</div>
</body></html>'''


def main():
    """CLI entry point."""
    app = create_app()
    port = int(os.getenv('PORT', '5002'))
    app.run(debug=True, port=port)


if __name__ == '__main__':
    main()

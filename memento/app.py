"""Flask application factory for Mento — multi-project docs portal."""

import os

from dotenv import load_dotenv
from flask import Flask, abort, g, redirect, request, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

# Resolve frontend dist path
_frontend_dist = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder=None,  # No Flask static — served by SPA or nginx
    )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'memento-dev-secret')

    main_host = os.getenv('MEMENTO_HOST', 'memento.local')

    # Ensure DB schema
    from .db import ensure_schema
    ensure_schema()

    # Auth (global)
    from .auth import auth_bp, init_auth
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
                    abort(404)
                g.project = project
                g.config = config

    # Custom domains: redirect root to /<project>/
    @app.before_request
    def custom_domain_redirect():
        host = request.host.split(':')[0]
        if host == main_host:
            return
        # Skip auth/api paths (already project-agnostic)
        if request.path.startswith(('/auth/', '/api/')):
            return
        from .db import get_project_by_domain
        config = get_project_by_domain(host)
        if not config:
            return
        # If path doesn't start with /<slug>/, redirect there
        if not request.path.startswith(f'/{config.slug}/') and request.path != f'/{config.slug}':
            return redirect(f'/{config.slug}{request.path}')

    # SPA: serve frontend/dist in prod (nginx serves static, Flask is fallback)
    dist = os.path.abspath(_frontend_dist)
    if os.path.isdir(dist):
        @app.route('/')
        def serve_spa_root():
            return send_from_directory(dist, 'index.html')

        @app.errorhandler(404)
        def spa_fallback(e):
            # Non-API 404s → serve SPA for client-side routing
            if '/api/' not in request.path:
                return send_from_directory(dist, 'index.html')
            return e

    return app


def main():
    """CLI entry point."""
    app = create_app()
    port = int(os.getenv('PORT', '5002'))
    app.run(debug=True, port=port)


if __name__ == '__main__':
    main()

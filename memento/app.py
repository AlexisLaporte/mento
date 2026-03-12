"""Flask application factory for Memento."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, redirect, session
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config

load_dotenv()


def create_app(config_path: str | None = None) -> Flask:
    """Create and configure the Flask application from a YAML config."""
    config_path = config_path or os.getenv('MEMENTO_CONFIG')
    if not config_path:
        print("Error: set MEMENTO_CONFIG env var or pass config path", file=sys.stderr)
        sys.exit(1)

    config = Config.from_yaml(config_path)

    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static',
        static_url_path='/static',
    )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'memento-dev-secret')

    # Store config on app for template access
    app.config['MEMENTO'] = config

    # Auth
    from .auth import auth_bp, init_auth
    init_auth(app, config)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Docs routes
    from .routes.docs import docs_bp, init_docs
    init_docs(config)
    app.register_blueprint(docs_bp)

    # GitHub routes
    from .routes.github import github_bp, init_github
    init_github(config)
    app.register_blueprint(github_bp)

    dev_mode = os.getenv('MEMENTO_DEV', '') == '1'

    # Root route
    @app.route('/')
    @app.route('/<path:doc_path>')
    def index(doc_path=None):
        if dev_mode and not session.get('user'):
            session['user'] = {'email': 'dev@local', 'name': 'Dev', 'picture': '', 'role': 'admin'}
        if session.get('user'):
            from flask import render_template
            return render_template('index.html', config=config)
        return _login_page(config)

    # Inject config into all templates
    @app.context_processor
    def inject_config():
        return {'config': config}

    return app


def _login_page(config):
    color = config.branding.color
    title = config.branding.title
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
body {{ font-family: 'Inter', system-ui, sans-serif; background: #f8fafc; margin: 0;
  min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
.card {{ text-align: center; }}
.title {{ color: {color}; font-size: 1.5rem; font-weight: 600; letter-spacing: 0.025em; }}
.sub {{ color: #9ca3af; font-size: 0.875rem; margin: 0.75rem 0 2rem; }}
.btn {{ display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.625rem 1.5rem;
  background: #fff; border: 1px solid #e5e7eb; border-radius: 0.5rem; color: #374151;
  font-size: 0.875rem; text-decoration: none; transition: all 0.15s; }}
.btn:hover {{ border-color: {color}; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.btn svg {{ width: 18px; height: 18px; }}
</style></head>
<body><div class="card">
<div class="title">{title}</div>
<p class="sub">Documentation portal</p>
<a href="/auth/login" class="btn">
<svg viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
Sign in with Google</a>
</div></body></html>'''


def main():
    """CLI entry point."""
    config_path = sys.argv[1] if len(sys.argv) > 1 else os.getenv('MEMENTO_CONFIG')
    app = create_app(config_path)
    port = int(os.getenv('PORT', '5002'))
    app.run(debug=True, port=port)


if __name__ == '__main__':
    main()

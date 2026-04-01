import pytest
from flask import Flask, session, url_for
from memento.auth import auth_bp, _is_safe_url

def test_is_safe_url():
    app = Flask(__name__)
    app.config['SERVER_NAME'] = 'memento.local'
    app.register_blueprint(auth_bp)

    with app.test_request_context(base_url='http://memento.local'):
        # Safe relative URLs
        assert _is_safe_url('/') is True
        assert _is_safe_url('/projects') is True
        assert _is_safe_url('docs/intro.md') is True

        # Safe absolute URLs (same host)
        assert _is_safe_url('http://memento.local/dashboard') is True

        # Unsafe URLs (different host)
        assert _is_safe_url('http://malicious.com') is False
        assert _is_safe_url('https://malicious.com/login') is False
        assert _is_safe_url('//malicious.com') is False

        # Malformed/Edge cases
        assert _is_safe_url('javascript:alert(1)') is False
        assert _is_safe_url('') is True # Considered relative to current path

def test_login_redirect_safety():
    app = Flask(__name__)
    app.secret_key = 'test'
    app.config['SERVER_NAME'] = 'memento.local'
    # Mocking oauth since it's not initialized
    from memento import auth
    class MockOAuth:
        def __init__(self):
            self.auth0 = MockAuth0()
    class MockAuth0:
        def authorize_redirect(self, uri):
            return "Redirecting"

    auth.oauth = MockOAuth()

    app.register_blueprint(auth_bp)

    client = app.test_client()

    # Safe next param
    with client:
        resp = client.get('/login?next=/safe')
        assert session['next'] == '/safe'

    # Unsafe next param
    with client:
        resp = client.get('/login?next=http://malicious.com')
        assert session['next'] == '/'

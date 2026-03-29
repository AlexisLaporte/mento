import unittest
from flask import Flask
from memento.auth import _is_safe_url

class TestAuthSecurity(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SERVER_NAME'] = 'memento.local'
        self.app.config['PREFERRED_URL_SCHEME'] = 'https'

    def test_is_safe_url(self):
        with self.app.test_request_context(base_url='https://memento.local'):
            # Safe relative URLs
            self.assertTrue(_is_safe_url('/'))
            self.assertTrue(_is_safe_url('/dashboard'))
            self.assertTrue(_is_safe_url('/project/docs/page'))

            # Safe absolute URLs with same host
            self.assertTrue(_is_safe_url('https://memento.local/'))
            self.assertTrue(_is_safe_url('https://memento.local/dashboard'))
            self.assertTrue(_is_safe_url('http://memento.local/dashboard'))

            # Unsafe external URLs
            self.assertFalse(_is_safe_url('https://evil.com'))
            self.assertFalse(_is_safe_url('https://evil.com/dashboard'))
            self.assertFalse(_is_safe_url('//evil.com'))
            self.assertFalse(_is_safe_url('javascript:alert(1)'))

            # Empty or None
            self.assertFalse(_is_safe_url(''))
            self.assertFalse(_is_safe_url(None))

if __name__ == '__main__':
    unittest.main()

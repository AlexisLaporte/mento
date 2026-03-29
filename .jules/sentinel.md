## 2025-05-15 - [CRITICAL] Open Redirect Mitigation in Auth0 Flow
**Vulnerability:** User-controlled 'next' parameter was used in Auth0 login and callback routes without validation, allowing Open Redirect (CWE-601).
**Learning:** Redirection parameters in authentication flows are high-risk entry points. Flask's `redirect()` does not perform host validation by default.
**Prevention:** Implement a central `_is_safe_url` helper that validates the target host against `request.host_url` and enforce it in all auth-related redirection points.

## 2025-05-15 - [improvement] Module Name Shadowing in Memento
**Vulnerability:** `memento/email.py` shadowed the Python standard library `email` module.
**Learning:** This caused `ModuleNotFoundError: No module named 'email.errors'` when other libraries (like `werkzeug` or `requests`) tried to import the standard `email` utilities.
**Prevention:** Avoid naming local modules the same as standard library modules. While I reverted the rename to stay within the 50-line security fix constraint, future refactoring should rename it to `notifications.py` or similar.

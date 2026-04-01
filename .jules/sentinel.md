## 2025-05-15 - [Open Redirect in Auth0 Flow]
**Vulnerability:** The `next` parameter in `/login` and `/callback` routes was used for redirection without validation, allowing attackers to redirect users to external, potentially malicious domains after authentication.
**Learning:** Redirection parameters must always be validated against the application's own host and scheme to prevent phishing and other redirection-based attacks.
**Prevention:** Implement a helper like `_is_safe_url` using `urlparse` and `urljoin` to compare the target URL's domain and scheme against the current application's host.

## 2025-05-15 - [Path Traversal in Repository File Access]
**Vulnerability:** Sibling directory path traversal in `memento/repo.py`.
**Learning:** Using `startswith` on resolved paths is insufficient if a directory name is a prefix of another (e.g., `/app/repo` and `/app/repo-secret`).
**Prevention:** Always use `os.path.commonpath` to ensure a resolved path resides within the intended base directory.

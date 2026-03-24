## 2025-05-15 - [Path Traversal in Repository File Access]
**Vulnerability:** Sibling directory path traversal in `memento/repo.py`.
**Learning:** Using `startswith` on resolved paths is insufficient if a directory name is a prefix of another (e.g., `/app/repo` and `/app/repo-secret`).
**Prevention:** Always use `os.path.commonpath` to ensure a resolved path resides within the intended base directory.

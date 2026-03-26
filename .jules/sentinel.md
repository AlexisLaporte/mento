## 2025-03-26 - [Path Traversal: commonpath vs startswith]
**Vulnerability:** Path Traversal via Sibling Directory Attack.
**Learning:** Using `os.path.realpath(path).startswith(base)` is insufficient for path validation if the attacker can influence the path to point to a sibling directory whose name begins with the same prefix as the base directory (e.g., `/repos/app` and `/repos/app-secrets`).
**Prevention:** Always use `os.path.commonpath([base, path]) == base` to ensure the resolved path is strictly within the intended directory hierarchy.

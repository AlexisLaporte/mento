## 2025-05-15 - Redact GitHub Tokens from Git Error Messages
**Vulnerability:** GitHub installation tokens were leaked in plaintext in application logs and stack traces if `git clone` or `git pull` operations failed, as the token was included in the `git -c` command-line arguments and subsequently captured in `stderr`.
**Learning:** Even if subprocess commands are executed with `capture_output=True`, any resulting `stderr` or `stdout` that is raised in an exception or logged as a warning can still leak sensitive credentials present in the command string.
**Prevention:** Implement a standard `_redact(text, token)` helper function to mask credentials in subprocess output (e.g., `stderr.strip()`) before it is used for any logging or exception raising.

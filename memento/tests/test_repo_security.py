import logging
import pytest
from unittest.mock import patch, MagicMock
from memento.repo import clone_repo, pull_repo

@patch('memento.repo.get_installation_token')
@patch('memento.repo.subprocess.run')
@patch('memento.repo.os.makedirs')
@patch('memento.repo.shutil.rmtree')
@patch('memento.repo.os.path.exists')
def test_clone_repo_redacts_token(mock_exists, mock_rmtree, mock_makedirs, mock_run, mock_get_token):
    # Setup
    mock_get_token.return_value = "secret-token-123"
    mock_exists.return_value = False

    # Mock subprocess.run to fail and leak the token in stderr
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "error: failed to clone with token secret-token-123"
    mock_run.return_value = mock_result

    # Execution & Verification
    with pytest.raises(RuntimeError) as excinfo:
        clone_repo("test-slug", "owner/repo", 123)

    assert "secret-token-123" not in str(excinfo.value)
    assert "[REDACTED]" in str(excinfo.value)

@patch('memento.repo.get_installation_token')
@patch('memento.repo.subprocess.run')
@patch('memento.repo.os.path.isdir')
def test_pull_repo_redacts_token(mock_isdir, mock_run, mock_get_token, caplog):
    # Setup
    mock_isdir.return_value = True
    mock_get_token.return_value = "secret-token-456"

    # Mock subprocess.run to fail and leak the token in stderr
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "error: failed to pull with token secret-token-456"
    mock_run.return_value = mock_result

    # Execution
    with caplog.at_level(logging.WARNING):
        pull_repo("test-slug", 123)

    # Verification
    assert "secret-token-456" not in caplog.text
    assert "[REDACTED]" in caplog.text

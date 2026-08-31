import os
import subprocess
import tempfile
import pytest
from pathlib import Path

@pytest.fixture
def temp_git_repo(monkeypatch):
    """Creates an isolated temporary Git repository with an initial commit on prod."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Configure local git user
        subprocess.run(["git", "init", "-b", "prod"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True)
        
        # Initial commit on prod
        init_file = repo_path / "README.md"
        init_file.write_text("# Test Repo\n")
        subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "chore: initial commit on prod"], cwd=repo_path, check=True, capture_output=True)
        
        # Switch working directory to repo
        monkeypatch.chdir(repo_path)
        
        yield repo_path

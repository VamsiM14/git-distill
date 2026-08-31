import subprocess
from pathlib import Path
from typer.testing import CliRunner
from git_distill.cli import app

runner = CliRunner()

def test_restore_dirty_working_tree_fails_safely(temp_git_repo):
    repo_path = temp_git_repo
    subprocess.run(["git", "checkout", "-b", "feature/dirty-test"], cwd=repo_path, check=True, capture_output=True)

    # Create uncommitted dirty file
    dirty_file = repo_path / "dirty.txt"
    dirty_file.write_text("uncommitted changes\n")

    result = runner.invoke(app, ["restore", "--prod-branch", "prod"])
    assert result.exit_code != 0
    assert "Working tree is not clean" in result.stdout or "uncommitted changes" in result.stdout

def test_restore_dry_run_does_not_modify_git_or_files(temp_git_repo):
    repo_path = temp_git_repo
    subprocess.run(["git", "checkout", "-b", "feature/dryrun-test"], cwd=repo_path, check=True, capture_output=True)

    # Add unready file
    unready = repo_path / "unready.py"
    unready.write_text("print('unready')\n")
    subprocess.run(["git", "add", "unready.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run([
        "git", "-c", "user.name=Bob Vance", "-c", "user.email=bob@example.com",
        "commit", "-m", "feat: unready feature"
    ], cwd=repo_path, check=True, capture_output=True)

    # Dry run restore
    result = runner.invoke(app, [
        "restore",
        "--prod-branch", "prod",
        "--unready", "Bob Vance",
        "--dry-run"
    ])
    assert result.exit_code == 0
    assert "DRY RUN" in result.stdout
    # File should still exist in working tree
    assert unready.exists()
    # No backup branch created
    branches = subprocess.check_output(["git", "branch"], cwd=repo_path, text=True)
    assert "backup/" not in branches

def test_restore_pure_unready_files_creates_backup_and_commits(temp_git_repo):
    repo_path = temp_git_repo

    # Set up initial state on prod with base_file.py
    base_file = repo_path / "base_file.py"
    base_file.write_text("PROD_VERSION = 1\n")
    subprocess.run(["git", "add", "base_file.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: base prod file"], cwd=repo_path, check=True, capture_output=True)

    # Create feature branch
    subprocess.run(["git", "checkout", "-b", "feature/restore-test"], cwd=repo_path, check=True, capture_output=True)

    # 1. Confirmed file by Alice
    conf_file = repo_path / "confirmed_feature.py"
    conf_file.write_text("def confirmed(): pass\n")
    subprocess.run(["git", "add", "confirmed_feature.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run([
        "git", "-c", "user.name=Alice Miller", "-c", "user.email=alice@example.com",
        "commit", "-m", "feat: confirmed work by Alice"
    ], cwd=repo_path, check=True, capture_output=True)

    # 2. Unready file by Bob (modifies base_file.py and adds unready_feature.py)
    base_file.write_text("PROD_VERSION = 2  # Modified by Bob\n")
    unready_file = repo_path / "unready_feature.py"
    unready_file.write_text("def unready(): pass\n")
    subprocess.run(["git", "add", "base_file.py", "unready_feature.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run([
        "git", "-c", "user.name=Bob Vance", "-c", "user.email=bob@example.com",
        "commit", "-m", "feat: unready work by Bob"
    ], cwd=repo_path, check=True, capture_output=True)

    # Execute restore
    result = runner.invoke(app, [
        "restore",
        "--prod-branch", "prod",
        "--confirmed", "Alice Miller",
        "--unready", "Bob Vance"
    ])
    assert result.exit_code == 0
    assert "Restoring unconfirmed files" in result.stdout or "Restored" in result.stdout

    # Verify backup branch created
    branches = subprocess.check_output(["git", "branch"], cwd=repo_path, text=True)
    assert "backup/feature/restore-test-" in branches

    # Verify base_file.py was restored to Prod content
    assert base_file.read_text() == "PROD_VERSION = 1\n"

    # Verify unready_feature.py was removed (since it didn't exist in prod)
    assert not unready_file.exists()

    # Verify confirmed_feature.py remains intact
    assert conf_file.exists()
    assert conf_file.read_text() == "def confirmed(): pass\n"

    # Verify Git commit created with standardized message
    last_commit_msg = subprocess.check_output(["git", "log", "-1", "--pretty=%s"], cwd=repo_path, text=True).strip()
    assert "revert(silver-bullet)" in last_commit_msg

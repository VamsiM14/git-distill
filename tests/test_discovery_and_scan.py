import subprocess
from pathlib import Path
from typer.testing import CliRunner
from git_distill.cli import app

runner = CliRunner()

def test_scan_discovers_commits_and_renders_tables(temp_git_repo):
    repo_path = temp_git_repo

    # Create feature branch
    subprocess.run(["git", "checkout", "-b", "feature/payments"], cwd=repo_path, check=True, capture_output=True)

    # Commit 1 by Alice on cart.py and shared.py
    cart_file = repo_path / "cart.py"
    cart_file.write_text("def get_cart(): return []\n")
    shared_file = repo_path / "shared.py"
    shared_file.write_text("API_VERSION = 1\n")
    subprocess.run(["git", "add", "cart.py", "shared.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run([
        "git", "-c", "user.name=Alice Miller", "-c", "user.email=alice@example.com",
        "commit", "-m", "feat: add cart logic"
    ], cwd=repo_path, check=True, capture_output=True)

    # Commit 2 by Bob on payment.py and shared.py
    payment_file = repo_path / "payment.py"
    payment_file.write_text("def process_payment(): pass\n")
    shared_file.write_text("API_VERSION = 1\nPAYMENT_ENABLED = True\n")
    subprocess.run(["git", "add", "payment.py", "shared.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run([
        "git", "-c", "user.name=Bob Vance", "-c", "user.email=bob@example.com",
        "commit", "-m", "feat: add payment processing"
    ], cwd=repo_path, check=True, capture_output=True)

    # Run gitbender scan
    result = runner.invoke(app, ["scan", "--prod-branch", "prod"])
    assert result.exit_code == 0
    assert "Alice Miller" in result.stdout
    assert "Bob Vance" in result.stdout
    assert "cart.py" in result.stdout
    assert "payment.py" in result.stdout
    assert "shared.py" in result.stdout
    assert "Mixed" in result.stdout or "MIX" in result.stdout

def test_scan_when_no_unmerged_commits(temp_git_repo):
    repo_path = temp_git_repo
    subprocess.run(["git", "checkout", "-b", "feature/empty-diff"], cwd=repo_path, check=True, capture_output=True)
    result = runner.invoke(app, ["scan", "--prod-branch", "prod"])
    assert result.exit_code == 0
    assert "No unmerged commits found" in result.stdout or "Already up-to-date" in result.stdout

def test_scan_with_offline_flag(temp_git_repo):
    repo_path = temp_git_repo
    subprocess.run(["git", "checkout", "-b", "feature/offline-test"], cwd=repo_path, check=True, capture_output=True)
    result = runner.invoke(app, ["scan", "--prod-branch", "prod", "--no-fetch"])
    assert result.exit_code == 0

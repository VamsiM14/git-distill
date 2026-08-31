import subprocess
from pathlib import Path
from typer.testing import CliRunner
from git_distill.cli import app

runner = CliRunner()

def test_review_and_classification_flags(temp_git_repo):
    repo_path = temp_git_repo
    subprocess.run(["git", "checkout", "-b", "feature/review-test"], cwd=repo_path, check=True, capture_output=True)

    # Alice touches confirmed_file.py
    f1 = repo_path / "confirmed_file.py"
    f1.write_text("def confirmed(): pass\n")
    subprocess.run(["git", "add", "confirmed_file.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run([
        "git", "-c", "user.name=Alice Miller", "-c", "user.email=alice@example.com",
        "commit", "-m", "feat: confirmed work"
    ], cwd=repo_path, check=True, capture_output=True)

    # Bob touches unready_file.py
    f2 = repo_path / "unready_file.py"
    f2.write_text("def unready(): pass\n")
    subprocess.run(["git", "add", "unready_file.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run([
        "git", "-c", "user.name=Bob Vance", "-c", "user.email=bob@example.com",
        "commit", "-m", "feat: unready work"
    ], cwd=repo_path, check=True, capture_output=True)

    # Both touch mixed_file.py
    f3 = repo_path / "mixed_file.py"
    f3.write_text("LINE_1 = 1\n")
    subprocess.run(["git", "add", "mixed_file.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run([
        "git", "-c", "user.name=Alice Miller", "-c", "user.email=alice@example.com",
        "commit", "-m", "feat: mixed part 1"
    ], cwd=repo_path, check=True, capture_output=True)

    f3.write_text("LINE_1 = 1\nLINE_2 = 2\n")
    subprocess.run(["git", "add", "mixed_file.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run([
        "git", "-c", "user.name=Bob Vance", "-c", "user.email=bob@example.com",
        "commit", "-m", "feat: mixed part 2"
    ], cwd=repo_path, check=True, capture_output=True)

    # Run review with Alice confirmed, Bob unready
    result = runner.invoke(app, [
        "review",
        "--prod-branch", "prod",
        "--confirmed", "Alice Miller",
        "--unready", "Bob Vance"
    ])
    assert result.exit_code == 0
    assert "Classification" in result.stdout
    assert "confirmed_file.py" in result.stdout
    assert "Confirmed" in result.stdout
    assert "unready_file.py" in result.stdout
    assert "Unready" in result.stdout
    assert "mixed_file.py" in result.stdout
    assert "Mixed" in result.stdout

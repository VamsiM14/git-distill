import os
import sys
import tempfile
import subprocess
from pathlib import Path
from typer.testing import CliRunner
from git_distill.cli import app

runner = CliRunner()

def test_mixed_file_interactive_resolution_with_mock_editor(temp_git_repo, monkeypatch):
    repo_path = temp_git_repo

    # Prod baseline for mixed_file.py
    base_file = repo_path / "mixed_file.py"
    base_file.write_text("def base():\n    return 'prod_baseline'\n")
    subprocess.run(["git", "add", "mixed_file.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: initial mixed file in prod"], cwd=repo_path, check=True, capture_output=True)

    # Feature branch
    subprocess.run(["git", "checkout", "-b", "feature/mixed-test"], cwd=repo_path, check=True, capture_output=True)

    # Alice adds confirmed block
    base_file.write_text(
        "def base():\n    return 'prod_baseline'\n\n"
        "def confirmed_feature():\n    return 'alice_ready'\n"
    )
    subprocess.run(["git", "add", "mixed_file.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run([
        "git", "-c", "user.name=Alice Miller", "-c", "user.email=alice@example.com",
        "commit", "-m", "feat: alice ready feature in mixed file"
    ], cwd=repo_path, check=True, capture_output=True)

    # Bob adds unready block
    base_file.write_text(
        "def base():\n    return 'prod_baseline'\n\n"
        "def confirmed_feature():\n    return 'alice_ready'\n\n"
        "def unready_feature():\n    return 'bob_unready'\n"
    )
    subprocess.run(["git", "add", "mixed_file.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run([
        "git", "-c", "user.name=Bob Vance", "-c", "user.email=bob@example.com",
        "commit", "-m", "feat: bob unready feature in mixed file"
    ], cwd=repo_path, check=True, capture_output=True)

    # Create mock diff editor script in a separate temporary directory
    mock_dir = tempfile.TemporaryDirectory()
    mock_editor = Path(mock_dir.name) / "mock_editor.py"
    mock_editor.write_text(
        "import sys, pathlib\n"
        "prod_file = pathlib.Path(sys.argv[1])\n"
        "working_file = pathlib.Path(sys.argv[2])\n"
        "# Verify prod_file exists\n"
        "assert prod_file.exists()\n"
        "content = working_file.read_text()\n"
        "# Strip Bob's unready function\n"
        "cleaned = content.replace('def unready_feature():\\n    return \\'bob_unready\\'\\n', '')\n"
        "working_file.write_text(cleaned)\n"
    )

    # Configure mock editor in env
    editor_cmd = f"{sys.executable} {mock_editor}"
    monkeypatch.setenv("GITDISTILL_DIFF_EDITOR", editor_cmd)

    # Run restore
    result = runner.invoke(app, [
        "restore",
        "--prod-branch", "prod",
        "--confirmed", "Alice Miller",
        "--unready", "Bob Vance"
    ])
    assert result.exit_code == 0
    assert "mixed_file.py" in result.stdout

    # Verify final content has confirmed block but not unready block
    final_content = base_file.read_text()
    assert "alice_ready" in final_content
    assert "bob_unready" not in final_content
    mock_dir.cleanup()

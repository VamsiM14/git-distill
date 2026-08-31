import json
import subprocess
from pathlib import Path
from typer.testing import CliRunner
from git_distill.cli import app

runner = CliRunner()

def test_audit_log_generation_and_undo_rollback(temp_git_repo):
    repo_path = temp_git_repo

    # Set up initial file in prod
    test_file = repo_path / "service.py"
    test_file.write_text("SERVICE_VERSION = 1\n")
    subprocess.run(["git", "add", "service.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: base service in prod"], cwd=repo_path, check=True, capture_output=True)

    # Checkout feature branch
    subprocess.run(["git", "checkout", "-b", "feature/audit-test"], cwd=repo_path, check=True, capture_output=True)

    # Bob modifies service.py
    test_file.write_text("SERVICE_VERSION = 2  # unready change\n")
    subprocess.run(["git", "add", "service.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run([
        "git", "-c", "user.name=Bob Vance", "-c", "user.email=bob@example.com",
        "commit", "-m", "feat: bob unready change"
    ], cwd=repo_path, check=True, capture_output=True)

    # Run restore
    result = runner.invoke(app, [
        "restore",
        "--prod-branch", "prod",
        "--unready", "Bob Vance"
    ])
    assert result.exit_code == 0

    # 1. Verify audit logs created under .gitdistill/
    audit_dir = repo_path / ".gitdistill"
    assert audit_dir.exists()
    json_logs = list(audit_dir.glob("audit-*.json"))
    md_logs = list(audit_dir.glob("audit-*.md"))
    assert len(json_logs) >= 1
    assert len(md_logs) >= 1

    # Verify JSON content
    audit_data = json.loads(json_logs[0].read_text())
    assert audit_data["branch"] == "feature/audit-test"
    assert "service.py" in audit_data["restored_files"]
    assert "Bob Vance" in audit_data["unready_authors"]

    # Verify file was restored to Prod
    assert test_file.read_text() == "SERVICE_VERSION = 1\n"

    # 2. Run undo command to roll back
    undo_result = runner.invoke(app, ["undo", "--yes"])
    assert undo_result.exit_code == 0
    assert "Successfully rolled back" in undo_result.stdout or "Rolled back" in undo_result.stdout

    # Verify file content is back to Bob's unready version (pre-restore)
    assert test_file.read_text() == "SERVICE_VERSION = 2  # unready change\n"

def test_audit_list_and_clean_commands(temp_git_repo):
    repo_path = temp_git_repo
    audit_dir = repo_path / ".gitdistill"
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "audit-20260101_000000.json").write_text("{}")
    (audit_dir / "audit-20260101_000000.md").write_text("# Test")

    # List audit logs
    list_res = runner.invoke(app, ["audit"])
    assert list_res.exit_code == 0
    assert "audit-20260101_000000.json" in list_res.stdout

    # Clean audit logs
    clean_res = runner.invoke(app, ["audit", "--clean"])
    assert clean_res.exit_code == 0
    assert "Cleaned 2 audit log file(s)" in clean_res.stdout
    assert len(list(audit_dir.glob("audit-*.*"))) == 0

def test_restore_no_audit_flag(temp_git_repo):
    repo_path = temp_git_repo
    subprocess.run(["git", "checkout", "-b", "feature/no-audit-test"], cwd=repo_path, check=True, capture_output=True)

    unready = repo_path / "extra.py"
    unready.write_text("print('extra')\n")
    subprocess.run(["git", "add", "extra.py"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run([
        "git", "-c", "user.name=Bob Vance", "-c", "user.email=bob@example.com",
        "commit", "-m", "feat: unready extra"
    ], cwd=repo_path, check=True, capture_output=True)

    result = runner.invoke(app, [
        "restore",
        "--prod-branch", "prod",
        "--unready", "Bob Vance",
        "--no-audit"
    ])
    assert result.exit_code == 0
    audit_dir = repo_path / ".gitdistill"
    assert not audit_dir.exists() or len(list(audit_dir.glob("audit-*.*"))) == 0

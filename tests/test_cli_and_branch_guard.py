import pytest
import subprocess
from typer.testing import CliRunner
from git_distill.cli import app

runner = CliRunner()

def test_version_command():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "git-distill version 0.1.0" in result.stdout

def test_help_command():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Git Distill" in result.stdout
    assert "scan" in result.stdout

def test_branch_guard_blocks_non_feature_branch(temp_git_repo):
    # Currently on 'prod' branch
    result = runner.invoke(app, ["scan"])
    assert result.exit_code != 0
    assert "Branch Guard Violation" in result.stdout
    assert "prod" in result.stdout
    assert "feature" in result.stdout

def test_branch_guard_bypassed_with_flag(temp_git_repo):
    # Currently on 'prod' branch, but with --bypass-branch-check
    result = runner.invoke(app, ["scan", "--bypass-branch-check"])
    assert result.exit_code == 0 or "Nothing to restore" in result.stdout or "No unmerged commits" in result.stdout

@pytest.mark.parametrize("branch_name", [
    "feature",
    "feature_sales",
    "feature-sales",
    "feature/my-feature",
    "feat",
    "feat_checkout",
    "feat-checkout",
    "feat/checkout"
])
def test_branch_guard_allows_feature_naming_conventions(temp_git_repo, branch_name):
    subprocess.run(["git", "checkout", "-b", branch_name], cwd=temp_git_repo, check=True, capture_output=True)
    result = runner.invoke(app, ["scan"])
    assert result.exit_code == 0

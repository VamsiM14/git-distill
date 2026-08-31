import subprocess
from pathlib import Path
from typer.testing import CliRunner
from git_distill.cli import app

runner = CliRunner()

def test_auto_detects_main_as_prod_branch(monkeypatch):
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True)
        
        # Initial commit on main
        init_file = repo_path / "README.md"
        init_file.write_text("# Main Branch Repo\n")
        subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "chore: initial commit on main"], cwd=repo_path, check=True, capture_output=True)
        
        # Create feature_sales branch
        subprocess.run(["git", "checkout", "-b", "feature_sales"], cwd=repo_path, check=True, capture_output=True)
        
        # Add a commit
        f = repo_path / "sales.py"
        f.write_text("def sales(): pass\n")
        subprocess.run(["git", "add", "sales.py"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run([
            "git", "-c", "user.name=Alice Miller", "-c", "user.email=alice@example.com",
            "commit", "-m", "feat: sales logic"
        ], cwd=repo_path, check=True, capture_output=True)
        
        monkeypatch.chdir(repo_path)
        
        # Run scan without --prod-branch -> should auto-detect 'main'
        result = runner.invoke(app, ["scan"])
        assert result.exit_code == 0
        assert "main" in result.stdout
        assert "sales.py" in result.stdout

def test_auto_detects_master_as_prod_branch(monkeypatch):
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        subprocess.run(["git", "init", "-b", "master"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True)
        
        # Initial commit on master
        init_file = repo_path / "README.md"
        init_file.write_text("# Master Branch Repo\n")
        subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "chore: initial commit on master"], cwd=repo_path, check=True, capture_output=True)
        
        # Create feature-billing branch
        subprocess.run(["git", "checkout", "-b", "feature-billing"], cwd=repo_path, check=True, capture_output=True)
        
        monkeypatch.chdir(repo_path)
        
        # Run scan without --prod-branch -> should auto-detect 'master'
        result = runner.invoke(app, ["scan"])
        assert result.exit_code == 0
        assert "master" in result.stdout

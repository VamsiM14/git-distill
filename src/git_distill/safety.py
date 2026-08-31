import time
from pathlib import Path
from typing import Optional, List, Tuple
from git_distill.git_ops import run_git, GitError

def is_working_tree_clean(cwd: Optional[Path] = None) -> bool:
    """Checks if the git working tree and index have no uncommitted changes."""
    status = run_git(["status", "--porcelain"], cwd=cwd)
    return len(status.strip()) == 0

def create_backup_branch(branch_name: str, cwd: Optional[Path] = None) -> str:
    """Creates a timestamped snapshot backup branch of current HEAD."""
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup/{branch_name}-{ts}"
    run_git(["branch", backup_name, "HEAD"], cwd=cwd)
    return backup_name

def find_latest_backup_branch(branch_name: str, cwd: Optional[Path] = None) -> Optional[str]:
    """Finds the most recent backup branch created for this feature branch."""
    prefix = f"backup/{branch_name}-"
    all_branches_raw = run_git(["branch", "--list", f"{prefix}*"], cwd=cwd)
    branches = [b.strip().replace("*", "").strip() for b in all_branches_raw.splitlines() if b.strip()]
    if not branches:
        return None
    # Sort by timestamp descending
    return sorted(branches, reverse=True)[0]

def rollback_to_backup(backup_branch: str, cwd: Optional[Path] = None) -> None:
    """Hard resets the current branch to the exact state of backup_branch."""
    run_git(["reset", "--hard", backup_branch], cwd=cwd)

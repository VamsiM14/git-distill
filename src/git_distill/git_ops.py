import re
import shutil
import subprocess
from typing import Optional, List, Tuple
from pathlib import Path

class GitError(Exception):
    pass

def get_git_executable() -> str:
    git_bin = shutil.which("git")
    if not git_bin:
        raise GitError("Git executable not found in PATH. Please ensure Git is installed.")
    return git_bin

def run_git(args: List[str], cwd: Optional[Path] = None, check: bool = True) -> str:
    git_bin = get_git_executable()
    try:
        res = subprocess.run(
            [git_bin] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise GitError(f"Git command failed: git {' '.join(args)}\n{e.stderr.strip()}") from e

def get_current_branch(cwd: Optional[Path] = None) -> str:
    return run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)

def ref_exists(ref: str, cwd: Optional[Path] = None) -> bool:
    """Checks if a git ref (branch/commit/tag) exists and points to a valid commit."""
    try:
        run_git(["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], cwd=cwd)
        return True
    except GitError:
        return False

def resolve_baseline_branch(
    explicit_branch: Optional[str] = None,
    cwd: Optional[Path] = None
) -> str:
    """
    Resolves the baseline production branch.
    If explicit_branch is supplied, validates and resolves it.
    If None, auto-detects from candidate standard branches: prod, main, master.
    """
    if explicit_branch:
        candidates = [
            explicit_branch,
            f"origin/{explicit_branch}" if not explicit_branch.startswith("origin/") else explicit_branch,
            explicit_branch.replace("origin/", "")
        ]
        for c in candidates:
            if ref_exists(c, cwd=cwd):
                return c
        raise GitError(
            f"Target production branch '{explicit_branch}' not found in repository.\n"
            f"Please ensure the branch exists locally or run 'git fetch' to retrieve remote branches."
        )

    # Auto-detection list
    auto_candidates = [
        "origin/prod", "prod",
        "origin/main", "main",
        "origin/master", "master"
    ]
    for c in auto_candidates:
        if ref_exists(c, cwd=cwd):
            return c

    # Check remote origin HEAD symbolic ref
    try:
        origin_head = run_git(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=cwd)
        clean_head = origin_head.replace("refs/remotes/", "")
        if ref_exists(clean_head, cwd=cwd):
            return clean_head
    except GitError:
        pass

    raise GitError(
        "Could not automatically detect production baseline branch ('prod', 'main', or 'master').\n"
        "Please explicitly specify your production branch using: --prod-branch <name>"
    )

def validate_feature_branch(cwd: Optional[Path] = None, bypass: bool = False) -> Tuple[bool, str]:
    """
    Validates if the current checked-out branch starts with feature or feat (e.g., feature, feature_sales, feature/xyz).
    Returns (is_valid, branch_name).
    """
    branch = get_current_branch(cwd=cwd)
    if bypass:
        return True, branch
    is_feature = bool(re.match(r"^(feature|feat)", branch, re.IGNORECASE))
    return is_feature, branch

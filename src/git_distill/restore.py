import os
from pathlib import Path
from typing import List, Optional, Tuple
from git_distill.git_ops import run_git, GitError
from git_distill.models import DiscoveryResult, FileDivergence, FileClassification

def check_file_exists_in_ref(ref: str, file_path: str, cwd: Optional[Path] = None) -> bool:
    """Checks if a file exists in the given git commit/branch ref."""
    try:
        run_git(["cat-file", "-e", f"{ref}:{file_path}"], cwd=cwd)
        return True
    except GitError:
        return False

def execute_pure_restore(
    prod_branch: str,
    files: List[FileDivergence],
    cwd: Optional[Path] = None
) -> List[str]:
    """
    Restores all pure unready files to their prod state.
    Returns list of restored file paths.
    """
    restored: List[str] = []
    for f in files:
        if f.classification != FileClassification.PURE_UNREADY:
            continue

        exists_in_prod = check_file_exists_in_ref(prod_branch, f.path, cwd=cwd)
        if exists_in_prod:
            # File existed in prod -> checkout prod version
            run_git(["checkout", prod_branch, "--", f.path], cwd=cwd)
            run_git(["add", f.path], cwd=cwd)
        else:
            # File was newly created on feature branch -> remove and stage deletion
            target_path = (cwd / f.path) if cwd else Path(f.path)
            if target_path.exists():
                target_path.unlink()
            run_git(["rm", "--cached", "-f", "--ignore-unmatch", f.path], cwd=cwd)

        restored.append(f.path)

    return restored

def commit_restore_operation(
    restored_files: List[str],
    custom_msg: Optional[str] = None,
    cwd: Optional[Path] = None
) -> str:
    """Commits staged changes with standardized CAB metadata."""
    msg = custom_msg or "revert(silver-bullet): restore unconfirmed files to prod state for CAB release"
    msg += f"\n\nRestored {len(restored_files)} file(s) to prod state:\n"
    for rf in restored_files:
        msg += f" - {rf}\n"

    run_git(["commit", "-m", msg], cwd=cwd)
    return run_git(["rev-parse", "HEAD"], cwd=cwd)

from pathlib import Path
from typing import Optional, Dict, List, Set
from collections import defaultdict
from git_distill.git_ops import run_git, GitError, resolve_baseline_branch
from git_distill.models import DiscoveryResult, UnmergedCommit, FileDivergence, FileClassification

def fetch_prod_reference(prod_branch: str, cwd: Optional[Path] = None) -> None:
    """Attempts to fetch latest prod_branch from origin if a remote is configured."""
    try:
        remotes = run_git(["remote"], cwd=cwd)
        if "origin" in remotes.splitlines():
            clean_ref = prod_branch.replace("origin/", "")
            run_git(["fetch", "origin", clean_ref], cwd=cwd, check=False)
    except GitError:
        pass

def run_discovery(
    prod_branch: Optional[str] = None,
    cwd: Optional[Path] = None,
    auto_fetch: bool = True
) -> DiscoveryResult:
    """Discovers unmerged commits and file divergences between prod and HEAD."""
    # 1. Resolve and validate production baseline branch
    resolved_prod = resolve_baseline_branch(prod_branch, cwd=cwd)

    if auto_fetch:
        fetch_prod_reference(resolved_prod, cwd=cwd)

    # 2. Resolve merge base
    merge_base = run_git(["merge-base", resolved_prod, "HEAD"], cwd=cwd)
    current_branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)

    # 3. Extract unmerged commits
    raw_log = run_git([
        "log", "--no-merges", f"{resolved_prod}..HEAD",
        "--pretty=format:%h|||%an|||%ae|||%at|||%s"
    ], cwd=cwd)

    commits: List[UnmergedCommit] = []
    author_commits: Dict[str, List[str]] = defaultdict(list)

    if raw_log:
        for line in raw_log.splitlines():
            if not line:
                continue
            parts = line.split("|||")
            if len(parts) == 5:
                sha, author, email, ts_str, msg = parts
                commit = UnmergedCommit(
                    sha=sha,
                    author=author,
                    email=email,
                    timestamp=int(ts_str) if ts_str.isdigit() else 0,
                    message=msg
                )
                commits.append(commit)
                author_commits[author].append(sha)

    # 4. Extract modified files via numstat
    raw_numstat = run_git(["diff", "--numstat", f"{resolved_prod}...HEAD"], cwd=cwd)
    files: List[FileDivergence] = []
    author_files: Dict[str, Set[str]] = defaultdict(set)

    if raw_numstat:
        for line in raw_numstat.splitlines():
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                ins_str, del_str, file_path = parts[0], parts[1], parts[2]
                ins = int(ins_str) if ins_str.isdigit() else 0
                dels = int(del_str) if del_str.isdigit() else 0

                # Get all authors who touched this file in the divergence
                file_authors_raw = run_git([
                    "log", f"{resolved_prod}..HEAD", "--format=%an", "--", file_path
                ], cwd=cwd)
                file_authors: Set[str] = set(filter(None, file_authors_raw.splitlines()))

                for fa in file_authors:
                    author_files[fa].add(file_path)

                # Get commit hashes touching this file
                file_commits_raw = run_git([
                    "log", f"{resolved_prod}..HEAD", "--format=%h", "--", file_path
                ], cwd=cwd)
                file_commits: List[str] = list(filter(None, file_commits_raw.splitlines()))

                files.append(
                    FileDivergence(
                        path=file_path,
                        insertions=ins,
                        deletions=dels,
                        authors=file_authors,
                        commits=file_commits,
                        classification=FileClassification.MIXED if len(file_authors) > 1 else FileClassification.UNKNOWN
                    )
                )

    return DiscoveryResult(
        current_branch=current_branch,
        prod_branch=resolved_prod,
        merge_base=merge_base,
        commits=commits,
        files=files,
        author_map=dict(author_commits),
        author_files_map=dict(author_files)
    )

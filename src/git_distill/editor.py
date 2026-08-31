import os
import shutil
import shlex
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
from git_distill.git_ops import run_git, GitError

def launch_diff_editor(
    prod_branch: str,
    file_path: str,
    custom_editor: Optional[str] = None,
    cwd: Optional[Path] = None
) -> None:
    """
    Extracts the exact prod version of file_path to a temporary file and launches
    the visual diff editor (VS Code diff or custom) in wait mode.
    Stages the file upon successful editor exit.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="gitdistill_diff_"))
    try:
        prod_tmp_file = tmp_dir / f"PROD_{Path(file_path).name}"
        
        # Write exact raw bytes from git show using git_ops
        try:
            show_output = run_git(["show", f"{prod_branch}:{file_path}"], cwd=cwd)
            prod_tmp_file.write_text(show_output)
        except GitError:
            # File did not exist in prod -> write empty file
            prod_tmp_file.write_text("")

        target_file = (cwd / file_path) if cwd else Path(file_path)

        # Editor command resolution
        editor_env = os.environ.get("GITDISTILL_DIFF_EDITOR") or os.environ.get("GITBENDER_DIFF_EDITOR")
        editor_str = custom_editor or editor_env or "code --wait --diff"

        editor_tokens = shlex.split(editor_str)
        if not editor_tokens:
            raise GitError("Invalid empty diff editor command.")

        editor_bin = shutil.which(editor_tokens[0]) or editor_tokens[0]
        cmd = [editor_bin] + editor_tokens[1:] + [str(prod_tmp_file), str(target_file)]

        res = subprocess.run(cmd, cwd=cwd)
        if res.returncode != 0:
            raise GitError(f"Diff editor '{editor_tokens[0]}' exited with error code {res.returncode}")

        # Stage resolved file
        run_git(["add", file_path], cwd=cwd)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

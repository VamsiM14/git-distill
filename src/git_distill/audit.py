import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from git_distill.git_ops import run_git
from git_distill.models import AuditContext

def write_audit_logs(
    context: AuditContext,
    cwd: Optional[Path] = None
) -> Tuple[Path, Path]:
    """Writes JSON and Markdown audit logs under .gitdistill/ directory using AuditContext."""
    audit_dir = (cwd / ".gitdistill") if cwd else Path(".gitdistill")
    audit_dir.mkdir(parents=True, exist_ok=True)

    ts_str = time.strftime("%Y%m%d_%H%M%S")
    json_path = audit_dir / f"audit-{ts_str}.json"
    md_path = audit_dir / f"audit-{ts_str}.md"

    user_name = run_git(["config", "user.name"], cwd=cwd) or "Unknown"
    user_email = run_git(["config", "user.email"], cwd=cwd) or "unknown@example.com"

    all_restored = context.pure_reverted_files + context.mixed_resolved_files

    # 1. JSON Payload
    data: Dict[str, Any] = {
        "timestamp": time.time(),
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "operator": {
            "name": user_name,
            "email": user_email
        },
        "branch": context.branch,
        "prod_branch": context.prod_branch,
        "backup_branch": context.backup_branch,
        "commit_sha": context.commit_sha,
        "confirmed_authors": sorted(list(context.confirmed_authors)),
        "unready_authors": sorted(list(context.unready_authors)),
        "pure_reverted_files": context.pure_reverted_files,
        "mixed_resolved_files": context.mixed_resolved_files,
        "restored_files": all_restored
    }
    json_path.write_text(json.dumps(data, indent=2))

    # 2. Markdown Report
    md_content = f"""# Git Distill Restore Audit Log

- **Date / Time:** {data['date']}
- **Operator:** {user_name} ({user_email})
- **Feature Branch:** `{context.branch}`
- **Baseline Prod Branch:** `{context.prod_branch}`
- **Safety Backup Branch:** `{context.backup_branch or 'None'}`
- **Restore Commit:** {f'`{context.commit_sha}`' if context.commit_sha else 'Pending (Manual review & commit)'}

## Author Status Breakdown
- **Confirmed Authors (Preserved):** {', '.join(sorted(context.confirmed_authors)) if context.confirmed_authors else 'None specified'}
- **Unready Authors (Restored):** {', '.join(sorted(context.unready_authors)) if context.unready_authors else 'None specified'}

## Pure Restored Files ({len(context.pure_reverted_files)})
"""
    for rf in context.pure_reverted_files:
        md_content += f"- `{rf}` (100% Prod Restore)\n"

    md_content += f"\n## Mixed Resolved Files ({len(context.mixed_resolved_files)})\n"
    for mf in context.mixed_resolved_files:
        md_content += f"- `{mf}` (Diff UI Hunk-Level Resolution)\n"

    md_path.write_text(md_content)

    return json_path, md_path

def get_audit_dir(cwd: Optional[Path] = None) -> Path:
    return (cwd / ".gitdistill") if cwd else Path(".gitdistill")

def list_audit_logs(cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Returns a summary of existing audit logs."""
    audit_dir = get_audit_dir(cwd)
    if not audit_dir.exists():
        return {"json_logs": [], "md_logs": []}
    
    json_logs = sorted(list(audit_dir.glob("audit-*.json")), reverse=True)
    md_logs = sorted(list(audit_dir.glob("audit-*.md")), reverse=True)
    return {
        "json_logs": [str(p) for p in json_logs],
        "md_logs": [str(p) for p in md_logs]
    }

def clean_audit_logs(cwd: Optional[Path] = None) -> int:
    """Removes all audit logs from .gitdistill directory. Returns count of removed files."""
    audit_dir = get_audit_dir(cwd)
    if not audit_dir.exists():
        return 0

    count = 0
    for f in list(audit_dir.glob("audit-*.*")):
        try:
            f.unlink()
            count += 1
        except OSError:
            pass
    return count

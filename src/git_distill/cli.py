import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from typing import Optional, Set
from git_distill import __version__
from git_distill.git_ops import validate_feature_branch, GitError
from git_distill.discovery import run_discovery
from git_distill.classification import classify_files
from git_distill.reporting import render_discovery_report
from git_distill.safety import (
    is_working_tree_clean,
    create_backup_branch,
    find_latest_backup_branch,
    rollback_to_backup
)
from git_distill.restore import execute_pure_restore, commit_restore_operation
from git_distill.editor import launch_diff_editor
from git_distill.audit import write_audit_logs, list_audit_logs, clean_audit_logs
from git_distill.models import FileClassification, AuditContext

app = typer.Typer(
    help="Git Distill - CLI tool to selectively restore and promote ready changes across Git branches",
    no_args_is_help=True
)
console = Console()

def parse_csv_items(val: Optional[str]) -> Set[str]:
    if not val:
        return set()
    return {a.strip() for a in val.split(",") if a.strip()}

def ensure_feature_branch(bypass: bool = False) -> str:
    """Enforces that the current checked-out branch is a feature branch."""
    is_valid, branch = validate_feature_branch(bypass=bypass)
    if not is_valid:
        console.print(
            Panel(
                f"[bold red]❌ Branch Guard Violation[/bold red]\n\n"
                f"Current branch is '[yellow]{branch}[/yellow]'.\n"
                f"Git Distill operations must run on a [bold green]feature*[/bold green] branch (e.g. feature, feature_sales, feature/xyz) so changes propagate safely.\n\n"
                f"Please checkout your feature branch or use [cyan]--bypass-branch-check[/cyan] if you are certain.",
                title="Safety Guard",
                border_style="red"
            )
        )
        raise typer.Exit(code=1)
    return branch

def version_callback(value: bool):
    if value:
        console.print(f"[bold green]git-distill version {__version__}[/bold green]")
        raise typer.Exit()

@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Show the version and exit", callback=version_callback, is_eager=True
    )
):
    pass

@app.command()
def scan(
    prod_branch: Optional[str] = typer.Option(None, "--prod-branch", "-p", help="Target production branch reference (auto-detects prod, main, master)"),
    bypass_branch_check: bool = typer.Option(False, "--bypass-branch-check", "--force", help="Bypass feature* branch check"),
    confirmed: Optional[str] = typer.Option(None, "--confirmed", "-c", help="Comma-separated list of confirmed authors"),
    unready: Optional[str] = typer.Option(None, "--unready", "-u", help="Comma-separated list of unready authors"),
    confirmed_files: Optional[str] = typer.Option(None, "--confirmed-files", help="Comma-separated list of confirmed file paths"),
    unready_files: Optional[str] = typer.Option(None, "--unready-files", help="Comma-separated list of unready file paths"),
    no_fetch: bool = typer.Option(False, "--no-fetch", "--offline", help="Disable automatic git fetch from remote origin"),
):
    """Scan current feature branch against prod and display divergence report."""
    try:
        branch = ensure_feature_branch(bypass=bypass_branch_check)
        discovery_result = run_discovery(prod_branch=prod_branch, auto_fetch=(not no_fetch))
        console.print(f"[dim]Scanning branch '[bold]{branch}[/bold]' against baseline '[bold]{discovery_result.prod_branch}[/bold]'...[/dim]\n")
        
        conf_authors = parse_csv_items(confirmed)
        unr_authors = parse_csv_items(unready)
        conf_fls = parse_csv_items(confirmed_files)
        unr_fls = parse_csv_items(unready_files)

        if conf_authors or unr_authors or conf_fls or unr_fls:
            classify_files(
                discovery_result,
                confirmed_authors=conf_authors,
                unready_authors=unr_authors,
                confirmed_files=conf_fls,
                unready_files=unr_fls
            )

        render_discovery_report(discovery_result, console, confirmed_authors=conf_authors, unready_authors=unr_authors)
    except GitError as e:
        console.print(f"[bold red]Git Error:[/bold red] {e}")
        raise typer.Exit(code=1)

@app.command()
def review(
    prod_branch: Optional[str] = typer.Option(None, "--prod-branch", "-p", help="Target production branch reference (auto-detects prod, main, master)"),
    bypass_branch_check: bool = typer.Option(False, "--bypass-branch-check", "--force", help="Bypass feature* branch check"),
    confirmed: Optional[str] = typer.Option(None, "--confirmed", "-c", help="Comma-separated list of confirmed authors"),
    unready: Optional[str] = typer.Option(None, "--unready", "-u", help="Comma-separated list of unready authors"),
    confirmed_files: Optional[str] = typer.Option(None, "--confirmed-files", help="Comma-separated list of confirmed file paths"),
    unready_files: Optional[str] = typer.Option(None, "--unready-files", help="Comma-separated list of unready file paths"),
    no_fetch: bool = typer.Option(False, "--no-fetch", "--offline", help="Disable automatic git fetch from remote origin"),
):
    """Review and classify changes based on CAB author confirmations."""
    try:
        ensure_feature_branch(bypass=bypass_branch_check)
        discovery_result = run_discovery(prod_branch=prod_branch, auto_fetch=(not no_fetch))
        conf_authors = parse_csv_items(confirmed)
        unr_authors = parse_csv_items(unready)
        conf_fls = parse_csv_items(confirmed_files)
        unr_fls = parse_csv_items(unready_files)

        classify_files(
            discovery_result,
            confirmed_authors=conf_authors,
            unready_authors=unr_authors,
            confirmed_files=conf_fls,
            unready_files=unr_fls
        )
        render_discovery_report(discovery_result, console, confirmed_authors=conf_authors, unready_authors=unr_authors)
    except GitError as e:
        console.print(f"[bold red]Git Error:[/bold red] {e}")
        raise typer.Exit(code=1)

@app.command()
def restore(
    prod_branch: Optional[str] = typer.Option(None, "--prod-branch", "-p", help="Target production branch reference (auto-detects prod, main, master)"),
    bypass_branch_check: bool = typer.Option(False, "--bypass-branch-check", "--force", help="Bypass feature* branch check"),
    confirmed: Optional[str] = typer.Option(None, "--confirmed", "-c", help="Comma-separated list of confirmed authors"),
    unready: Optional[str] = typer.Option(None, "--unready", "-u", help="Comma-separated list of unready authors"),
    confirmed_files: Optional[str] = typer.Option(None, "--confirmed-files", help="Comma-separated list of confirmed file paths"),
    unready_files: Optional[str] = typer.Option(None, "--unready-files", help="Comma-separated list of unready file paths"),
    diff_editor: Optional[str] = typer.Option(None, "--diff-editor", help="Custom diff editor command (e.g. 'code --wait --diff')"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Simulate restore actions without modifying files or branches"),
    no_fetch: bool = typer.Option(False, "--no-fetch", "--offline", help="Disable automatic git fetch from remote origin"),
    no_audit: bool = typer.Option(False, "--no-audit", help="Skip writing local audit logs to .gitdistill/"),
):
    """Execute silver bullet restore: restore unconfirmed files and resolve mixed diffs."""
    try:
        # 1. Branch Validation
        branch = ensure_feature_branch(bypass=bypass_branch_check)

        # 2. Clean Working Tree Guard
        if not is_working_tree_clean():
            console.print(
                Panel(
                    f"[bold red]❌ Working tree is not clean[/bold red]\n\n"
                    f"You have uncommitted changes or untracked files.\n"
                    f"Please commit or stash your changes before running restore.",
                    title="Safety Guard",
                    border_style="red"
                )
            )
            raise typer.Exit(code=1)

        # 3. Discovery and Classification
        discovery_result = run_discovery(prod_branch=prod_branch, auto_fetch=(not no_fetch))
        conf_authors = parse_csv_items(confirmed)
        unr_authors = parse_csv_items(unready)
        conf_fls = parse_csv_items(confirmed_files)
        unr_fls = parse_csv_items(unready_files)

        classify_files(
            discovery_result,
            confirmed_authors=conf_authors,
            unready_authors=unr_authors,
            confirmed_files=conf_fls,
            unready_files=unr_fls
        )

        pure_unready = [f for f in discovery_result.files if f.classification == FileClassification.PURE_UNREADY]
        mixed_files = [f for f in discovery_result.files if f.classification == FileClassification.MIXED]
        pure_confirmed = [f for f in discovery_result.files if f.classification == FileClassification.PURE_CONFIRMED]

        if not pure_unready and not mixed_files:
            console.print("[green]No files require restore. All unmerged work is confirmed or preserved.[/green]")
            return

        if dry_run:
            console.print(
                Panel(
                    f"[bold yellow]⚠️ DRY RUN MODE[/bold yellow]\n\n"
                    f"• Pure Unready Files to Restore to Prod ({len(pure_unready)}): {[f.path for f in pure_unready]}\n"
                    f"• Mixed Files for Diff Resolution ({len(mixed_files)}): {[f.path for f in mixed_files]}\n"
                    f"• Confirmed Files to Preserve ({len(pure_confirmed)}): {[f.path for f in pure_confirmed]}\n\n"
                    f"No branches or files were modified.",
                    title="Restore Plan (Dry Run)",
                    border_style="yellow"
                )
            )
            return

        # 4. Mandatory Safety Backup Branch
        backup_branch = create_backup_branch(branch)
        console.print(f"[bold green]🛡️ Safety backup created:[/bold green] [cyan]{backup_branch}[/cyan]")

        pure_reverted: list[str] = []
        mixed_resolved: list[str] = []

        # 5. Pure Unready Restores
        if pure_unready:
            console.print(f"[cyan]Restoring {len(pure_unready)} unconfirmed file(s) to {discovery_result.prod_branch} state...[/cyan]")
            pure_reverted = execute_pure_restore(discovery_result.prod_branch, pure_unready)
            for rf in pure_reverted:
                console.print(f"  [red]↺ Restored to Prod:[/red] {rf}")

        # 6. Mixed Files Resolution via Diff Editor
        if mixed_files:
            console.print(f"\n[yellow]⚡ Resolving {len(mixed_files)} mixed file(s) via Diff UI...[/yellow]")
            for mf in mixed_files:
                console.print(f"  Opening [bold cyan]{mf.path}[/bold cyan] in diff editor...")
                launch_diff_editor(
                    prod_branch=discovery_result.prod_branch,
                    file_path=mf.path,
                    custom_editor=diff_editor
                )
                console.print(f"  [green]✓ Resolved and staged:[/green] {mf.path}")
                mixed_resolved.append(mf.path)

        all_restored = pure_reverted + mixed_resolved

        # 7. Commit staged changes
        commit_sha: Optional[str] = None
        if all_restored:
            commit_sha = commit_restore_operation(all_restored)
            console.print(f"\n[bold green]✅ Committed restore changes:[/bold green] [yellow]{commit_sha[:8]}[/yellow]")

        # 8. Write Structured Audit Logs
        if not no_audit:
            audit_ctx = AuditContext(
                branch=branch,
                prod_branch=discovery_result.prod_branch,
                backup_branch=backup_branch,
                commit_sha=commit_sha,
                confirmed_authors=conf_authors,
                unready_authors=unr_authors,
                pure_reverted_files=pure_reverted,
                mixed_resolved_files=mixed_resolved
            )
            json_log, md_log = write_audit_logs(audit_ctx)
            console.print(f"[dim]Audit logs written to [cyan]{json_log}[/cyan] and [cyan]{md_log}[/cyan][/dim]")

    except GitError as e:
        console.print(f"[bold red]Git Error:[/bold red] {e}")
        raise typer.Exit(code=1)

@app.command()
def audit(
    clean: bool = typer.Option(False, "--clean", help="Scrub all local audit logs in .gitdistill/"),
):
    """Inspect or manage local audit logs in .gitdistill/."""
    if clean:
        count = clean_audit_logs()
        console.print(f"[bold green]Cleaned {count} audit log file(s) from .gitdistill/[/bold green]")
    else:
        logs = list_audit_logs()
        if not logs["json_logs"]:
            console.print("[dim]No audit logs found in .gitdistill/[/dim]")
        else:
            console.print(f"[bold cyan]Found {len(logs['json_logs'])} audit log session(s) in .gitdistill/:[/bold cyan]")
            for p in logs["json_logs"]:
                console.print(f"  • [yellow]{p}[/yellow]")

@app.command()
def undo(
    bypass_branch_check: bool = typer.Option(False, "--bypass-branch-check", "--force", help="Bypass feature* branch check"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm rollback without interactive prompt"),
):
    """Roll back the feature branch to the most recent pre-restore backup snapshot."""
    try:
        branch = ensure_feature_branch(bypass=bypass_branch_check)
        latest_backup = find_latest_backup_branch(branch)
        if not latest_backup:
            console.print(f"[bold yellow]No backup branches found for branch '{branch}'.[/bold yellow]")
            raise typer.Exit(code=1)

        if not yes:
            confirm = Confirm.ask(
                f"Roll back '{branch}' to snapshot '[bold cyan]{latest_backup}[/bold cyan]'?",
                default=False
            )
            if not confirm:
                console.print("[dim]Rollback cancelled.[/dim]")
                return

        rollback_to_backup(latest_backup)
        console.print(
            Panel(
                f"[bold green]✅ Successfully rolled back '{branch}' to backup '{latest_backup}'[/bold green]\n"
                f"All files and commit history have been restored to the pre-restore state.",
                title="Rollback Complete",
                border_style="green"
            )
        )

    except GitError as e:
        console.print(f"[bold red]Git Error:[/bold red] {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()

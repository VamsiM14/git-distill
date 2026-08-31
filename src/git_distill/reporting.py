from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional, Set
from git_distill.models import DiscoveryResult, FileClassification

def render_discovery_report(
    result: DiscoveryResult,
    console: Console,
    confirmed_authors: Optional[Set[str]] = None,
    unready_authors: Optional[Set[str]] = None,
) -> None:
    """Renders the discovery overview, author breakdown with touched files, and file divergence tables."""
    if not result.commits:
        console.print(
            Panel(
                f"[bold green]✨ Already up-to-date![/bold green]\n\n"
                f"No unmerged commits found between '[bold]{result.prod_branch}[/bold]' and '[bold]{result.current_branch}[/bold]'.",
                title="Discovery Result",
                border_style="green"
            )
        )
        return

    # Header Panel
    console.print(
        Panel(
            f"[bold cyan]🔍 Git Distill Discovery:[/bold cyan] [bold]{result.current_branch}[/bold] vs [bold]{result.prod_branch}[/bold]\n"
            f"Common Ancestor (Merge-base): [yellow]{result.merge_base[:8]}[/yellow] | Total Commits: [bold]{len(result.commits)}[/bold] | Files Diverged: [bold]{len(result.files)}[/bold]",
            title="CAB Release Discovery",
            border_style="cyan"
        )
    )

    # Table 1: Author Breakdown with Touched Files
    author_table = Table(title="Author Breakdown & CAB Status", header_style="bold magenta", expand=True)
    author_table.add_column("Author", style="bold")
    author_table.add_column("Commits", justify="center")
    author_table.add_column("Status", justify="center")
    author_table.add_column("Touched Files")

    conf_lower = {a.lower() for a in confirmed_authors} if confirmed_authors else set()
    unr_lower = {a.lower() for a in unready_authors} if unready_authors else set()

    for author, shas in result.author_map.items():
        status = "[dim]Pending[/dim]"
        if author.lower() in conf_lower:
            status = "[bold green]✅ Confirmed[/bold green]"
        elif author.lower() in unr_lower:
            status = "[bold red]❌ Unready[/bold red]"

        touched = result.author_files_map.get(author, set())
        touched_str = ", ".join(sorted(touched)) if touched else "[dim]None[/dim]"

        author_table.add_row(author, f"{len(shas)} commit(s)", status, touched_str)

    console.print(author_table)
    console.print()

    # Table 2: File-level Divergence
    file_table = Table(title="File-Level Divergences & Classification Plan", header_style="bold blue", expand=True)
    file_table.add_column("File Path", style="cyan")
    file_table.add_column("Changes (+/-)", justify="center")
    file_table.add_column("Contributing Authors")
    file_table.add_column("Classification Plan", justify="center")

    for f in result.files:
        diff_str = f"[green]+{f.insertions}[/green] / [red]-{f.deletions}[/red]"
        authors_str = ", ".join(sorted(f.authors))
        if f.classification == FileClassification.MIXED:
            class_str = "[bold yellow]Mixed (Requires Review)[/bold yellow]"
        elif f.classification == FileClassification.PURE_CONFIRMED:
            class_str = "[bold green]✅ Pure Confirmed (Preserve)[/bold green]"
        elif f.classification == FileClassification.PURE_UNREADY:
            class_str = "[bold red]❌ Pure Unready (Restore)[/bold red]"
        else:
            class_str = "[dim]Unclassified[/dim]"

        file_table.add_row(f.path, diff_str, authors_str, class_str)

    console.print(file_table)

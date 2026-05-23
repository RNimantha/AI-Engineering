"""
main.py
────────
CLI entry point for the Automated Clinical Trial Matcher MVP.

Usage:
    python main.py --input sample_data/sample_patient.txt
    python main.py --input /path/to/chart.pdf --output my_report.md
    python main.py --input chart.txt --output report.md --verbose

The CLI:
  1. Loads environment variables from .env
  2. Reads the chart file (.txt or .pdf)
  3. Runs the MasterOrchestrator pipeline
  4. Writes the Markdown report to disk
  5. Prints a Rich-formatted summary to the terminal
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

# Load .env before any other imports that might need env vars
load_dotenv()

from orchestrator.master import MasterOrchestrator
from utils.pdf_parser import read_chart, UnsupportedFileTypeError
from utils.logger import get_logger
from utils.state import PipelineState

console = Console()
logger = get_logger(__name__)


# ── CLI Definition ────────────────────────────────────────────────────────────

@click.command()
@click.option(
    "--input", "-i",
    "input_path",
    required=True,
    type=click.Path(exists=True, readable=True),
    help="Path to patient chart file (.txt or .pdf)",
)
@click.option(
    "--output", "-o",
    "output_path",
    default="report.md",
    show_default=True,
    help="Path for the output Markdown dossier",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Enable DEBUG logging",
)
def main(input_path: str, output_path: str, verbose: bool) -> None:
    """
    Automated Clinical Trial Matcher MVP

    Reads a patient chart, anonymizes it, queries ClinicalTrials.gov,
    evaluates eligibility, and writes a physician dossier to OUTPUT.
    """
    # ── Environment check ──
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print(
            Panel(
                "[bold red]ANTHROPIC_API_KEY not set.[/bold red]\n"
                "Copy .env.example → .env and add your key.",
                title="❌ Configuration Error",
                border_style="red",
            )
        )
        sys.exit(1)

    if verbose:
        os.environ["LOG_LEVEL"] = "DEBUG"

    # ── Banner ──
    console.print(
        Panel(
            "[bold cyan]Automated Clinical Trial Matcher MVP[/bold cyan]\n"
            f"[dim]Input:[/dim]  {input_path}\n"
            f"[dim]Output:[/dim] {output_path}",
            title="🏥 Clinical Trial Matcher",
            border_style="cyan",
        )
    )

    # ── Read chart ──
    try:
        console.print(f"\n📄 Reading chart: [bold]{input_path}[/bold]")
        raw_chart_text: str = read_chart(input_path)
        console.print(f"   [green]✓[/green] Loaded {len(raw_chart_text):,} characters")
    except FileNotFoundError as exc:
        console.print(f"[bold red]File not found:[/bold red] {exc}")
        sys.exit(1)
    except UnsupportedFileTypeError as exc:
        console.print(f"[bold red]Unsupported file type:[/bold red] {exc}")
        sys.exit(1)
    except RuntimeError as exc:
        console.print(f"[bold red]Failed to read file:[/bold red] {exc}")
        sys.exit(1)

    # ── Run pipeline ──
    console.print("\n🚀 Starting multi-agent pipeline...\n")

    with console.status("[bold green]Running agents...[/bold green]", spinner="dots") as status:
        status.update("[bold cyan]Subagent 1: Anonymizer — stripping PII...[/bold cyan]")
        orchestrator = MasterOrchestrator()

        try:
            state: PipelineState = orchestrator.run(raw_chart_text)
        except KeyboardInterrupt:
            console.print("\n[yellow]Pipeline interrupted by user.[/yellow]")
            sys.exit(130)
        except Exception as exc:
            console.print(f"\n[bold red]Fatal pipeline error:[/bold red] {exc}")
            logger.error(f"Fatal pipeline error: {exc}", exc_info=True)
            sys.exit(1)

    # ── Write report ──
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        output_file.write_text(state.report_markdown, encoding="utf-8")
        console.print(f"\n✅ Report written to: [bold green]{output_file.resolve()}[/bold green]")
    except OSError as exc:
        console.print(f"[bold red]Failed to write report:[/bold red] {exc}")
        sys.exit(1)

    # ── Print summary table ──
    _print_summary(state)

    # ── Exit with error code if fatal errors occurred ──
    if state.has_fatal_errors():
        console.print("\n[bold red]Pipeline completed with fatal errors. See logs.[/bold red]")
        sys.exit(2)
    elif state.errors:
        console.print(
            f"\n[yellow]Pipeline completed with {len(state.errors)} non-fatal error(s). "
            "See logs for details.[/yellow]"
        )


def _print_summary(state: PipelineState) -> None:
    """Print a Rich-formatted summary table to the terminal."""

    # ── Stats panel ──
    stats_table = Table(show_header=False, box=None, padding=(0, 2))
    stats_table.add_column("Metric", style="dim")
    stats_table.add_column("Value", style="bold")
    stats_table.add_row("Trials fetched", str(state.total_trials_fetched))
    stats_table.add_row("Trials evaluated", str(state.total_trials_evaluated))
    stats_table.add_row("✅ Eligible matches", f"[green]{len(state.verified_matches)}[/green]")
    stats_table.add_row("❌ Rejected", str(len(state.rejected_trials)))
    stats_table.add_row("⚠️  Pipeline errors", str(len(state.errors)))

    console.print(
        Panel(stats_table, title="📊 Pipeline Summary", border_style="green")
    )

    # ── Verified matches ──
    if state.verified_matches:
        matches_table = Table(
            title="✅ Eligible Trials",
            show_header=True,
            header_style="bold cyan",
        )
        matches_table.add_column("NCT ID", style="cyan", no_wrap=True)
        matches_table.add_column("Title", max_width=50)
        matches_table.add_column("Phase", justify="center")
        matches_table.add_column("Location", max_width=30)

        for match in state.verified_matches:
            matches_table.add_row(
                match.nct_id,
                match.official_title[:50] + ("..." if len(match.official_title) > 50 else ""),
                match.phase,
                match.primary_location[:30],
            )

        console.print(matches_table)

    else:
        console.print(
            Panel(
                "[yellow]No eligible trials found for this patient profile.[/yellow]\n"
                "See the generated report for details and recommendations.",
                border_style="yellow",
            )
        )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()

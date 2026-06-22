#!/usr/bin/env python3
"""
AI Code Reviewer — CLI Entry Point

Usage examples:
  python main.py review path/to/file.py
  python main.py review src/ --output reports/
  python main.py pr --owner myorg --repo myrepo --pr 42
  python main.py document path/to/file.py --write
"""

import os
import sys
from pathlib import Path

import click
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

load_dotenv()

console = Console()

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def load_config(config_path: str = "config/config.yaml") -> dict:
    path = Path(config_path)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _should_review(filename: str, cfg: dict) -> bool:
    filters = cfg.get("filters", {})
    include_exts = filters.get("include_extensions", [])
    if include_exts:
        _, ext = os.path.splitext(filename)
        if ext.lower() not in include_exts:
            return False
    exclude = filters.get("exclude_paths", [])
    for pattern in exclude:
        if Path(filename).match(pattern):
            return False
    return True


def _collect_files(paths: tuple[str, ...], cfg: dict) -> list[Path]:
    collected = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            for f in path.rglob("*"):
                if f.is_file() and _should_review(str(f), cfg):
                    collected.append(f)
        elif path.is_file():
            collected.append(path)
    return collected


def _print_result_table(result) -> None:
    from src.code_reviewer import Severity

    SEVERITY_COLOR = {
        Severity.CRITICAL: "red",
        Severity.HIGH: "orange3",
        Severity.MEDIUM: "yellow",
        Severity.LOW: "cyan",
        Severity.INFO: "white",
    }

    score_color = "green" if result.overall_score >= 80 else ("yellow" if result.overall_score >= 60 else "red")
    console.print(
        Panel(
            f"[bold]{result.filename}[/bold]  "
            f"Score: [{score_color}]{result.overall_score}/100[/{score_color}]  "
            f"Language: {result.language}\n{result.summary}",
            title="[bold blue]Review Result[/bold blue]",
        )
    )

    if result.comments:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Severity", style="bold", width=10)
        table.add_column("Category", width=14)
        table.add_column("Location", width=8)
        table.add_column("Message")
        for c in result.comments:
            color = SEVERITY_COLOR.get(c.severity, "white")
            table.add_row(
                f"[{color}]{c.severity.value}[/{color}]",
                c.category,
                f"L{c.line_range}" if c.line_range else "—",
                c.message,
            )
        console.print(table)

    if result.test_suggestions:
        console.print("\n[bold cyan]🧪 Test Suggestions:[/bold cyan]")
        for t in result.test_suggestions:
            console.print(f"  • {t}")

    if result.doc_suggestions:
        console.print("\n[bold yellow]📝 Documentation Gaps:[/bold yellow]")
        for d in result.doc_suggestions:
            console.print(f"  • {d}")


# ------------------------------------------------------------------
# CLI Commands
# ------------------------------------------------------------------

@click.group()
def cli():
    """🤖 AI Code Reviewer — Automate code review, testing & documentation."""


@cli.command()
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Directory to write reports to")
@click.option("--format", "fmt", default="both", type=click.Choice(["markdown", "json", "both"]))
@click.option("--config", "cfg_path", default="config/config.yaml")
@click.option("--fail-on-issues", is_flag=True, default=False, help="Exit with code 1 if issues found")
def review(paths, output, fmt, cfg_path, fail_on_issues):
    """Review local files or directories with AI."""
    from src.code_reviewer import AICodeReviewer
    from src.report_generator import render_markdown, render_json, save_report

    cfg = load_config(cfg_path)
    model = os.environ.get("OPENAI_MODEL", cfg.get("reviewer", {}).get("model", "gpt-4o"))
    reviewer = AICodeReviewer(model=model)
    files = _collect_files(paths, cfg)

    if not files:
        console.print("[yellow]No matching files found.[/yellow]")
        sys.exit(0)

    results = []
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Reviewing files…", total=len(files))
        for f in files:
            progress.update(task, description=f"Reviewing [cyan]{f.name}[/cyan]…")
            code = f.read_text(encoding="utf-8", errors="ignore")
            result = reviewer.review_code(code, str(f))
            results.append(result)
            progress.advance(task)

    for r in results:
        _print_result_table(r)

    # Save reports
    out_dir = output or cfg.get("output", {}).get("report_dir", "./reports")
    if fmt in ("markdown", "both"):
        md = render_markdown(results)
        save_report(md, f"{out_dir}/review_report.md")
        console.print(f"\n[green]✅ Markdown report saved:[/green] {out_dir}/review_report.md")
    if fmt in ("json", "both"):
        js = render_json(results)
        save_report(js, f"{out_dir}/review_report.json")
        console.print(f"[green]✅ JSON report saved:[/green] {out_dir}/review_report.json")

    if fail_on_issues and any(not r.passed for r in results):
        console.print("\n[red]❌ Review failed: high/critical issues detected.[/red]")
        sys.exit(1)


@cli.command()
@click.option("--owner", required=True, help="GitHub repository owner")
@click.option("--repo", required=True, help="GitHub repository name")
@click.option("--pr", "pr_number", required=True, type=int, help="Pull Request number")
@click.option("--post-comment/--no-post-comment", default=True, help="Post review to GitHub")
@click.option("--config", "cfg_path", default="config/config.yaml")
def pr(owner, repo, pr_number, post_comment, cfg_path):
    """Review a GitHub Pull Request and post AI feedback."""
    from src.code_reviewer import AICodeReviewer
    from src.github_integration import GitHubClient, build_review_markdown

    cfg = load_config(cfg_path)
    model = os.environ.get("OPENAI_MODEL", cfg.get("reviewer", {}).get("model", "gpt-4o"))
    reviewer = AICodeReviewer(model=model)
    gh = GitHubClient()

    console.print(f"[bold]Fetching PR #{pr_number}[/bold] from {owner}/{repo}…")
    pr_files = gh.get_pr_files(owner, repo, pr_number)
    commit_sha = gh.get_pr_head_sha(owner, repo, pr_number)

    if not pr_files:
        console.print("[yellow]No reviewable files found in this PR.[/yellow]")
        sys.exit(0)

    results = []
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Reviewing PR files…", total=len(pr_files))
        for pf in pr_files:
            if not _should_review(pf.filename, cfg):
                progress.advance(task)
                continue
            progress.update(task, description=f"Reviewing [cyan]{pf.filename}[/cyan]…")
            result = reviewer.review_diff(pf.patch, pf.filename)
            results.append(result)
            _print_result_table(result)
            progress.advance(task)

    if post_comment and results:
        review_body = build_review_markdown(results)
        block_on = cfg.get("thresholds", {}).get("block_on_severity", "high")
        has_blocking = any(
            c.severity.value in ("critical", "high")
            for r in results for c in r.comments
        )
        event = (
            cfg.get("github", {}).get("review_event", "REQUEST_CHANGES")
            if has_blocking else "COMMENT"
        )
        gh.post_review(owner, repo, pr_number, commit_sha, review_body, event=event)
        console.print(f"\n[green]✅ Review posted to PR #{pr_number} as {event}[/green]")


@cli.command()
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--write", is_flag=True, default=False, help="Overwrite files with documented versions")
@click.option("--output-dir", default=None, help="Directory to write documented copies")
@click.option("--config", "cfg_path", default="config/config.yaml")
def document(paths, write, output_dir, cfg_path):
    """Generate or improve docstrings/documentation for source files."""
    from src.doc_generator import DocGenerator

    cfg = load_config(cfg_path)
    model = os.environ.get("OPENAI_MODEL", cfg.get("reviewer", {}).get("model", "gpt-4o"))
    generator = DocGenerator(model=model)
    files = _collect_files(paths, cfg)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Generating docs…", total=len(files))
        for f in files:
            progress.update(task, description=f"Documenting [cyan]{f.name}[/cyan]…")
            code = f.read_text(encoding="utf-8", errors="ignore")
            result = generator.generate_docs(code, str(f))

            if write:
                f.write_text(result.documented_code, encoding="utf-8")
                console.print(f"[green]✅ Updated:[/green] {f}  (+{result.added_docstrings} docstrings)")
            elif output_dir:
                out = Path(output_dir) / f.name
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(result.documented_code, encoding="utf-8")
                console.print(f"[green]✅ Saved to:[/green] {out}  (+{result.added_docstrings} docstrings)")
            else:
                console.print(f"\n[bold]{f}[/bold]  (+{result.added_docstrings} docstrings)")
                console.print(result.documented_code)

            progress.advance(task)


if __name__ == "__main__":
    cli()

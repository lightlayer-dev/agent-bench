"""CLI entry point for agent-bench."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option()
def cli() -> None:
    """agent-bench — Benchmark how AI-agent-native a website is."""


@cli.command()
@click.argument("url")
@click.option("--checks", "-c", multiple=True, help="Specific checks to run (default: all)")
@click.option("--output", "-o", type=click.Path(), help="Output file for results")
@click.option("--format", "fmt", type=click.Choice(["json", "table", "markdown", "html"]), default="table")
@click.option("--threshold", "-t", type=float, default=None, help="Minimum score (0.0-1.0). Exit code 1 if below. For CI pipelines.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress human-readable output (useful with --output in CI)")
@click.option("--post", "post_url", type=str, default=None, help="POST results to a LightLayer Dashboard URL (e.g. http://localhost:8000)")
@click.option("--source", type=str, default="cli", help="Source label for dashboard (cli, ci, api)")
def analyze(url: str, checks: tuple[str, ...], output: str | None, fmt: str, threshold: float | None, quiet: bool, post_url: str | None, source: str) -> None:
    """Run static analysis on a website and produce an agent-readiness score.

    Use --threshold in CI to fail builds when agent-readiness drops:

      agent-bench analyze https://api.example.com --threshold 0.5 --output results.json

    Exit codes: 0 = pass (or no threshold), 1 = below threshold.
    """
    import sys

    from agent_bench.analysis.scorer import SiteScorer

    if not quiet:
        console.print(f"[bold]Analyzing[/bold] {url} ...\n")

    scorer = SiteScorer(url=url, checks=list(checks) if checks else None)
    report = scorer.run()

    if not quiet:
        console.print(report.render(fmt))

    if output:
        Path(output).write_text(report.to_json())
        if not quiet:
            console.print(f"\n[dim]Results saved to {output}[/dim]")

    if post_url:
        import json
        import urllib.request
        import urllib.error

        payload = json.loads(report.to_json())
        payload["source"] = source
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{post_url.rstrip('/')}/api/scans/",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                if not quiet:
                    console.print(f"\n[dim]Posted to dashboard → scan #{result.get('id', '?')}[/dim]")
        except urllib.error.URLError as e:
            console.print(f"\n[red]Failed to post to dashboard: {e}[/red]")

    if threshold is not None:
        if report.overall_score < threshold:
            console.print(
                f"\n[red bold]✗ FAIL[/red bold] — score {report.overall_score:.0%} is below threshold {threshold:.0%}"
            )
            sys.exit(1)
        else:
            if not quiet:
                console.print(
                    f"\n[green bold]✓ PASS[/green bold] — score {report.overall_score:.0%} meets threshold {threshold:.0%}"
                )


def _load_config_models() -> None:
    """Load config file and register any custom models."""
    from agent_bench.config import BenchConfig
    from agent_bench.models.registry import ModelRegistry

    config = BenchConfig.load()
    for model_cfg in config.models:
        ModelRegistry.register(model_cfg)


@cli.command()
@click.argument("task_file", type=click.Path(exists=True))
@click.option("--model", "-m", required=True, help="Model name from registry or config file")
@click.option("--adapter", "-a", default="browser-use", help="Agent adapter to use")
@click.option("--runs", "-n", default=3, help="Number of runs per task")
@click.option("--output-dir", "-o", type=click.Path(), default="results")
@click.option("--config", "-c", "config_path", type=click.Path(exists=True), default=None, help="Config file path")
def run(task_file: str, model: str, adapter: str, runs: int, output_dir: str, config_path: str | None) -> None:
    """Run live agent benchmarks against a website.

    Loads models from agent-bench.yaml (auto-discovered) or --config.
    Use 'agent-bench models' to see available models.
    """
    from agent_bench.config import BenchConfig
    from agent_bench.models.registry import ModelRegistry
    from agent_bench.runner.executor import BenchExecutor

    # Load config and register custom models
    config = BenchConfig.load(Path(config_path) if config_path else None)
    for model_cfg in config.models:
        ModelRegistry.register(model_cfg)

    console.print(f"[bold]Running[/bold] {task_file} × {model} × {adapter} ({runs} runs)\n")
    executor = BenchExecutor(
        task_file=Path(task_file),
        model_name=model,
        adapter_name=adapter,
        num_runs=runs,
        output_dir=Path(output_dir),
    )
    results = executor.execute()
    console.print(results.summary())


@cli.command()
@click.argument("url")
@click.option("--format", "fmt", type=click.Choice(["json", "table", "yaml"]), default="table")
def classify(url: str, fmt: str) -> None:
    """Classify a website and generate benchmark tasks for it."""
    from agent_bench.runner.classifier import SiteClassifier
    from agent_bench.runner.generator import generate_tasks

    classifier = SiteClassifier()
    profile = classifier.classify(url)

    console.print(f"[bold]Category:[/bold] {profile.category.value} ({profile.confidence:.0%} confidence)")
    console.print(f"[bold]Signals:[/bold] {', '.join(profile.signals[:5]) or 'none'}")
    console.print(f"[bold]Features:[/bold] {', '.join(k for k, v in profile.features.items() if v) or 'none'}")

    tasks = generate_tasks(profile)
    console.print(f"\n[bold]{len(tasks)} tasks generated:[/bold]\n")
    for task in tasks:
        console.print(f"  [{task.difficulty}] {task.name} — {task.description}")


@cli.command()
@click.option("--runs", "-r", multiple=True, type=click.Path(exists=True), help="Result files to compare (live runs)")
@click.option("--before", "-b", type=click.Path(exists=True), help="Before analysis result (static)")
@click.option("--after", "-a", type=click.Path(exists=True), help="After analysis result (static)")
@click.option("--format", "fmt", type=click.Choice(["json", "table", "markdown"]), default="table")
def compare(runs: tuple[str, ...], before: str | None, after: str | None, fmt: str) -> None:
    """Compare results across different runs or analysis snapshots.

    For live run comparison: --runs file1.json --runs file2.json
    For static analysis diff: --before old.json --after new.json
    """
    if before and after:
        from agent_bench.results.compare import compare_analyses

        comparison = compare_analyses(Path(before), Path(after))
        console.print(comparison.render(fmt))
    elif runs:
        from agent_bench.results.compare import compare_runs

        if len(runs) < 2:
            console.print("[red]Provide at least two result files to compare.[/red]")
            return
        comparison = compare_runs([Path(r) for r in runs])
        console.print(comparison.render(fmt))
    else:
        console.print("[red]Use --before/--after for analysis diffs, or --runs for live run comparison.[/red]")


@cli.command()
def models() -> None:
    """List available foundation models (built-in + config file)."""
    from agent_bench.models.registry import _BUILTIN_MODELS, _custom_models

    _load_config_models()

    console.print("[bold]Built-in models:[/bold]\n")
    for name in sorted(_BUILTIN_MODELS):
        cfg = _BUILTIN_MODELS[name]
        console.print(f"  {name:<20} {cfg.provider.value:<12} {cfg.model_id}")

    if _custom_models:
        console.print("\n[bold]From config:[/bold]\n")
        for name in sorted(_custom_models):
            cfg = _custom_models[name]
            console.print(f"  {name:<20} {cfg.provider.value:<12} {cfg.model_id}")


@cli.command()
@click.argument("urls", nargs=-1, required=False)
@click.option("--output-dir", "-o", type=click.Path(), default="benchmark-results", help="Directory for results")
@click.option("--format", "fmt", type=click.Choice(["json", "table", "markdown", "html"]), default="json")
@click.option("--threshold", "-t", type=float, default=None, help="Minimum overall score (0-100). Exit 1 if ANY site falls below.")
@click.option("--quiet", "-q", is_flag=True, help="Minimal output for CI pipelines")
@click.option("--post", "post_url", type=str, default=None, help="POST results to a LightLayer Dashboard URL")
@click.option("--source", type=str, default="cli", help="Source tag for dashboard submissions")
@click.option("--config", "config_path", type=click.Path(exists=True), default=None, help="Config file with sites list")
def batch(urls: tuple[str, ...], output_dir: str, fmt: str, threshold: float | None, quiet: bool, post_url: str | None, source: str, config_path: str | None) -> None:
    """Run static analysis on multiple websites.

    URLs can be passed as arguments or defined in agent-bench.yaml under 'sites'.
    If both are provided, they are combined.
    """
    from agent_bench.analysis.scorer import SiteScorer
    from agent_bench.config import BenchConfig
    import json as json_mod

    # Merge CLI URLs with config sites
    config = BenchConfig.load(Path(config_path) if config_path else None)
    site_entries: list[tuple[str, list[str] | None]] = []

    # Add config sites
    for site in config.sites:
        site_entries.append((str(site.url), site.checks))

    # Add CLI URLs (no per-site check overrides)
    for url in (urls or ()):
        site_entries.append((url, None))

    if not site_entries:
        console.print("[red]No URLs provided. Pass URLs as arguments or define 'sites' in agent-bench.yaml[/red]")
        raise SystemExit(1)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    failures: list[tuple[str, float]] = []

    for url, checks in site_entries:
        if not quiet:
            console.print(f"[bold]Analyzing[/bold] {url} ...")
        try:
            scorer = SiteScorer(url=url, checks=checks)
            report = scorer.run()
            data = json_mod.loads(report.to_json())
            results.append(data)

            # Save individual result
            slug = url.replace("https://", "").replace("http://", "").replace("/", "_").rstrip("_")
            (out / f"{slug}.json").write_text(json_mod.dumps(data, indent=2))

            score = data.get("overall_score", 0)
            if not quiet:
                console.print(f"  Score: {score}\n")
            else:
                console.print(f"{url} {score}")

            # Check threshold
            if threshold is not None and score < threshold:
                failures.append((url, score))

            # Post to dashboard
            if post_url:
                try:
                    import httpx

                    resp = httpx.post(
                        f"{post_url.rstrip('/')}/api/scans/",
                        json={**data, "source": source},
                        timeout=10,
                    )
                    resp.raise_for_status()
                    if not quiet:
                        console.print(f"  [green]Posted to dashboard[/green]")
                except Exception as e:
                    console.print(f"  [red]Failed to post: {e}[/red]")

        except Exception as e:
            console.print(f"  [red]Error: {e}[/red]\n" if not quiet else f"{url} ERROR: {e}")

    # Save summary
    (out / "summary.json").write_text(json_mod.dumps(results, indent=2))

    # Generate HTML leaderboard if requested
    if fmt == "html" and results:
        from agent_bench.analysis.leaderboard import render_leaderboard

        html = render_leaderboard(results)
        html_path = out / "leaderboard.html"
        html_path.write_text(html)
        if not quiet:
            console.print(f"\n[bold]Leaderboard:[/bold] {html_path}")

    if not quiet:
        console.print(f"\n[dim]Results saved to {output_dir}/ ({len(results)} sites)[/dim]")

    if failures:
        for url, score in failures:
            console.print(f"[red]FAIL[/red] {url}: {score} < {threshold}")
        raise SystemExit(1)


@cli.command()
@click.argument("result_files", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default="leaderboard.html", help="Output HTML file")
def leaderboard(result_files: tuple[str, ...], output: str) -> None:
    """Generate an HTML leaderboard from analysis result files."""
    from agent_bench.analysis.leaderboard import load_results, render_leaderboard

    results = load_results([Path(f) for f in result_files])
    html = render_leaderboard(results)
    Path(output).write_text(html)
    console.print(f"[bold]Leaderboard generated:[/bold] {output} ({len(results)} sites)")


if __name__ == "__main__":
    cli()

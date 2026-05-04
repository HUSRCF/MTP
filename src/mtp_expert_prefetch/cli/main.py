from __future__ import annotations

import typer

from mtp_expert_prefetch.data.material import fetch_text_material
from mtp_expert_prefetch.tracing.router_mtp import trace_router_mtp

app = typer.Typer(help="MTP expert prefetch research utilities.")


@app.command()
def version() -> None:
    """Print package version."""
    from mtp_expert_prefetch import __version__

    typer.echo(__version__)


@app.command("fetch-text-material")
def fetch_text_material_cmd(
    config: str = typer.Argument(..., help="Data config YAML."),
    output: str | None = typer.Option(None, "--output", "-o", help="Output JSONL path."),
) -> None:
    """Fetch or materialize text data into JSONL."""
    typer.echo(fetch_text_material(config, output))


@app.command("trace-router-mtp")
def trace_router_mtp_cmd(
    config: str = typer.Argument(..., help="Trace config YAML."),
) -> None:
    """Collect router/MTP traces from a frozen model."""
    typer.echo(trace_router_mtp(config))


if __name__ == "__main__":
    app()

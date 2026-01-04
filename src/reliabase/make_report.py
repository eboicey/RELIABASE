"""Asset report generator CLI placeholder."""
from __future__ import annotations

from pathlib import Path

import typer

from reliabase.analytics.reporting import generate_asset_report

app = typer.Typer(help="Generate reliability packet for an asset")


@app.command()
def main(asset_id: int, output_dir: Path = Path("./examples")):
    """Generate a PDF report for the given asset ID (placeholder)."""
    pdf_path = generate_asset_report(output_dir, {"asset_id": asset_id})
    typer.echo(f"Generated report at {pdf_path}")


if __name__ == "__main__":
    app()

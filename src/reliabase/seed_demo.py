"""Demo dataset generator CLI placeholder."""
from __future__ import annotations

import typer


app = typer.Typer(help="RELIABASE demo data seeding")


@app.command()
def main():
    """Generate a coherent demo dataset (placeholder)."""
    typer.echo("Demo dataset generation not yet implemented.")


if __name__ == "__main__":
    app()

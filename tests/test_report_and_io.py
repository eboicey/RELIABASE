from pathlib import Path

from sqlmodel import Session, select
from typer.testing import CliRunner

from reliabase.io import csv_io
from reliabase.make_report import app as report_app
from reliabase.models import Asset
from reliabase.seed_demo import seed_demo_dataset


def test_seed_demo_and_csv_export(session: Session, tmp_path: Path):
    seed_demo_dataset(session)
    count = session.exec(select(Asset)).all()
    assert len(count) > 0
    out_csv = tmp_path / "assets.csv"
    csv_io.export_table(session, Asset, out_csv)
    assert out_csv.exists()


def test_report_generation(tmp_path: Path, session: Session, monkeypatch):
    seed_demo_dataset(session)
    asset_id = session.exec(select(Asset.id)).first()
    output_dir = tmp_path / "report"
    runner = CliRunner()
    result = runner.invoke(report_app, ["--asset-id", str(asset_id), "--output-dir", str(output_dir)])
    assert result.exit_code == 0
    assert (output_dir / "asset_reliability_packet.pdf").exists()

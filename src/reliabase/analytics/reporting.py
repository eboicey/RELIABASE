"""PDF/plot reporting utilities."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Sequence

import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _plot_reliability(output_dir: Path, times: Sequence[float], reliability: Sequence[float], hazard: Sequence[float]) -> Path:
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(times, reliability, label="R(t)")
    ax[0].set_title("Reliability Curve")
    ax[0].set_xlabel("Time (hours)")
    ax[0].set_ylabel("Reliability")
    ax[0].grid(True)
    ax[1].plot(times, hazard, color="orange", label="h(t)")
    ax[1].set_title("Hazard Curve")
    ax[1].set_xlabel("Time (hours)")
    ax[1].set_ylabel("Hazard")
    ax[1].grid(True)
    plt.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "reliability_curves.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _plot_pareto(output_dir: Path, failure_counts: Dict[str, int]) -> Path:
    labels = list(failure_counts.keys())
    values = list(failure_counts.values())
    if not labels:
        labels = ["No failures"]
        values = [0]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, values, color="#3366cc")
    ax.set_title("Top Failure Modes (Pareto)")
    ax.set_ylabel("Count")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "failure_modes_pareto.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _plot_timeline(output_dir: Path, events: Sequence[Dict[str, Any]]) -> Path:
    if not events:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "event_timeline.png"
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.text(0.5, 0.5, "No events", ha="center", va="center")
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    fig, ax = plt.subplots(figsize=(8, 2.5))
    colors_map = {"failure": "red", "maintenance": "green", "inspection": "blue"}
    for idx, event in enumerate(events):
        ts = event["timestamp"]
        ax.scatter(ts, 0, color=colors_map.get(event["event_type"], "black"), label=event["event_type"] if idx == 0 else None)
    ax.get_yaxis().set_visible(False)
    ax.set_xlabel("Timestamp")
    fig.autofmt_xdate()
    ax.set_title("Event Timeline")
    plt.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "event_timeline.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _table(data: Sequence[Sequence[Any]], col_widths=None) -> Table:
    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ]
        )
    )
    return tbl


def generate_asset_report(output_dir: Path, context: Dict[str, Any]) -> Path:
    """Generate PDF packet plus PNG plots for an asset."""
    output_dir.mkdir(parents=True, exist_ok=True)

    asset = context.get("asset")
    metrics = context.get("metrics", {})
    weibull = context.get("weibull", {})
    curves = context.get("curves", {})
    events = context.get("events", [])
    failure_counts = context.get("failure_counts", {})

    reliability_plot = _plot_reliability(output_dir, curves.get("times", []), curves.get("reliability", []), curves.get("hazard", []))
    pareto_plot = _plot_pareto(output_dir, failure_counts)
    timeline_plot = _plot_timeline(output_dir, events)

    pdf_path = output_dir / "asset_reliability_packet.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Asset Reliability Packet: {asset.name if asset else ''}", styles["Title"]))
    story.append(Spacer(1, 12))

    kpi_rows = [
        ["Metric", "Value"],
        ["MTBF (hours)", f"{metrics.get('mtbf_hours', 0):.2f}"],
        ["MTTR (hours)", f"{metrics.get('mttr_hours', 0):.2f}"],
        ["Availability", f"{metrics.get('availability', 0):.3f}"],
    ]
    story.append(_table(kpi_rows, col_widths=[200, 200]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Weibull Fit (2-parameter)", styles["Heading2"]))
    story.append(
        Paragraph(
            f"Shape (beta): {weibull.get('shape', 0):.3f} (CI {weibull.get('shape_ci', (0, 0))})",
            styles["Normal"],
        )
    )
    story.append(
        Paragraph(
            f"Scale (eta): {weibull.get('scale', 0):.3f} (CI {weibull.get('scale_ci', (0, 0))})",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 8))

    story.append(Image(str(reliability_plot), width=400, height=180))
    story.append(Spacer(1, 8))
    story.append(Image(str(pareto_plot), width=400, height=200))
    story.append(Spacer(1, 8))
    story.append(Image(str(timeline_plot), width=400, height=120))
    story.append(Spacer(1, 12))

    event_rows = [["Timestamp", "Type", "Downtime (min)", "Description"]]
    for e in events:
        ts = e.get("timestamp")
        ts_str = ts.strftime("%Y-%m-%d %H:%M") if isinstance(ts, datetime) else str(ts)
        event_rows.append([ts_str, e.get("event_type"), f"{e.get('downtime_minutes', 0):.1f}", e.get("description", "")])
    story.append(Paragraph("Event Timeline", styles["Heading2"]))
    story.append(_table(event_rows, col_widths=[140, 80, 100, 200]))

    doc.build(story)
    return pdf_path

# RELIABASE — Reliability Engineering Tracking & Analysis

Local-first reliability database + analytics engine for assets, events, exposures, and parts. Outputs MTBF/MTTR, availability, Weibull fits, reliability curves, and produces exportable reports (PDF/CSV).

## Stack
- Python 3.11+
- FastAPI (API + minimal UI)
- SQLModel + SQLite
- Pandas / NumPy / SciPy
- Matplotlib (plots)
- ReportLab (PDF)
- Pytest

## Data model (minimum)
- Asset (id, name, type, serial, in_service_date, notes)
- ExposureLog (asset_id, start_time, end_time, hours, cycles)
- Event (asset_id, timestamp, event_type: failure/maintenance/inspection, downtime_minutes, description)
- FailureMode (name, category)
- EventFailureDetail (event_id, failure_mode_id, root_cause, corrective_action, part_replaced)
- Part (name, part_number)
- PartInstall (asset_id, part_id, install_time, remove_time)

## Planned capabilities
- CRUD for assets, exposures, events, failure modes, parts
- MTBF / MTTR / Availability (MTBF / (MTBF + MTTR))
- Weibull analysis (2-parameter MLE, bootstrap CIs, reliability/hazard curves, right-censoring aware)
- Reports: KPI summary, Weibull plots, Pareto of failure modes, event timeline
- Import/export CSV for core tables and KPIs
- Demo dataset generator: `python -m reliabase.seed_demo`
- Report generator: `python -m reliabase.make_report --asset_id X`

## Quickstart (development)
1) Create virtualenv and install deps:
   ```bash
   python -m venv .venv
   .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2) Run API:
   ```bash
   uvicorn reliabase.api.main:app --reload
   ```
3) Run tests:
   ```bash
   pytest
   ```

## Repo layout
- `src/reliabase/` — package code (models, API, analytics, IO, CLI)
- `tests/` — pytest suite (to be expanded)
- `examples/` — sample outputs (PDF/CSV/plots) to be generated

## Current status
- Core models, CRUD API routers (assets, exposures, events, failure modes, parts, installs)
- KPI calculations (MTBF/MTTR/availability) using exposure logs with right-censor handling
- Weibull fit with right-censoring + bootstrap CIs; reliability and hazard curves
- CSV import/export helpers; demo data seeder CLI; report generator CLI producing PDF + plots
- Smoke, API, analytics, and report/io pytest coverage (early stage)

## Usage
1) Seed demo data:
   ```bash
   python -m reliabase.seed_demo
   ```
2) Run API for CRUD:
   ```bash
   uvicorn reliabase.api.main:app --reload
   ```
3) Generate a report for asset id 1:
   ```bash
   python -m reliabase.make_report --asset-id 1 --output-dir ./examples
   ```
4) Export tables to CSV (example):
   ```python
   from sqlmodel import Session
   from reliabase.config import get_engine
   from reliabase.io import csv_io
   from reliabase.models import Asset

   with Session(get_engine()) as s:
       csv_io.export_table(s, Asset, Path("./examples/assets.csv"))
   ```

## Next steps
- Add more validation/business rules (e.g., non-overlapping exposures, part install lifecycle checks)
- Expand tests toward 30+ coverage and add CI workflow
- Add minimal UI views and richer audit logging

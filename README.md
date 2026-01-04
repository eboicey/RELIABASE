# RELIABASE — Reliability Engineering Tracking & Analysis

Local-first reliability database + analytics engine for assets, events, exposures, and parts. Outputs MTBF/MTTR, availability, Weibull fits, reliability curves, and produces exportable reports (PDF/CSV).

## Stack
- Python 3.11+
- FastAPI (API + minimal UI)
- SQLModel + SQLite (local-first)
- Pandas / NumPy / SciPy
- Matplotlib (plots)
- ReportLab (PDF)
- Pytest

## Architecture (high level)
```mermaid
flowchart TD
   client[FastAPI routes / CLI] --> api[(Routers)]
   api --> models[SQLModel ORM]
   models --> db[(SQLite)]
   api --> analytics[Analytics: MTBF/MTTR/Weibull]
   analytics --> reporting[Reporting (plots + PDF)]
   api --> csv[CSV Import/Export]
   seed[seed_demo CLI] --> db
   reporting --> outputs[/examples]
```

## Data model (minimum)
- Asset (id, name, type, serial, in_service_date, notes)
- ExposureLog (asset_id, start_time, end_time, hours, cycles)
- Event (asset_id, timestamp, event_type: failure/maintenance/inspection, downtime_minutes, description)
- FailureMode (name, category)
- EventFailureDetail (event_id, failure_mode_id, root_cause, corrective_action, part_replaced)
- Part (name, part_number)
- PartInstall (asset_id, part_id, install_time, remove_time)

## Capabilities
- CRUD for assets, exposures, events, failure modes, parts, installs
- MTBF / MTTR / Availability (censor-aware using exposure logs and downtime minutes)
- Weibull analysis (2-parameter MLE, bootstrap CIs, reliability/hazard curves, right-censoring aware)
- Reports: KPI summary, Weibull plots, Pareto of failure modes, event timeline (PDF + PNG)
- Import/export CSV for core tables + KPIs
- Demo dataset generator: `python -m reliabase.seed_demo`
- Report generator: `python -m reliabase.make_report --asset-id X --output-dir examples`

## Formulas (assumptions)
- MTBF: $\text{MTBF} = \frac{\sum \text{operating hours between failures}}{N_\text{fail}}$
- MTTR: $\text{MTTR} = \frac{\sum \text{downtime minutes}}{60\,N_\text{fail}}$
- Availability: $A = \frac{\text{MTBF}}{\text{MTBF} + \text{MTTR}}$
- Weibull (2-parameter): $f(t)=\frac{\beta}{\eta}\left(\frac{t}{\eta}\right)^{\beta-1} e^{-(t/\eta)^\beta}$ with shape $\beta$ and scale $\eta$; right-censored handled in log-likelihood; CIs via bootstrap (N=1000).

## Quickstart (development)
1) Create virtualenv and install deps:
   ```bash
   python -m venv .venv
   .venv/Scripts/Activate.ps1  # PowerShell
   pip install -r requirements.txt
   ```
2) Seed demo data:
   ```bash
   python -m reliabase.seed_demo
   ```
       (or hit `POST /demo/seed` with JSON `{ "reset": true }` if running the API)
3) Generate a sample report (creates PDF + PNGs in ./examples):
   ```bash
   python -m reliabase.make_report --asset-id 1 --output-dir ./examples
   ```
4) Run API:
   ```bash
   uvicorn reliabase.api.main:app --reload
   ```
5) Run tests (currently 30 passing):
   ```bash
   pytest
   ```

## Repo layout
- `src/reliabase/` — package code (models, API, analytics, IO, CLI)
- `tests/` — pytest suite (30 tests covering CRUD, analytics, CSV, report)
- `examples/` — generated outputs (PDF/CSV/plots) from demo run

## Current status
- Core models, CRUD API routers (assets, exposures, events, failure modes, parts, installs)
- KPI calculations (MTBF/MTTR/availability) using exposure logs with right-censor handling
- Weibull fit with right-censoring + bootstrap CIs; reliability and hazard curves
- CSV import/export helpers; demo data seeder CLI; report generator CLI producing PDF + plots
- Example artifacts generated in `examples/` (PDF + PNG plots + CSV exports)
- Tests: 30 passing (API, analytics, CSV, report)

## Usage
- Seed + report (end-to-end demo):
  ```bash
  python -m reliabase.seed_demo
  python -m reliabase.make_report --asset-id 1 --output-dir ./examples
  ```
- Run API for CRUD:
  ```bash
  uvicorn reliabase.api.main:app --reload
  ```
   Optional: override CORS origins with `RELIABASE_CORS_ORIGINS` (comma-separated list) for the frontend.
- Export tables to CSV (example):
  ```python
  from pathlib import Path
  from sqlmodel import Session
  from reliabase.config import get_engine
  from reliabase.io import csv_io
  from reliabase.models import Asset

  with Session(get_engine()) as s:
      csv_io.export_table(s, Asset, Path("./examples/assets.csv"))
  ```

## Next steps
- Polish validation/audit trails; optional minimal UI surfaces
- Consider CI workflow + linting
- Improve warning silencing (SQLModel deprecations, SciPy runtime warnings)

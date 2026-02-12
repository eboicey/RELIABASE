# RELIABASE — Reliability Engineering Tracking & Analysis

<p align="center">
  <strong>Local-first reliability database + analytics engine for assets, events, exposures, and parts.</strong><br>
  Outputs MTBF/MTTR, availability, Weibull fits, reliability curves, and produces exportable reports (PDF/CSV).
</p>

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/eboicey/RELIABASE.git
cd RELIABASE

# Create and activate Python virtual environment
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1

# macOS/Linux:
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Running the Application (Streamlit)

```bash
streamlit run streamlit_app/Home.py
```

The app will open in your browser at **http://localhost:8501**

### First-Time Setup: Seed Demo Data

1. Open the app in your browser
2. Navigate to **Operations** in the sidebar
3. Click **"🌱 Seed Demo Data"** button

Or via CLI:
```bash
python -m reliabase.seed_demo
```

### Generate a Reliability Report

```bash
python -m reliabase.make_report --asset-id 1 --output-dir ./examples
```
This creates a PDF report + PNG charts in the `examples/` folder.

---

## 📚 Stack

| Layer | Technology |
|-------|-----------|
| **UI** | Streamlit 1.31+ |
| **Backend** | Python 3.11+, SQLModel, SQLite |
| **Analytics** | Pandas, NumPy, SciPy (Weibull MLE) |
| **Reporting** | Matplotlib (plots), ReportLab (PDF) |
| **Testing** | Pytest (30+ tests) |

---

## 🏗️ Architecture

The architecture is designed to scale from Streamlit to a full API + custom frontend:

```
RELIABASE/
├── src/reliabase/
│   ├── services/        # ← Business logic (used by both Streamlit & API)
│   ├── api/             # FastAPI endpoints (for future scaling)
│   ├── analytics/       # MTBF, MTTR, Weibull calculations
│   └── models.py        # SQLModel definitions
├── streamlit_app/       # ← Current UI
│   ├── Home.py          # Dashboard
│   └── pages/           # Feature pages
└── frontend/            # React UI (for future scaling)
```

**Scaling Path:**
1. **Now**: Streamlit for quick iteration and user testing
2. **Later**: FastAPI backend + React frontend for production scale
3. **Services layer** is shared, making migration seamless

---

## 📊 Data Model

| Entity | Key Fields |
|--------|-----------|
| **Asset** | id, name, type, serial, in_service_date, notes |
| **ExposureLog** | asset_id, start_time, end_time, hours, cycles |
| **Event** | asset_id, timestamp, event_type (failure/maintenance/inspection), downtime_minutes, description |
| **FailureMode** | name, category |
| **EventFailureDetail** | event_id, failure_mode_id, root_cause, corrective_action, part_replaced |
| **Part** | name, part_number |
| **PartInstall** | asset_id, part_id, install_time, remove_time |

---

## ✨ Features

### Core Functionality
- ✅ Full CRUD for assets, exposures, events, failure modes, parts, and installs
- ✅ Real-time dashboard with KPI cards and recent events table
- ✅ Asset filtering across all analytics views

### Analytics
- ✅ **MTBF** (Mean Time Between Failures) — censor-aware calculation
- ✅ **MTTR** (Mean Time To Repair) — from downtime minutes
- ✅ **Availability** — computed from MTBF and MTTR
- ✅ **Weibull Analysis** — 2-parameter MLE with bootstrap confidence intervals
- ✅ **Reliability & Hazard Curves** — visual plots with right-censoring support
- ✅ **Failure Mode Pareto** — ranked failure causes

### Reporting & Export
- ✅ PDF reliability packet with KPI summary, plots, and event timeline
- ✅ CSV export for all tables (via UI)
- ✅ PNG chart exports (Weibull curves, Pareto, timeline)

---

## 📐 Formulas

| Metric | Formula |
|--------|---------|
| **MTBF** | Total operating hours ÷ Number of failures |
| **MTTR** | Total downtime (hours) ÷ Number of failures |
| **Availability** | MTBF ÷ (MTBF + MTTR) |
| **Weibull PDF** | f(t) = (β/η)(t/η)^(β-1) × e^(-(t/η)^β) |

Where β = shape parameter, η = scale parameter. Right-censored observations handled in MLE. Confidence intervals via bootstrap (N=1000 resamples).

---

## 🗂️ Project Structure

```
RELIABASE/
├── src/reliabase/           # Python package
│   ├── services/            # Business logic (shared by UI & API)
│   ├── api/                 # FastAPI routers (for scaling)
│   ├── analytics/           # MTBF, MTTR, Weibull calculations
│   ├── io/                  # CSV import/export
│   ├── models.py            # SQLModel definitions
│   ├── config.py            # Database configuration
│   ├── seed_demo.py         # Demo data generator
│   └── make_report.py       # PDF report generator
├── streamlit_app/           # Streamlit UI (current)
│   ├── Home.py              # Dashboard entry point
│   └── pages/               # Feature pages
├── frontend/                # React application (for scaling)
│   └── src/                 # React components
├── tests/                   # Pytest test suite
├── examples/                # Generated reports & exports
├── requirements.txt         # Python dependencies
└── pyproject.toml           # Python package metadata
```

---

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_analytics.py
```

---

## 🔌 API Mode (For Scaling)

When ready to scale beyond Streamlit, use the FastAPI backend:

```bash
uvicorn reliabase.api.main:app --host 127.0.0.1 --port 8000 --reload
```

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/health` | GET | Health check |
| `/assets/` | GET, POST | List/create assets |
| `/assets/{id}` | GET, PATCH, DELETE | Asset CRUD |
| `/exposures/` | GET, POST | List/create exposure logs |
| `/events/` | GET, POST | List/create events |
| `/failure-modes/` | GET, POST | List/create failure modes |
| `/event-details/` | GET, POST | List/create event failure details |
| `/parts/` | GET, POST | List/create parts |
| `/parts/{id}/installs` | GET, POST | Part installation history |
| `/demo/seed` | POST | Seed demo data (reset optional) |

Full API docs available at **http://localhost:8000/docs** when backend is running.

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RELIABASE_DB` | `./reliabase.sqlite` | SQLite database file path |
| `RELIABASE_DATABASE_URL` | `sqlite:///./reliabase.sqlite` | Full database URL (use PostgreSQL for production) |
| `RELIABASE_ECHO_SQL` | `false` | Log SQL queries |

---

## 🚀 Deployment

### Streamlit Cloud (Quick Demo)
1. Push to GitHub
2. Connect to [Streamlit Cloud](https://streamlit.io/cloud)
3. Set entry point to `streamlit_app/Home.py`

### Production (Docker + PostgreSQL)
1. Set `RELIABASE_DATABASE_URL` to PostgreSQL connection string
2. Use the FastAPI backend + custom frontend
3. Services layer works identically with any database

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/), [FastAPI](https://fastapi.tiangolo.com/), and [SQLModel](https://sqlmodel.tiangolo.com/)
- Weibull analysis powered by [SciPy](https://scipy.org/)
- Designed for scalability from prototype to production

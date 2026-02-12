# RELIABASE Deployment Guide

Complete instructions for running RELIABASE locally and deploying to Streamlit Cloud or Docker.

---

## 1. Local Development

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python      | 3.11+   |
| pip         | latest  |
| Git         | any     |

### Setup

```bash
# Clone the repository
git clone https://github.com/eboicey/RELIABASE.git
cd RELIABASE

# Create a virtual environment
python -m venv .venv

# Activate – Windows PowerShell
.venv\Scripts\Activate.ps1

# Activate – macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run the App

```bash
streamlit run streamlit_app/Home.py
```

The app opens at **http://localhost:8501**.

On first launch the database (`reliabase.sqlite`) is created automatically.
Navigate to **Operations** and click **Seed Demo Data** to populate sample records.

### Run Tests

```bash
pytest -v
```

### Generate a PDF Reliability Report

```bash
python -m reliabase.make_report --asset-id 1 --output-dir ./examples
```

---

## 2. Streamlit Community Cloud

Streamlit Cloud is the fastest way to share a public demo. Free tier is fine for most uses.

### Step-by-Step

1. **Push your repo** to a public (or private) GitHub repository.

2. **Create a `packages.txt`** (only if you need OS-level system dependencies —
   RELIABASE currently does not).

3. **Verify `requirements.txt`** exists at the project root with all Python deps.
   Streamlit Cloud reads this automatically.

4. **Go to** [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.

5. **New app → fill in:**

   | Field            | Value                          |
   |------------------|--------------------------------|
   | Repository       | `eboicey/RELIABASE`            |
   | Branch           | `main`                         |
   | Main file path   | `streamlit_app/Home.py`        |

6. **Advanced settings (optional)**

   Add secrets or env vars:

   ```
   RELIABASE_DATABASE_URL = "sqlite:///./reliabase.sqlite"
   ```

   > **Note:** Streamlit Cloud provides an ephemeral filesystem. The SQLite
   > database resets on every deploy/reboot. For persistent data, use a managed
   > PostgreSQL database (see Section 4).

7. Click **Deploy**.  The app is live within a few minutes.

### Streamlit Cloud File Layout

```
RELIABASE/
├── .streamlit/
│   └── config.toml          # Theme & layout settings (included)
├── requirements.txt         # Auto-installed by Cloud
├── streamlit_app/
│   ├── Home.py              # ← entry point
│   ├── _common.py
│   └── pages/
│       ├── 1_Assets.py
│       ├── 2_Exposures.py
│       ├── ...
│       └── 8_Operations.py
└── src/reliabase/           # Backend code
```

---

## 3. Docker

Use Docker when you need a reproducible, portable deployment.

### Dockerfile

Create a `Dockerfile` in the project root:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install OS deps (none required currently)
# RUN apt-get update && apt-get install -y --no-install-recommends <pkg> && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "streamlit_app/Home.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.headless=true"]
```

### Build & Run

```bash
docker build -t reliabase .
docker run -p 8501:8501 reliabase
```

Open **http://localhost:8501**.

### Docker Compose (with PostgreSQL)

Create a `docker-compose.yml`:

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: reliabase
      POSTGRES_PASSWORD: changeme
      POSTGRES_DB: reliabase
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  app:
    build: .
    ports:
      - "8501:8501"
    environment:
      RELIABASE_DATABASE_URL: postgresql://reliabase:changeme@db:5432/reliabase
    depends_on:
      - db

volumes:
  pgdata:
```

```bash
docker compose up --build
```

---

## 4. PostgreSQL (Persistent Data)

By default RELIABASE uses a local SQLite file. To switch to PostgreSQL:

1. **Set the environment variable** before launching:

   ```bash
   # Linux / macOS
   export RELIABASE_DATABASE_URL="postgresql://user:password@host:5432/reliabase"

   # Windows PowerShell
   $env:RELIABASE_DATABASE_URL = "postgresql://user:password@host:5432/reliabase"
   ```

2. **Install the PostgreSQL driver** (already handled if you use `psycopg2-binary`):

   ```bash
   pip install psycopg2-binary
   ```

3. **Run the app** — tables are created automatically on first launch.

Recommended managed PostgreSQL providers:
- [Supabase](https://supabase.com) (free tier)
- [Neon](https://neon.tech) (free tier, serverless)
- [Railway](https://railway.app)
- [Render](https://render.com/docs/databases)

---

## 5. Environment Variables Reference

| Variable                | Default                          | Description                       |
|-------------------------|----------------------------------|-----------------------------------|
| `RELIABASE_DB`          | `./reliabase.sqlite`             | SQLite file path                  |
| `RELIABASE_DATABASE_URL`| `sqlite:///./reliabase.sqlite`   | Full DB URL (PostgreSQL, etc.)    |
| `RELIABASE_ECHO_SQL`    | `false`                          | Log all SQL to console            |

---

## 6. Custom Domain & Scaling

When RELIABASE outgrows Streamlit:

1. **API mode** — the FastAPI backend is production-ready:

   ```bash
   uvicorn reliabase.api.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

2. **Custom frontend** — React app in `frontend/` already scaffolded.

3. **Services layer** (`src/reliabase/services/`) is shared by both UIs,
   so all business logic migrates without changes.

4. **Reverse proxy** — put Nginx or Caddy in front for HTTPS + custom domain.

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| `ModuleNotFoundError: No module named 'reliabase'` | Make sure you're running from the project root, or that `src/` is on `PYTHONPATH`. |
| Streamlit Cloud: data resets on deploy | SQLite is ephemeral on Cloud. Use PostgreSQL (Section 4). |
| Port 8501 already in use | `streamlit run streamlit_app/Home.py --server.port 8502` |
| Slow first load | The database and tables are created on the first request. Subsequent loads are faster. |

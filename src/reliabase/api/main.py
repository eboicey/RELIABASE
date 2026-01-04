"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI

from reliabase.config import init_db
from reliabase.api.routers import assets, exposures, events, failure_modes, event_details, parts

app = FastAPI(title="RELIABASE", version="0.1.0")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(assets.router)
app.include_router(exposures.router)
app.include_router(events.router)
app.include_router(failure_modes.router)
app.include_router(event_details.router)
app.include_router(parts.router)


def get_app() -> FastAPI:
    """Return configured FastAPI app (useful for testing)."""
    return app


def run():
    """Convenience launcher for `python -m reliabase.api.main`."""
    import uvicorn

    uvicorn.run("reliabase.api.main:app", host="0.0.0.0", port=8000, reload=True)

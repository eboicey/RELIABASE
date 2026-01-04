"""FastAPI application entrypoint."""
from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from reliabase.config import init_db
from reliabase.api.routers import assets, exposures, events, failure_modes, event_details, parts, demo

app = FastAPI(title="RELIABASE", version="0.1.0")

cors_origins = os.getenv(
    "RELIABASE_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
).split(",")
allowed_origins = [origin.strip() for origin in cors_origins if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
app.include_router(demo.router)


def get_app() -> FastAPI:
    """Return configured FastAPI app (useful for testing)."""
    return app


def run():
    """Convenience launcher for `python -m reliabase.api.main`."""
    import uvicorn

    uvicorn.run("reliabase.api.main:app", host="0.0.0.0", port=8000, reload=True)

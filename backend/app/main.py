"""FastAPI application entrypoint for the IIoT Monitoring Platform.

Run from backend/:
    uvicorn app.main:app --reload --port 8000

Swagger UI: http://localhost:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_TITLE, API_VERSION, CORS_ORIGINS
from app.api.routers import health, machines, readings, tags

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=(
        "Read-only monitoring API over the MetroPT-3 industrial time-series data "
        "stored in PostgreSQL + TimescaleDB. Serves machines, tags, latest values, "
        "downsampled trends and statistics to the React dashboard. "
        "The React app talks ONLY to this API — never directly to the database."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(machines.router)
app.include_router(tags.router)
app.include_router(readings.router)


@app.get("/", tags=["health"], summary="Service banner")
def root() -> dict:
    return {
        "service": API_TITLE,
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }

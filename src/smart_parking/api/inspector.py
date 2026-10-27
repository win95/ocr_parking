"""Pipeline Inspector HTTP API (real metrics from INSPECTOR_STORE)."""

from __future__ import annotations

from pathlib import Path

from smart_parking.pipeline.observability import INSPECTOR_STORE

_HTML = Path(__file__).resolve().parent / "static" / "inspector.html"


def create_app():
    try:
        from fastapi import FastAPI
        from fastapi.responses import FileResponse, JSONResponse
    except ImportError as exc:
        raise RuntimeError("fastapi required: pip install fastapi uvicorn") from exc

    app = FastAPI(title="Smart Parking Pipeline Inspector")

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    @app.get("/api/state")
    def state() -> JSONResponse:
        return JSONResponse(INSPECTOR_STORE.to_dict())

    @app.get("/api/metrics")
    def metrics() -> JSONResponse:
        data = INSPECTOR_STORE.to_dict()
        return JSONResponse(data.get("metrics") or {})

    @app.get("/api/alerts")
    def alerts() -> JSONResponse:
        return JSONResponse({"alerts": INSPECTOR_STORE.alerts()})

    @app.get("/api/system")
    def system() -> JSONResponse:
        from smart_parking.pipeline.system_stats import system_snapshot

        return JSONResponse(system_snapshot())

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(_HTML)

    return app


def run_inspector(host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port, log_level="info")

"""Pipeline Inspector HTTP API (real metrics from INSPECTOR_REGISTRY)."""

from __future__ import annotations

from pathlib import Path

from smart_parking.pipeline.observability import INSPECTOR_REGISTRY

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

    @app.get("/api/cameras")
    def cameras() -> JSONResponse:
        return JSONResponse({"cameras": INSPECTOR_REGISTRY.list_cameras()})

    @app.get("/api/state")
    def state(camera_id: str | None = None) -> JSONResponse:
        return JSONResponse(INSPECTOR_REGISTRY.to_dict(camera_id=camera_id))

    @app.get("/api/metrics")
    def metrics(camera_id: str | None = None) -> JSONResponse:
        data = INSPECTOR_REGISTRY.to_dict(camera_id=camera_id)
        return JSONResponse(data.get("metrics") or {})

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(_HTML)

    return app


def run_inspector(host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port, log_level="info")

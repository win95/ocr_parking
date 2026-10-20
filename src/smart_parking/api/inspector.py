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

    def _client_ok(request) -> bool:
        host = getattr(request.client, "host", None)
        return host in ("127.0.0.1", "::1", "localhost")

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    @app.get("/api/state")
    def state(request) -> JSONResponse:
        if not _client_ok(request):
            return JSONResponse({"error": "forbidden"}, status_code=403)
        return JSONResponse(INSPECTOR_STORE.to_dict())

    @app.get("/api/metrics")
    def metrics(request) -> JSONResponse:
        if not _client_ok(request):
            return JSONResponse({"error": "forbidden"}, status_code=403)
        data = INSPECTOR_STORE.to_dict()
        return JSONResponse(data.get("metrics") or {})

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(_HTML)

    return app


def run_inspector(host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port, log_level="info")

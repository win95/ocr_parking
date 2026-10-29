"""Pipeline Inspector HTTP API (real metrics from INSPECTOR_REGISTRY)."""

from __future__ import annotations

import ipaddress
import secrets
from pathlib import Path

from smart_parking.config import InspectorConfig
from smart_parking.pipeline.observability import INSPECTOR_REGISTRY

_HTML = Path(__file__).resolve().parent / "static" / "inspector.html"
_PUBLIC_PATHS = {"/", "/api/health"}


def _client_ip(host: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    if not host:
        return None
    try:
        return ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        return None


def _client_allowed(
    client_ip: ipaddress.IPv4Address | ipaddress.IPv6Address | None,
    cfg: InspectorConfig,
) -> bool:
    if client_ip is None:
        return False
    if client_ip.is_loopback:
        return True
    for network in cfg.allow_networks:
        try:
            if client_ip in ipaddress.ip_network(network, strict=False):
                return True
        except (TypeError, ValueError):
            continue
    return False


def _token_valid(request, cfg: InspectorConfig) -> bool:
    if not cfg.api_token:
        return True
    supplied = request.headers.get("x-api-token") or ""
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        supplied = auth[7:].strip()
    return bool(supplied) and secrets.compare_digest(supplied, cfg.api_token)


def create_app(cfg: InspectorConfig | None = None):
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import FileResponse, JSONResponse
    except ImportError as exc:
        raise RuntimeError("fastapi required: pip install fastapi uvicorn") from exc

    settings = cfg or InspectorConfig()
    app = FastAPI(title="Smart Parking Pipeline Inspector")

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)
        client = _client_ip(request.client.host if request.client else None)
        if not _client_allowed(client, settings):
            return JSONResponse(
                status_code=403,
                content={"detail": "forbidden: client not in allow_networks"},
            )
        if not _token_valid(request, settings):
            return JSONResponse(
                status_code=401,
                content={"detail": "unauthorized: missing or invalid API token"},
            )
        return await call_next(request)

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


def run_inspector(cfg: InspectorConfig) -> None:
    import uvicorn

    uvicorn.run(create_app(cfg), host=cfg.host, port=cfg.port, log_level="info")

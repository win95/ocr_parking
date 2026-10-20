# Kiến trúc pipeline modular

## Hiện trạng (sau refactor)

| Tầng | Module | Chạy độc lập |
|------|--------|----------------|
| Ingest | `ingest/sources.py`, `frame_loop.py` | Có |
| DETR-R50-DC5 | `detection/detr_r50.py` | Có (`pipeline.layers.detr`) |
| YOLO11 | `detection/yolo_ultralytics.py` | Có (`pipeline.layers.yolo`) |
| Fusion | `detection/fusion.py` | Cần cả hai model nếu bật fusion |
| Tracking | `tracking/mot.py` | Có |
| Occupancy | `occupancy/engine.py` | Có |
| Analytics | `analytics/kpi_engine.py` | Có |
| Overlay OpenCV | `ui/overlay.py` | Có |
| Minimap | `ui/minimap_3d.py` | Có (`SlotStateContract`) |
| API Inspector | `api/inspector.py` | `python -m smart_parking --inspector-only` |

Điều phối: `pipeline/runner.py` (`ModularPipeline`).

Hợp đồng dữ liệu: `contracts.py` (schema v1).

Quan sát: `pipeline/observability.py` — correlation ID, log JSON, `INSPECTOR_STORE`.

Artifact replay: `replay/store.py` khi `artifacts.enabled`.

## Luồng dữ liệu

```
Ingest → PipelineFrame → [DETR] [YOLO] → Fusion? → Tracking → Occupancy → Overlay / Minimap
                              ↓           ↓
                         detr_batch   yolo_batch → fused_batch
```

## Chế độ

- `configs/default.yaml` — bình thường
- `configs/modes/debug.yaml` — artifact + inspector + minimap
- `configs/modes/benchmark.yaml` — không UI
- `configs/modes/dual_model.yaml` — DETR + YOLO + fusion (`pip install -e ".[detr]"`)
- `configs/deploy/server-rtsp.yaml` — server kéo RTSP từ laptop

## Giao diện web

Không có SPA riêng; **Pipeline Inspector** là `api/static/inspector.html` phục vụ bởi FastAPI, dữ liệu thật từ `/api/state`.

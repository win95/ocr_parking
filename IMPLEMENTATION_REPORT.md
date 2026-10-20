# Báo cáo triển khai — pipeline modular & Inspector

## File đã thêm / sửa

- `src/smart_parking/contracts.py` — hợp đồng kiểu
- `src/smart_parking/pipeline/*` — context, observability, runner, stages
- `src/smart_parking/detection/detr_r50.py`, `normalize.py`, `fusion.py`
- `src/smart_parking/occupancy/engine.py`
- `src/smart_parking/replay/store.py`
- `src/smart_parking/api/inspector.py`, `api/static/inspector.html`
- `src/smart_parking/config.py` — chế độ pipeline, layer, fusion, inspector
- `src/smart_parking/app.py` — dùng `ModularPipeline`
- `configs/modes/*`, `configs/deploy/*`
- Kiểm thử: fusion, normalize, config, pipeline, coasting, stale, halt
- `docs/PIPELINE_ARCHITECTURE.md`, `docs/setup/SCENARIO_B_LAPTOP_CLIENT.md`

## Quyết định kiến trúc

- Giữ YAML `detection` và UI OpenCV; thêm pipeline modular song song.
- DETR qua Hugging Face (extra `detr`).
- Chiến lược fusion trong `FusionConfig`; `weighted_nms` scale score, không giả định tương đương trực tiếp.
- Inspector chỉ hiển thị dữ liệu thật từ `INSPECTOR_STORE`.
- Kịch bản B: laptop phát RTSP, server GPU inference.

## Lệnh

```bash
pip install -e ".[dev,inspector]"
pytest -q
python -m smart_parking --config configs/modes/debug.yaml
python -m smart_parking --inspector-only --config configs/modes/debug.yaml
```

## Kết quả kiểm thử

`pytest -q` — unit + integration (YOLO mock).

## Việc còn lại

- Đếm reconnect RTSP trong ingest.
- Metric GPU trong `PipelineMetrics` (tùy chọn nvidia-ml-py).
- Preview ảnh từng tầng trên Inspector.
- Xác thực Inspector cho production.
- Benchmark GPU (`@pytest.mark.gpu`).

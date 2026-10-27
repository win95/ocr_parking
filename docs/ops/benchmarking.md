# Đo hiệu năng

**Trạng thái:** Đã triển khai

```bash
python scripts/benchmark_fps.py --config configs/default.yaml --seconds 30
```

Ghi MLflow (một run / lần benchmark):

```bash
pip install -e ".[mlflow]"
export MLFLOW_TRACKING_URI=./mlruns   # hoặc server team
python scripts/benchmark_fps.py --config configs/modes/benchmark.yaml --seconds 30 \
  --mlflow --dataset parking_lot --dataset-version v1
```

Lưu: artifact YAML (`config/`), `model_version`, tags dataset, metrics FPS/latency.

Báo latency mean/p50/p95 (ms) và FPS. Dùng SSD local cho nguồn video.

Warmup: 50 frame trước khi đo.

## Checklist review

- [x] Quy trình đã mô tả

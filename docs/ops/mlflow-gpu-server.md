# MLflow + đánh giá model trên server GPU

## 1. Chuẩn bị môi trường

```bash
cd /opt/smart-parking/OCR   # hoặc clone repo
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,inspector,mlflow]"
python scripts/verify_gpu_ready.py
```

| Hạng mục | Ghi chú |
|----------|---------|
| GPU + driver | `nvidia-smi` |
| Model weights | `models/*.pt` hoặc `yolo11n.pt` |
| Video / RTSP | `data/*.mp4` hoặc `configs/deploy/server-rtsp.yaml` |
| Slots | `configs/slots/parking_lot_01.json` khớp resolution stream |
| MLflow | `MLFLOW_TRACKING_URI=./mlruns` (hoặc server nội bộ) |
| Thư mục log | `mkdir -p logs mlruns` |

```bash
export MLFLOW_TRACKING_URI=./mlruns
export MLFLOW_EXPERIMENT_NAME=smart-parking
export SMART_PARKING_CONFIG=configs/modes/experiment_gpu.yaml
```

## 2. Debug / kiểm tra khung hình

| Cách | Lệnh / URL |
|------|------------|
| UI overlay + minimap | `python -m smart_parking --config configs/modes/experiment_gpu.yaml` |
| Inspector health | `http://127.0.0.1:8765` (SSH tunnel nếu remote) |
| Artifact JSON (detections/metrics) | `logs/artifacts_eval/` mỗi N frame |
| Ảnh khi cảnh báo | `logs/alert_frames/*.jpg` (overlay) |
| Sự kiện slot | `logs/events_eval.jsonl` |

Benchmark + MLflow:

```bash
python scripts/benchmark_fps.py --config configs/modes/benchmark.yaml --seconds 60 \
  --mlflow --dataset parking_lot --dataset-version v1 --run-name gpu-bench-$(date +%Y%m%d)
mlflow ui --host 0.0.0.0 --port 5000 --backend-store-uri ./mlruns
```

## 3. Cảnh báo thử nghiệm (chỉ log)

Bật trong YAML (`analytics.alerts`):

- `ingest_degraded` / `ingest_unhealthy` — stream / RTSP
- `model_unhealthy` — inference lỗi
- `slot_stale` — occupancy STALE
- `utilization_high` — ngưỡng % (tùy chọn)

Output: `logs/alerts_eval.jsonl` + dòng `WARNING` logger `smart_parking.alerts`.

Giai đoạn sau: webhook/email (chưa triển khai).

## 4. Quy trình gợi ý

1. `verify_gpu_ready.py`
2. `python scripts/benchmark_fps.py --config configs/modes/benchmark.yaml --seconds 60 --mlflow` (tùy chọn `--pipeline` cho E2E)
3. `mlflow ui --port 5000`
4. Debug qualitative: `configs/modes/experiment_gpu.yaml` + Inspector `:8765`
5. Promote: cập nhật `detection.model_path` hoặc `models.active` + `configs/deploy/server.yaml`

### Model registry (YAML)

```yaml
models:
  active: yolo11n-default
  registry:
    - id: yolo11n-default
      path: models/yolo11n.pt
      backend: pytorch
      status: approved
      mlflow_run_id: "<run-id>"
```

Chạy lặp benchmark: `bash scripts/bench_models.sh configs/modes/benchmark.yaml`

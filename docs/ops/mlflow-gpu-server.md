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
bash scripts/server_start_rtsp.sh --with-mlflow
# hoặc chỉ UI tracking:
bash scripts/server_start_rtsp.sh --mlflow-only

python scripts/benchmark_fps.py --config configs/modes/benchmark.yaml --seconds 60 \
  --mlflow --dataset parking_lot --dataset-version v1 --run-name gpu-bench-$(date +%Y%m%d)
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

## 5. MLflow MCP server (AI assistant)

Cho phép agent/IDE đọc experiments, runs, model registry qua MCP thay vì
mở UI. Yêu cầu MLflow ≥ 3.5.1 + Python ≥ 3.10, nên chạy trong môi trường
riêng — **không** cài vào `.venv` Python 3.8 của project.

```bash
# Cài (một lần, dùng uv để lấy Python 3.12)
curl -LsSf https://astral.sh/uv/install.sh | sh
~/.local/bin/uv venv --python 3.12 ~/.venvs/mlflow-mcp
~/.local/bin/uv pip install --python ~/.venvs/mlflow-mcp/bin/python 'mlflow[mcp]>=3.5.1'

# Kiểm tra
~/.venvs/mlflow-mcp/bin/mlflow mcp run --help
```

Đăng ký với OpenCode (tạo `opencode.json` ở root repo):

```bash
opencode mcp add mlflow \
  --env MLFLOW_TRACKING_URI=http://127.0.0.1:5000 \
  --env MLFLOW_MCP_TOOLS=ml \
  --env MLFLOW_DISABLE_AGENT_HINT=1 \
  -- ~/.venvs/mlflow-mcp/bin/mlflow mcp run
opencode mcp list   # ✓ mlflow connected
```

`MLFLOW_MCP_TOOLS` chọn nhóm tool: `ml` (experiments, runs, models,
deployments — mặc định ở đây), `genai` (traces, scorers, experiments, runs),
`all`, hoặc danh sách `traces,runs,...`.

Lưu ý tương thích: MCP 3.x dùng API mới cho traces/scorers, nên **chỉ dùng
`MLFLOW_MCP_TOOLS=ml`** khi tracking server vẫn là 2.17.x (như hiện tại).
Muốn dùng trace tools phải nâng server lên ≥ 3.5.1 rồi đổi sang `genai`
hoặc `all`.

Client khác (Claude Desktop, Cursor…) dùng cùng command/args ở trên với
`MLFLOW_TRACKING_URI` trỏ tới server hoặc `file:///home/ubuntu/ocr_parking/mlruns`.

# Sổ tay vận hành

**Trạng thái:** Đã triển khai

> Cài đặt từ đầu, cấu hình và tra cứu script: [../setup/RUN_AND_SETUP.md](../setup/RUN_AND_SETUP.md).
> Trang này chỉ gồm thao tác vận hành hàng ngày.

## 1. Khởi động

```bash
cd /home/ubuntu/ocr_parking
source .venv/bin/activate

# Pipeline RTSP + Inspector (khuyến nghị)
bash scripts/server_start_rtsp.sh

# Kèm MLflow UI :5000
bash scripts/server_start_rtsp.sh --with-mlflow

# Chỉ MLflow UI
bash scripts/server_start_rtsp.sh --mlflow-only

# Chỉ Inspector (không xử lý video)
python -m smart_parking --config configs/deploy/server.local.yaml --inspector-only
```

Chạy trực tiếp không qua script:

```bash
python -m smart_parking --config configs/deploy/server.local.yaml
python -m smart_parking --config configs/default.yaml --source webcam:0
python -m smart_parking --config configs/deploy/server-file-local.yaml
python -m smart_parking --config configs/deploy/server.local.yaml --backend tensorrt
```

## 2. Dừng

```bash
# Nếu chạy bằng script (foreground): Ctrl+C

# Nếu chạy nền
pkill -f "python -m smart_parking"
pkill -f "mlflow ui"

# Systemd
sudo systemctl stop smart-parking-server
```

## 3. Kiểm tra sức khỏe

```bash
curl -s http://127.0.0.1:8765/api/health
curl -s http://127.0.0.1:8765/api/state | python -m json.tool

# Từ LAN (đã khai báo allow_networks)
curl -s http://192.168.100.239:8765/api/state

# Có token
curl -s -H "X-API-Token: $SMART_PARKING_INSPECTOR_TOKEN" \
  http://192.168.100.239:8765/api/state
```

Đọc nhanh `overall_status` và 3 block `ingest` / `model` / `occupancy`:

- `HEALTHY` — bình thường.
- `DEGRADED` — stream trễ, chưa có frame, hoặc inference chậm.
- `UNHEALTHY` — lỗi mở stream / inference / occupancy.

Dashboard: `http://<server-ip>:8765` (thêm `?token=...` nếu bật token).

## 4. Log & artifact

| Đường dẫn | Nội dung |
|---|---|
| `logs/server.log` | Log pipeline + Inspector (khi chạy qua script) |
| `logs/events.jsonl` | Sự kiện KPI (enter/exit/dwell) |
| `logs/alerts.jsonl` | Cảnh báo vận hành |
| `logs/artifacts/` | Frame mẫu (JSON + ảnh) |
| `logs/mlflow_ui.log` | Log MLflow UI |

```bash
tail -f logs/server.log
tail -f logs/events.jsonl
pytest -q        # kiểm thử nhanh
```

## 5. MLflow

```bash
export MLFLOW_TRACKING_URI="$PWD/mlruns"
export MLFLOW_EXPERIMENT_NAME=smart-parking

bash scripts/server_start_rtsp.sh --with-mlflow
# UI local: http://127.0.0.1:5000

# Mở cho LAN
MLFLOW_UI_HOST=0.0.0.0 bash scripts/server_start_rtsp.sh --with-mlflow
# UI: http://<server-ip>:5000
```

Benchmark / train và MCP: xem [mlflow-gpu-server.md](mlflow-gpu-server.md).

## 6. Calibrate slot

```bash
ffmpeg -rtsp_transport tcp -i rtsp://<CLIENT_IP>:8554/parking \
  -frames:v 1 -y data/ref_live.jpg
python scripts/calibrate_slots.py \
  --image data/ref_live.jpg \
  --out configs/slots/parking_lot_01.json
```

Sau khi lưu: khởi động lại pipeline. Nếu log có warning
`Slot calibration is ... but incoming frame is ...` → calibrate lại đúng
resolution stream.

## 7. Sự cố nhanh

| Triệu chứng | Xử lý |
|---|---|
| `Cannot reach RTSP` | Chạy client (`client_laptop_start.sh`), kiểm tra firewall 8554, `ffprobe` |
| `overall=DEGRADED` | Xem `frame_age_ms`, `last_error` trong block tương ứng |
| Inspector `403` | Thêm subnet client vào `inspector.allow_networks` |
| Inspector `401` | Gửi đúng `X-API-Token` / `Authorization: Bearer` |
| Slot lệch | Calibrate lại từ frame đúng resolution |
| FPS thấp | Giảm resolution client, TensorRT, kiểm tra `nvidia-smi` |
| MLflow UI lỗi | `pip install -e ".[mlflow]"`; xem `logs/mlflow_ui.log` |

Chi tiết: [../setup/TROUBLESHOOTING.md](../setup/TROUBLESHOOTING.md).

## Checklist review

- [x] CLI khớp `__main__.py`
- [x] Lệnh khớp `scripts/server_start_rtsp.sh`
- [x] Đường dẫn log khớp code

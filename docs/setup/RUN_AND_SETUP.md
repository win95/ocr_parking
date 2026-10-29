# Hướng dẫn Setup & Chạy

**Trạng thái:** Sẵn sàng · **Cập nhật:** 2026-10-29

Tài liệu hợp nhất: cài đặt máy chủ/client, cấu hình, chạy pipeline, Inspector,
MLflow + MCP, calibrate slot, systemd và tra cứu nhanh toàn bộ script.

- Kịch bản B (server GPU + laptop client): [SCENARIO_B_LAPTOP_CLIENT.md](SCENARIO_B_LAPTOP_CLIENT.md)
- Cấu hình chi tiết: [../03-configuration.md](../03-configuration.md)
- Calibrate slot: [../04-slot-calibration.md](../04-slot-calibration.md)
- Vận hành hàng ngày: [../ops/runbook.md](../ops/runbook.md)

---

## 0. TL;DR

**Server GPU** (chạy pipeline + Inspector):

```bash
git clone git@github.com:win95/ocr_parking.git && cd ocr_parking
bash scripts/setup_server.sh                 # apt + .venv + extras
source .venv/bin/activate
python scripts/verify_gpu_ready.py

# Sửa source + slots_path trong configs/deploy/server.local.yaml
bash scripts/server_start_rtsp.sh            # probe RTSP rồi chạy pipeline
```

**Laptop client** (chỉ phát video, không cần GPU):

```bash
bash scripts/client_prepare_local.sh         # ffmpeg + MediaMTX, không cần sudo
bash scripts/client_laptop_start.sh webcam                 # /dev/video0
bash scripts/client_laptop_start.sh video data/parking_demo.mp4
```

Mặc định stream: `rtsp://<LAPTOP_IP>:8554/parking` (MediaMTX, TCP).

---

## 1. Yêu cầu

| Hạng mục | Ghi chú |
|---|---|
| Python | ≥ 3.8 (khuyến nghị 3.11). MLflow MCP cần ≥ 3.10 → venv riêng |
| Hệ điều hành | Ubuntu 22.04/24.04 |
| GPU | NVIDIA + driver; CUDA cho PyTorch/TensorRT (không bắt buộc để chạy CPU) |
| Công cụ | `ffmpeg`, `ffprobe`, `git`, `curl` |
| Mạng | Server và laptop cùng LAN/VPN; mở `8554/tcp` (RTSP) và `8765/tcp` (Inspector) |

Cài PyTorch CUDA (chọn đúng phiên bản CUDA của máy):

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

---

## 2. Cài đặt Server (GPU)

### 2.1 Tự động

```bash
bash scripts/setup_server.sh
```

Script thực hiện:

1. `docs/setup/ubuntu-gpu.sh` — apt: build tools, ffmpeg, v4l-utils, libgl/gtk.
2. Tạo `.venv`, cài `-e ".[dev,inspector,mlflow]"`.
3. Tạo thư mục `data/ models/ logs/ logs/artifacts/ mlruns/ configs/slots/`.
4. `cp -n configs/deploy/server.yaml → configs/deploy/server.local.yaml` (không ghi đè nếu đã có).

Sau đó sửa `configs/deploy/server.local.yaml` (xem [mục 4](#4-cấu-hình)) rồi chạy:

```bash
source .venv/bin/activate
python scripts/verify_gpu_ready.py
```

### 2.2 Thủ công

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel
pip install -e ".[dev,inspector,mlflow]"
mkdir -p data models logs logs/artifacts mlruns configs/slots
```

| Extra | Dùng cho |
|---|---|
| `dev` | pytest, test suite |
| `inspector` | FastAPI + Uvicorn cho Inspector `:8765` |
| `mlflow` | MLflow UI, benchmark/train logging |
| `detr` | DETR + fusion (`configs/modes/dual_model.yaml`) |
| `roboflow` | Tải dataset Roboflow |
| `desktop` | `python-xlib` cho `scripts/raise_window.py` |

### 2.3 Kiểm tra môi trường

```bash
python scripts/verify_gpu_ready.py
nvidia-smi
ffprobe -version
```

---

## 3. Cài đặt Client (laptop)

Client **không cần GPU**, chỉ cần phát RTSP hoặc copy file.

```bash
# Cách nhanh, không cần sudo (tải ffmpeg static + MediaMTX vào tools/)
bash scripts/client_prepare_local.sh

# Hoặc cài hệ thống (cần sudo)
bash scripts/setup_client.sh                       # role=streamer
sudo bash scripts/install_mediamtx_client.sh
```

Edge mode (chạy app ngay trên laptop có GPU):

```bash
bash scripts/setup_client.sh --role edge --install-app
python -m smart_parking --config configs/deploy/edge.yaml --source webcam:0
```

Cấu hình stream: copy `configs/deploy/client-laptop.env.example` →
`configs/deploy/client.local.env` (hoặc `/etc/smart-parking/stream.env`):

```bash
VIDEO_DEVICE=/dev/video0
VIDEO_SIZE=1280x720     # phải khớp resolution dùng để calibrate slot
VIDEO_FPS=15
RTSP_LISTEN=8554
RTSP_PATH=parking
```

Kiểm tra stream tại client:

```bash
ffprobe -rtsp_transport tcp rtsp://127.0.0.1:8554/parking
```

---

## 4. Cấu hình

Thứ tự ưu tiên: `--source` (CLI) → biến môi trường → file YAML.

| Biến môi trường | Mặc định | Ý nghĩa |
|---|---|---|
| `SMART_PARKING_CONFIG` | `configs/default.yaml` | File YAML khi không truyền `--config` |
| `SMART_PARKING_INSPECTOR_TOKEN` | — | Bật bearer token cho Inspector (không ghi vào YAML) |
| `MLFLOW_TRACKING_URI` | `$PWD/mlruns` (script) | Tracking store hoặc `http://host:5000` |
| `MLFLOW_EXPERIMENT_NAME` | `smart-parking` | Experiment mặc định |
| `MLFLOW_UI_HOST` / `MLFLOW_UI_PORT` | `127.0.0.1` / `5000` | Địa chỉ MLflow UI |
| `STREAM_ENV` | `/etc/smart-parking/stream.env` | File env của client |
| `RTSP_URL`, `CFG`, `DISPLAY` | — | Dùng cho `server_show_camera.sh` |

`source` chấp nhận: `data/x.mp4`, `webcam:0`, `rtsp://...`.

Profile có sẵn:

| File | Mục đích |
|---|---|
| `configs/default.yaml` | Chạy local, UI bật |
| `configs/deploy/server.yaml` | Server headless, model production |
| `configs/deploy/server-rtsp.yaml` | Mẫu RTSP (thay `CLIENT_IP`) |
| `configs/deploy/server.local.yaml` | **Cấu hình thực tế của server** (không commit khi khác site) |
| `configs/deploy/server.view.yaml` | Server + cửa sổ OpenCV để xem camera |
| `configs/deploy/server-file-local.yaml`, `server-file.yaml` | Nguồn file MP4 |
| `configs/modes/benchmark.yaml`, `debug.yaml`, `dual_model.yaml` | Benchmark / debug / DETR+YOLO |

Inspector khi mở LAN phải khai báo subnet và nên bật token:

```yaml
inspector:
  enabled: true
  host: 0.0.0.0
  port: 8765
  allow_networks:
    - 127.0.0.0/8
    - ::1/128
    - 192.168.100.0/24
```

Xem thêm: [../ops/security.md](../ops/security.md).

---

## 5. Chạy pipeline

### 5.1 Lệnh trực tiếp

```bash
source .venv/bin/activate

# File MP4
python -m smart_parking --config configs/deploy/server-file-local.yaml

# Webcam
python -m smart_parking --config configs/default.yaml --source webcam:0

# RTSP (kịch bản B)
python -m smart_parking --config configs/deploy/server.local.yaml

# Đổi backend
python -m smart_parking --config configs/deploy/server.local.yaml --backend tensorrt

# Chỉ Inspector, không xử lý video
python -m smart_parking --config configs/deploy/server.local.yaml --inspector-only
```

| Flag | Ý nghĩa |
|---|---|
| `--config PATH` | File YAML (mặc định theo `SMART_PARKING_CONFIG`) |
| `--source ...` | Ghi đè `source` (`file`, `webcam:N`, `rtsp://`) |
| `--backend pytorch\|tensorrt` | Ghi đè backend detection |
| `--inspector-only` | Chỉ chạy API Inspector |

### 5.2 Script server (khuyến nghị)

```bash
bash scripts/server_start_rtsp.sh                 # pipeline + Inspector
bash scripts/server_start_rtsp.sh --with-mlflow   # + MLflow UI :5000
bash scripts/server_start_rtsp.sh --mlflow-only   # chỉ MLflow UI
```

Script sẽ:

1. Kiểm tra `configs/deploy/server.local.yaml` tồn tại và không còn placeholder `CLIENT_IP`/`LAPTOP_IP`.
2. `ffprobe` stream RTSP trước khi chạy (báo lỗi sớm nếu client chưa lên).
3. Kích hoạt `.venv` và chạy `python -m smart_parking --config ...`.
4. Với `--with-mlflow`: chạy `mlflow ui` nền và tắt kèm khi script dừng.

### 5.3 Xem camera trên màn hình server

```bash
bash scripts/server_show_camera.sh           # ffplay, camera thô
bash scripts/server_show_camera.sh --app     # app + YOLO + occupancy + minimap
bash scripts/server_show_camera.sh --both
```

Cần `DISPLAY` (mặc định `:0`). Nếu cửa sổ bị che:

```bash
python scripts/raise_window.py "Smart Parking" --remap
```

---

## 6. Inspector

| Endpoint | Bảo vệ |
|---|---|
| `/` , `/api/health` | Công khai |
| `/api/state`, `/api/cameras`, `/api/metrics` | Theo `allow_networks` + token |

```bash
# Trên server
curl http://127.0.0.1:8765/api/health

# Trong LAN (đã khai báo subnet)
curl http://192.168.100.239:8765/api/state

# Có token
curl -H "X-API-Token: $SMART_PARKING_INSPECTOR_TOKEN" \
  http://192.168.100.239:8765/api/state

# Dashboard có token
# http://192.168.100.239:8765/?token=<token>
```

`overall_status` gồm `HEALTHY` / `DEGRADED` / `UNHEALTHY`, tổng hợp từ
`ingest`, `model`, `occupancy`.

---

## 7. MLflow

### 7.1 UI + tracking

```bash
bash scripts/server_start_rtsp.sh --with-mlflow   # pipeline + UI
bash scripts/server_start_rtsp.sh --mlflow-only   # chỉ UI

# Mở UI cho máy khác trong LAN (mặc định chỉ 127.0.0.1)
MLFLOW_UI_HOST=0.0.0.0 bash scripts/server_start_rtsp.sh --with-mlflow
# http://<server-ip>:5000
```

Mặc định `MLFLOW_TRACKING_URI=./mlruns`, experiment `smart-parking`.
Script tự dùng `.venv/bin/mlflow`, không cần kích hoạt venv trước.

### 7.2 Ghi benchmark / training

```bash
export MLFLOW_TRACKING_URI="$PWD/mlruns"
export MLFLOW_EXPERIMENT_NAME=smart-parking

# Detector latency/FPS
python scripts/benchmark_fps.py \
  --config configs/deploy/server-file-local.yaml \
  --seconds 30 --mlflow \
  --dataset parking_demo --dataset-version demo \
  --run-name "bench-$(date +%Y%m%d-%H%M)"

# Toàn pipeline (tracking + occupancy + overlay)
python scripts/benchmark_fps.py --config configs/deploy/server.local.yaml \
  --seconds 60 --pipeline --mlflow

# Toàn bộ model registry
bash scripts/bench_models.sh configs/modes/benchmark.yaml

# Train YOLO từ Roboflow
python scripts/roboflow_train.py \
  --workspace WS --project parking --version 3 \
  --model yolo11s.pt --config configs/default.yaml --mlflow
```

### 7.3 MLflow MCP (AI assistant)

MLflow MCP cần **MLflow ≥ 3.5.1 + Python ≥ 3.10** → cài venv riêng, không đụng `.venv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
~/.local/bin/uv venv --python 3.12 ~/.venvs/mlflow-mcp
~/.local/bin/uv pip install --python ~/.venvs/mlflow-mcp/bin/python 'mlflow[mcp]>=3.5.1'

opencode mcp add mlflow \
  --env MLFLOW_TRACKING_URI=http://127.0.0.1:5000 \
  --env MLFLOW_MCP_TOOLS=ml \
  --env MLFLOW_DISABLE_AGENT_HINT=1 \
  -- ~/.venvs/mlflow-mcp/bin/mlflow mcp run

opencode mcp list          # ✓ mlflow connected
```

| `MLFLOW_MCP_TOOLS` | Nhóm tool |
|---|---|
| `ml` (đang dùng) | experiments, runs, models, deployments |
| `genai` (mặc định) | traces, scorers, experiments, runs |
| `all` | tất cả |
| `traces,runs,...` | chọn thủ công |

> Tracking server 2.17.x chưa hỗ trợ trace API → giữ `ml`. Muốn dùng trace
> tools phải nâng server lên ≥ 3.5.1 rồi đổi sang `genai`/`all`.

Chi tiết: [../ops/mlflow-gpu-server.md](../ops/mlflow-gpu-server.md).

---

## 8. Calibrate slot

Slot polygon phải khớp **đúng resolution của stream** (ví dụ 1280×720).

```bash
# 1. Lấy frame tham chiếu từ chính stream
ffmpeg -rtsp_transport tcp -i rtsp://<CLIENT_IP>:8554/parking \
  -frames:v 1 -y data/ref_live.jpg

# 2. Calibrate (cần màn hình desktop)
python scripts/calibrate_slots.py \
  --image data/ref_live.jpg \
  --out configs/slots/parking_lot_01.json
```

Thao tác: click trái thêm điểm · `n` polygon mới · `s` lưu · `q` thoát.

Sau khi lưu, khởi động lại pipeline. Nếu resolution slot ≠ frame, app ghi
warning `Slot calibration is ... but incoming frame is ...` — calibrate lại.

Chi tiết schema: [../04-slot-calibration.md](../04-slot-calibration.md).

---

## 9. Systemd (chạy nền)

```bash
# Dừng các tiến trình chạy tay trước
pkill -f "python -m smart_parking"

sudo cp deploy/systemd/smart-parking-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now smart-parking-server

systemctl status smart-parking-server
journalctl -u smart-parking-server -f
```

Unit dùng `%h/ocr_parking`, `SMART_PARKING_CONFIG=configs/deploy/server.local.yaml`
và đọc secret tùy chọn từ `/etc/smart-parking/server.env`:

```bash
sudo install -d -m 755 /etc/smart-parking
sudo sh -c 'echo "SMART_PARKING_INSPECTOR_TOKEN=$(openssl rand -hex 24)" \
  > /etc/smart-parking/server.env'
sudo chmod 600 /etc/smart-parking/server.env
```

Client streamer: `deploy/systemd/rtsp-publish.service`.

---

## 10. Tra cứu script

| Script | Máy | Mô tả |
|---|---|---|
| `setup_server.sh` | Server | apt + venv + extras + thư mục + config local |
| `install_dev.sh` | Dev | venv + extras dev + PyTorch CPU/CUDA + verify |
| `verify_gpu_ready.py` | Server | Báo cáo GPU/CUDA/Torch/disk |
| `server_start_rtsp.sh` | Server | Probe RTSP → chạy pipeline; `--with-mlflow`, `--mlflow-only` |
| `server_show_camera.sh` | Server | `ffplay` / app overlay / cả hai |
| `raise_window.py` | Server | Đưa cửa sổ OpenCV lên trước (X11) |
| `setup_client.sh` | Client | apt ffmpeg/v4l; `--role edge --install-app` |
| `client_prepare_local.sh` | Client | Tải ffmpeg static + MediaMTX, tạo env (không sudo) |
| `install_mediamtx_client.sh` | Client | Cài MediaMTX vào `/usr/local/bin` |
| `client_laptop_start.sh` | Client | `webcam` hoặc `video <path>` → MediaMTX + ffmpeg |
| `run_rtsp_publish.sh` | Client | Phát webcam/MP4 thành RTSP |
| `calibrate_slots.py` | Server | Vẽ polygon slot từ ảnh tham chiếu |
| `benchmark_fps.py` | Server | Đo latency/FPS; `--pipeline`, `--mlflow` |
| `bench_models.sh` | Server | Benchmark model registry + MLflow |
| `roboflow_train.py` | GPU | Tải dataset + train YOLO; `--mlflow` |
| `export_tensorrt.py` | GPU | Export `.engine` (`--model`, `--imgsz`, `--half`) |

Chạy `bash scripts/<script>.sh --help` hoặc `python scripts/<script>.py --help`
để xem tham số đầy đủ.

---

## 11. Kiểm tra sức khỏe & lỗi thường gặp

```bash
# Dịch vụ
curl -s http://127.0.0.1:8765/api/health
curl -s http://127.0.0.1:8765/api/state | python -m json.tool

# Log
tail -f logs/server.log
tail -f logs/mlflow_ui.log
tail -f logs/events.jsonl

# Test suite
pytest -q
```

| Triệu chứng | Nguyên nhân / xử lý |
|---|---|
| `Cannot reach RTSP` | Client chưa chạy MediaMTX/ffmpeg; firewall `8554`; sai IP |
| `Replace LAPTOP_IP/CLIENT_IP` | Sửa `source:` trong `server.local.yaml` |
| `overall=DEGRADED` | Xem block `ingest`/`model`/`occupancy`; thường stream trễ hoặc chưa có frame |
| `403 forbidden` | Client ngoài `inspector.allow_networks` |
| `401 unauthorized` | Thiếu/sai `X-API-Token` hoặc Bearer token |
| Slot lệch | Calibrate lại đúng resolution stream |
| FPS thấp | Giảm resolution client, dùng TensorRT, kiểm tra GPU |
| MLflow UI trắng/500 | `mlflow` chưa cài hoặc sai `--backend-store-uri`; xem `logs/mlflow_ui.log` |
| `ModuleNotFoundError: mlflow` | `pip install -e ".[mlflow]"` |
| MCP trace tool lỗi | Server 2.17 chưa hỗ trợ trace → dùng `MLFLOW_MCP_TOOLS=ml` |

Thêm: [TROUBLESHOOTING.md](TROUBLESHOOTING.md), [HARDWARE.md](HARDWARE.md).

---

## 12. Checklist

- [ ] `python scripts/verify_gpu_ready.py` OK
- [ ] `ffprobe` tới stream client OK (TCP)
- [ ] `configs/deploy/server.local.yaml` đúng `source`, `slots_path`, `allow_networks`
- [ ] Slot calibrate đúng resolution stream
- [ ] Inspector `:8765` trả `HEALTHY`
- [ ] MLflow UI `:5000` (nếu dùng) truy cập được
- [ ] `pytest -q` pass
- [ ] (Tùy chọn) systemd enabled, secret trong `/etc/smart-parking/server.env`

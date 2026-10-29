# Phân tích bãi đỗ xe thông minh

Theo dõi chỗ trống/đã chiếm thời gian thực với YOLO11, làm mượt theo thời gian và giao diện OpenCV. Sẵn sàng TensorRT trên Ubuntu + GPU NVIDIA.

**Tài liệu:** [docs/README.md](docs/README.md) · **Công nghệ:** [docs/TECH_STACK.md](docs/TECH_STACK.md)

## Bắt đầu nhanh

```bash
git clone git@github.com:win95/ocr_parking.git && cd ocr_parking
bash scripts/setup_server.sh          # apt + .venv + extras
source .venv/bin/activate
python scripts/verify_gpu_ready.py    # cài PyTorch CUDA nếu chưa có

# Chạy với file MP4 có sẵn
python -m smart_parking --config configs/deploy/server-file-local.yaml

# Kịch bản B: server nhận RTSP từ laptop client
bash scripts/server_start_rtsp.sh
```

Hướng dẫn đầy đủ (setup, cấu hình, script, Inspector, MLflow/MCP, systemd):
[docs/setup/RUN_AND_SETUP.md](docs/setup/RUN_AND_SETUP.md).

## Pipeline modular & gỡ lỗi

- Kiến trúc: [docs/PIPELINE_ARCHITECTURE.md](docs/PIPELINE_ARCHITECTURE.md)
- Chế độ debug: `python -m smart_parking --config configs/modes/debug.yaml`
- Giao diện Pipeline Inspector: `http://<server-ip>:8765` (khi `inspector.enabled: true`; xem [docs/ops/security.md](docs/ops/security.md))
- DETR + YOLO: `pip install -e ".[detr]"` rồi dùng `configs/modes/dual_model.yaml`

Calibrate slot: `python scripts/calibrate_slots.py --image data/ref.jpg --out configs/slots/parking_lot_01.json`

Phần cứng: [docs/setup/HARDWARE.md](docs/setup/HARDWARE.md)

**Server GPU + laptop client (kịch bản B):** [docs/setup/SCENARIO_B_LAPTOP_CLIENT.md](docs/setup/SCENARIO_B_LAPTOP_CLIENT.md)

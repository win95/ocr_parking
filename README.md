# Phân tích bãi đỗ xe thông minh

Theo dõi chỗ trống/đã chiếm thời gian thực với YOLO11, làm mượt theo thời gian và giao diện OpenCV. Sẵn sàng TensorRT trên Ubuntu + GPU NVIDIA.

**Tài liệu:** [docs/README.md](docs/README.md) · **Công nghệ:** [docs/TECH_STACK.md](docs/TECH_STACK.md)

## Bắt đầu nhanh

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,inspector]"
# Cài PyTorch CUDA: https://pytorch.org
python scripts/verify_gpu_ready.py
python -m smart_parking --config configs/default.yaml --source data/sample.mp4
```

## Pipeline modular & gỡ lỗi

- Kiến trúc: [docs/PIPELINE_ARCHITECTURE.md](docs/PIPELINE_ARCHITECTURE.md)
- Chế độ debug: `python -m smart_parking --config configs/modes/debug.yaml`
- Giao diện Pipeline Inspector: `http://127.0.0.1:8765` (khi `inspector.enabled: true`)
- DETR + YOLO: `pip install -e ".[detr]"` rồi dùng `configs/modes/dual_model.yaml`

Calibrate slot: `python scripts/calibrate_slots.py --image data/ref.jpg --out configs/slots/parking_lot_01.json`

Phần cứng: [docs/setup/HARDWARE.md](docs/setup/HARDWARE.md)

**Server GPU + laptop client (kịch bản B):** [docs/setup/SCENARIO_B_LAPTOP_CLIENT.md](docs/setup/SCENARIO_B_LAPTOP_CLIENT.md)

# Smart Parking Analytics

Real-time parking slot occupancy with YOLO11, temporal smoothing, and OpenCV UI. TensorRT-ready on Ubuntu + NVIDIA GPU.

**Documentation:** [docs/README.md](docs/README.md) · **Tech stack:** [docs/TECH_STACK.md](docs/TECH_STACK.md)

## Quick start

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,inspector]"
# Install PyTorch with CUDA from https://pytorch.org
python scripts/verify_gpu_ready.py
python -m smart_parking --config configs/default.yaml --source data/sample.mp4
```

## Modular pipeline & debug

- Architecture: [docs/PIPELINE_ARCHITECTURE.md](docs/PIPELINE_ARCHITECTURE.md)
- Debug mode: `python -m smart_parking --config configs/modes/debug.yaml`
- Pipeline Inspector UI: `http://127.0.0.1:8765` (when `inspector.enabled: true`)
- Dual DETR+YOLO: `pip install -e ".[detr]"` then `configs/modes/dual_model.yaml`

Calibrate slots: `python scripts/calibrate_slots.py --image data/ref.jpg --out configs/slots/parking_lot_01.json`

Hardware: [docs/setup/HARDWARE.md](docs/setup/HARDWARE.md)

Server GPU + laptop client (kịch bản B): [docs/setup/SCENARIO_B_LAPTOP_CLIENT.md](docs/setup/SCENARIO_B_LAPTOP_CLIENT.md)

# Sổ tay vận hành

**Trạng thái:** Đã triển khai

## Chạy ứng dụng

```bash
source .venv/bin/activate
python -m smart_parking --config configs/default.yaml
python -m smart_parking --config configs/default.yaml --source webcam:0
python -m smart_parking --config configs/deploy/server.local.yaml
python -m smart_parking --config configs/default.yaml --backend tensorrt
```

## Server + RTSP (kịch bản B)

```bash
bash scripts/server_start_rtsp.sh
```

## Calibrate slot

```bash
python scripts/calibrate_slots.py --image data/ref.jpg --out configs/slots/parking_lot_01.json
```

## Log

`logs/events.jsonl` — một object JSON mỗi dòng (enter/exit/dwell).

## Inspector

```bash
python -m smart_parking --inspector-only --config configs/modes/debug.yaml
```

## Checklist review

- [x] CLI khớp `__main__.py`

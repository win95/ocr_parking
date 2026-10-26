# Cấu hình

**Trạng thái:** Sẵn sàng triển khai  
**Ánh xạ code:** `smart_parking.config`, `configs/default.yaml`

## File

Mặc định: `configs/default.yaml` hoặc biến môi trường `SMART_PARKING_CONFIG`.

## Schema (các khóa chính)

| Khóa | Kiểu | Mặc định | Mô tả |
|------|------|----------|--------|
| `source` | str | `data/sample.mp4` | Đường dẫn, `webcam:N`, hoặc `rtsp://` |
| `slots_path` | str | `configs/slots/...` | Polygon slot |
| `pipeline.mode` | str | `normal` | normal / debug / replay / benchmark |
| `pipeline.layers.*` | bool | — | Bật/tắt từng tầng |
| `detection.backend` | str | `pytorch` | `pytorch` hoặc `tensorrt` |
| `detection.model_path` | str | `yolo11n.pt` | Weights hoặc `.engine` |
| `detection.confidence` | float | 0.35 | Ngưỡng score |
| `detection.imgsz` | int | 640 | Kích thước input |
| `detection.device` | str | `0` | CUDA hoặc `cpu` |
| `detr.model_id` | str | `facebook/detr-resnet-50-dc5` | HF model id cho DETR |
| `detr.device` | str | `cpu` | CUDA (`0`) hoặc `cpu` |
| `detr.confidence` | float | 0.5 | Ngưỡng score DETR |
| `detr.vehicle_only` | bool | true | Chỉ giữ car / bus / truck |
| `detr.size` | int | 800 | Shortest edge; 384 giữ realtime |
| `fusion.strategy` | str | `yolo_only` | yolo_only / detr_only / union / weighted_nms |
| `smoothing.window` | int | 15 | Cửa sổ bỏ phiếu |
| `smoothing.t_on` / `t_off` | int | 10 / 12 | Hysteresis |
| `tracking.coast_frames` | int | 8 | Coast tối đa |
| `tracking.iou_threshold` | float | 0.3 | Ngưỡng IoU |
| `ui.enabled` | bool | true | Cửa sổ OpenCV |
| `inspector.enabled` | bool | false | API Inspector |
| `analytics.log_path` | str | `logs/events.jsonl` | Sự kiện KPI |

Chi tiết pipeline: `pipeline/`, `fusion/`, `detr/`, `artifacts/` trong `config.py`.

## Checklist review

- [x] Khóa đã liệt kê
- [x] Khớp `AppConfig` trong code

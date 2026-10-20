# Module detection

**Trạng thái:** Đã triển khai  
**Code:** `smart_parking.detection`

## DetectorProtocol

```python
def detect(self, image: np.ndarray) -> list[Detection]:
```

`Detection`: `bbox_xyxy`, `confidence`, `class_id`, `class_name`.

## Backend

- **pytorch:** Ultralytics YOLO11.
- **tensorrt:** `TensorRTDetector` nếu có file `.engine`; fallback PyTorch.
- **detr:** `DetrR50Detector` (extra `transformers`).

## Export

```bash
python scripts/export_tensorrt.py --model yolo11n.pt --imgsz 640
```

## Checklist review

- [x] Protocol đã định nghĩa
- [x] Đường TRT đã mô tả

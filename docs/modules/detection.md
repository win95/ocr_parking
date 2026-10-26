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
- **detr:** `DetrR50Detector` (extra `transformers` + `timm`).

## DETR

`DetrR50Detector` chạy `facebook/detr-resnet-50-dc5` qua Hugging Face
transformers. Cài đặt:

```bash
pip install -e ".[detr]"     # transformers + timm
```

Bật trong config:

```yaml
pipeline:
  layers:
    detr: true
    yolo: false
    fusion: false
detr:
  model_id: facebook/detr-resnet-50-dc5
  device: "0"
  confidence: 0.5
  vehicle_only: true
  size: 384
fusion:
  strategy: detr_only
```

Config sẵn dùng: `configs/deploy/server.detr.yaml` (inspector 8768).
Muốn chạy song song YOLO để so sánh: `layers.yolo: true` + `layers.fusion: true`
+ `fusion.strategy: union`.

Đo trên GTX 1080, frame 1280x720 (gồm cả tiền/hậu xử lý):

| `detr.size` | Latency | FPS |
|-------------|---------|-----|
| 800 (mặc định) | 360 ms | 2.8 |
| 480 | 78 ms | 12.9 |
| 384 | 49 ms | 20.3 |
| 320 | 38 ms | 26.2 |

`size` là shortest edge; longest edge = `size * 1.66`. Frame được resize
bằng OpenCV trước khi đưa vào processor (`do_resize=False`) để tránh ~25 ms
resize bằng PIL.

Lưu ý: `vehicle_only: true` chỉ giữ car / motorcycle / bus / truck.

## Export

```bash
python scripts/export_tensorrt.py --model yolo11n.pt --imgsz 640
```

## Checklist review

- [x] Protocol đã định nghĩa
- [x] Đường TRT đã mô tả

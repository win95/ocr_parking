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

Bật trong config (chạy song song với YOLO):

```yaml
pipeline:
  layers:
    detr: true
    yolo: true
    fusion: true
detr:
  model_id: facebook/detr-resnet-50-dc5
  device: "0"
  confidence: 0.5
  vehicle_only: true
  size: 384
fusion:
  strategy: union          # gộp DETR + YOLO rồi NMS
  iou_threshold: 0.5
```

Config sẵn dùng: `configs/deploy/server.detr.yaml` (inspector 8768).

Các chế độ khác:

| Mục đích | Cấu hình |
|----------|----------|
| Chỉ DETR (nhẹ GPU nhất cho DETR) | `yolo: false`, `fusion: false`, `strategy: detr_only` |
| Chỉ YOLO (nhanh nhất) | `detr: false`, `fusion: false`, `strategy: yolo_only` |
| Ưu tiên theo confidence | `strategy: weighted_nms` + `detr_weight` / `yolo_weight` |

`fusion` bắt buộc cả `detr` và `yolo` cùng bật (validator trong `config.py`).
Lưu ý `_nms` của fusion là class-agnostic: box chồng nhau giữa hai model sẽ
triệt tiêu nhau bất kể class, nên hai model chỉ nên trả về cùng nhóm lớp
(ở đây là xe).

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

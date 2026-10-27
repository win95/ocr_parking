# Config — dùng file nào?

Chỉ có **3 config deploy** cần quan tâm. Tên file không quan trọng — app chỉ
đọc nội dung qua `--config`.

| File | Khi nào dùng | Nguồn | Model | Inspector |
|------|--------------|-------|-------|-----------|
| **`deploy/server.detr.yaml`** | **Demo chính** (kịch bản B: laptop phát RTSP) | RTSP client | DETR + YOLO (fusion `union`) | `0.0.0.0:8768` |
| `deploy/server.view.yaml` | Chỉ xem camera + overlay, nhẹ hơn | RTSP client | YOLO | `0.0.0.0:8767` |
| `deploy/server-file-local.yaml` | Không có laptop — xử lý file MP4 trên server (kịch bản C) | `data/*.mp4` | YOLO | `0.0.0.0:8765` |
| `deploy/edge.yaml` | Tất cả trên một máy có webcam (kịch bản A) | `webcam:0` | YOLO | `127.0.0.1:8765` |

## Chạy

```bash
python -m smart_parking --config configs/deploy/server.detr.yaml
```

Đổi nguồn video: sửa `source:` trong file, hoặc tạo bản local (đã gitignore):

```bash
bash scripts/setup_server.sh --rtsp rtsp://192.168.100.234:8554/parking
# → configs/deploy/server.local.yaml
python -m smart_parking --config configs/deploy/server.local.yaml
```

## Config khác (không phải deploy)

- `configs/default.yaml` — mặc định cho dev, nguồn `data/sample.mp4`.
- `configs/modes/*.yaml` — benchmark / debug / dual-model / experiment, dùng cho test.
- `configs/slots/parking_lot_01.json` — dữ liệu slot (hiện `zones: []`, chờ calibrate).

## Kiểm tra nhanh

```bash
bash scripts/setup_server.sh --check              # môi trường + GPU + RTSP
ps -eo pid,cmd | grep "smart_parking --config"    # app đang dùng config nào
curl -s http://127.0.0.1:8768/api/state | head -c 200
```

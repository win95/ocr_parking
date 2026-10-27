# Module UI

**Trạng thái:** Đã triển khai  
**Code:** `smart_parking.ui`

## Overlay

Polygon slot: xanh = trống, đỏ = đã chiếm, vàng = coasting.

Khung detect theo từng model (khi bật `layers.detr` / `layers.yolo`):

| Model | Màu | Nhãn |
|-------|-----|------|
| DETR | cam `(0,140,255)` | `DETR <class> <conf>` |
| YOLO | cyan `(255,255,0)` | `YOLO <class> <conf>` |
| Không có batch riêng (1 model / legacy) | xanh dương `(255,128,0)` | `DET <class> <conf>` |

Legend góc trên-phải hiển thị số detection của từng model, kể cả khi bằng 0
(ví dụ `DETR: 0`). Góc trên-trái dành cho minimap.

## Panel

Cột phải: tổng, thanh utilization, FPS, tên backend.

## Minimap

Góc ảnh hoặc tầng `minimap` pipeline — bản đồ 2D từ `SlotStateContract`.
Không có slot → canvas xám trống.

## Dashboard (Inspector)

`GET /` phục vụ HTML; `/api/state` trả trạng thái pipeline, `/api/system`
trả tài nguyên máy server (GPU/RAM/CPU), `/api/alerts` trả cảnh báo gần đây.
Dashboard tự vẽ thanh GPU/VRAM/RAM và sparkline 120 điểm gần nhất.

## Checklist review

- [x] Màu đã mô tả
- [x] `panel_width` trong config
- [x] Khung detect theo model + legend
- [x] Dashboard có GPU/RAM và cảnh báo

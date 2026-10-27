# Calibrate slot

**Trạng thái:** Sẵn sàng triển khai  
**Code:** `scripts/calibrate_slots.py`, `occupancy/slots.py`

## Schema JSON

```json
{
  "zones": [
    {"id": "A-01", "zone": "A", "polygon": [[x, y], ...]}
  ],
  "meta": {"width": 1920, "height": 1080, "source": "cam_main"}
}
```

## Quy tắc

- Polygon: ≥ 3 điểm, trong `[0,width]×[0,height]`.
- ID duy nhất; `zone` nhóm tùy chọn.
- `meta` phải khớp độ phân giải frame calibrate.

## Công cụ

```bash
python scripts/calibrate_slots.py --image path/to/ref.jpg --out configs/slots/parking_lot_01.json
```

- Click trái: thêm điểm  
- `n`: polygon mới (≥ 3 điểm)  
- `s`: lưu  
- `q`: thoát  

## Trạng thái dữ liệu

`configs/slots/parking_lot_01.json` hiện **rỗng** (`zones: []`,
`meta.source: "awaiting_calibration"`) — chờ frame thật từ camera bãi xe.
Hệ thống chạy bình thường với 0 ô đỗ: overlay không vẽ polygon, minimap
trắng, KPI = 0/0, health vẫn HEALTHY.

## Checklist review

- [x] Schema đã định nghĩa
- [x] CLI đã mô tả

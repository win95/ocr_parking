# Module tracking

**Trạng thái:** Đã triển khai  
**Code:** `smart_parking.tracking`

## Smoother

Deque độ dài `window`; occupied nếu ≥ `t_on` phiếu; free nếu ≤ `window - t_off` (hysteresis).

## MOT

Ghép IoU; coast tối đa `coast_frames` khi mất detection.

## Coasting → slot

`pipeline/coasting.py` gắn cờ coasting lên slot khi track coasting nằm trong polygon.

## Checklist review

- [x] Tham số khớp config
- [x] Test trong `test_smoother.py`

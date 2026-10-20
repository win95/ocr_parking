# Module analytics

**Trạng thái:** Đã triển khai  
**Code:** `smart_parking.analytics`

## KPIEngine

- `occupied_count`, `free_count`, `utilization_pct`
- Sự kiện: `slot_enter`, `slot_exit` → JSONL
- Registry `KPIWidget` cho metric mở rộng

## Hook dwell

Khi `slot_exit`, ghi `dwell_seconds` trong payload.

## Checklist review

- [x] Schema sự kiện
- [x] Protocol widget

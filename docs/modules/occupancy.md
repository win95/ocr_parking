# Module occupancy

**Trạng thái:** Đã triển khai  
**Code:** `smart_parking.occupancy`, `occupancy/engine.py`

## Mapper

Tâm bbox trong polygon → `slot_id`. Lớp xe: `car`, `truck`, `bus`, `motorcycle`, `vehicle` (cấu hình được).

## Trạng thái slot

`FREE` / `OCCUPIED` / `UNKNOWN` / `STALE` qua `SlotStateContract`.

## Checklist review

- [x] Quy tắc center-in-poly
- [x] Lọc class

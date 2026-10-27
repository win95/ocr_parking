# Module analytics

**Trạng thái:** Đã triển khai  
**Code:** `smart_parking.analytics`

## KPIEngine

- `occupied_count`, `free_count`, `utilization_pct`
- Sự kiện: `slot_enter`, `slot_exit` → JSONL
- Registry `KPIWidget` cho metric mở rộng

## Hook dwell

Khi `slot_exit`, ghi `dwell_seconds` trong payload.

## AlertEngine

Bật bằng `analytics.alerts.enabled`. Mỗi cảnh báo được ghi JSONL **và**
đẩy vào `INSPECTOR_STORE` để dashboard hiển thị (`/api/alerts`, `alerts`
trong `/api/state`). Cooldown mặc định 30 s cho mỗi mã.

| Mã | Điều kiện |
|----|-----------|
| `ingest_degraded` / `ingest_unhealthy` | trạng thái ingest |
| `model_unhealthy` | lỗi inference |
| `slot_stale` | slot STALE (khi có calibration) |
| `utilization_high` | `utilization_pct_threshold` |
| `gpu_temp_high` | `gpu_temp_c_threshold` (mặc định tắt) |
| `vram_high` | `vram_pct_threshold` (mặc định tắt) |
| `ram_high` | `ram_pct_threshold` (mặc định tắt) |
| `pipeline_started` | info, phát lúc khởi động |

## Checklist review

- [x] Schema sự kiện
- [x] Protocol widget
- [x] Cảnh báo ra web + JSONL

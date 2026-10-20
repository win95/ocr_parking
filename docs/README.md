# Tài liệu — Phân tích bãi đỗ xe thông minh

Mục lục tài liệu (documentation-first). Cập nhật **Trạng thái** khi hoàn thành.

| Tài liệu | Trạng thái |
|----------|------------|
| [00-overview.md](00-overview.md) | Sẵn sàng |
| [01-glossary.md](01-glossary.md) | Sẵn sàng |
| [02-architecture.md](02-architecture.md) | Sẵn sàng |
| [03-configuration.md](03-configuration.md) | Sẵn sàng |
| [04-slot-calibration.md](04-slot-calibration.md) | Sẵn sàng |
| [PIPELINE_ARCHITECTURE.md](PIPELINE_ARCHITECTURE.md) | Sẵn sàng |
| [TECH_STACK.md](TECH_STACK.md) | Sẵn sàng |
| [setup/HARDWARE.md](setup/HARDWARE.md) | Sẵn sàng |
| [setup/ubuntu-gpu.md](setup/ubuntu-gpu.md) | Sẵn sàng |
| [setup/VERSIONS.md](setup/VERSIONS.md) | Sẵn sàng |
| [setup/TROUBLESHOOTING.md](setup/TROUBLESHOOTING.md) | Sẵn sàng |
| [setup/READINESS-CHECKLIST.md](setup/READINESS-CHECKLIST.md) | Sẵn sàng |
| [setup/DEPLOYMENT_SERVER_CLIENT.md](setup/DEPLOYMENT_SERVER_CLIENT.md) | Sẵn sàng |
| [setup/SCENARIO_B_LAPTOP_CLIENT.md](setup/SCENARIO_B_LAPTOP_CLIENT.md) | Sẵn sàng |
| [modules/ingest.md](modules/ingest.md) | Đã triển khai |
| [modules/detection.md](modules/detection.md) | Đã triển khai |
| [modules/occupancy.md](modules/occupancy.md) | Đã triển khai |
| [modules/tracking.md](modules/tracking.md) | Đã triển khai |
| [modules/analytics.md](modules/analytics.md) | Đã triển khai |
| [modules/ui.md](modules/ui.md) | Đã triển khai |
| [ml/dataset.md](ml/dataset.md) | Sẵn sàng |
| [ml/training.md](ml/training.md) | Sẵn sàng |
| [ml/evaluation.md](ml/evaluation.md) | Sẵn sàng |
| [ops/runbook.md](ops/runbook.md) | Đã triển khai |
| [ops/benchmarking.md](ops/benchmarking.md) | Đã triển khai |
| [ops/security.md](ops/security.md) | Sẵn sàng |
| [roadmap/phase2-detr-fusion.md](roadmap/phase2-detr-fusion.md) | Sẵn sàng |
| [roadmap/phase2-minimap-3d.md](roadmap/phase2-minimap-3d.md) | Sẵn sàng |

## Cách đọc

1. Tổng quan và kiến trúc để nắm bức tranh lớn.
2. `setup/` trước khi cài GPU trên Ubuntu.
3. `03-configuration` và `04-slot-calibration` trước khi chạy app.
4. `modules/` tương ứng `src/smart_parking/`.
5. `ops/runbook.md` cho vận hành hàng ngày.
6. Triển khai server + laptop: `setup/SCENARIO_B_LAPTOP_CLIENT.md`.

# Đo hiệu năng

**Trạng thái:** Đã triển khai

```bash
python scripts/benchmark_fps.py --config configs/default.yaml --seconds 30
```

Báo latency mean/p50/p95 (ms) và FPS. Dùng SSD local cho nguồn video.

Warmup: 50 frame trước khi đo.

## Checklist review

- [x] Quy trình đã mô tả

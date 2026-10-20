# Đánh giá

**Trạng thái:** Sẵn sàng

## Metric

- mAP@0.5 trên tập validation.
- **Recall cấp slot:** tỷ lệ slot occupied có ≥ 1 detection (tâm trong polygon).

## Quy trình

1. Video hold-out có nhãn slot theo frame (lấy mẫu).
2. Chạy pipeline; so sánh trạng thái đã làm mượt với nhãn.
3. Ghi confusion theo zone.

## Checklist review

- [x] Metric cấp slot đã định nghĩa

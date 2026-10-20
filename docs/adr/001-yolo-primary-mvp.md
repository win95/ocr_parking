# ADR 001: YOLO11 làm detector chính cho MVP

**Trạng thái:** Chấp nhận  
**Ngày:** 2026-03-20

## Bối cảnh

DETR mạnh nhưng chậm hơn trên edge. MVP hướng TensorRT real-time trên Ubuntu + GPU.

## Quyết định

Dùng YOLO11 (Ultralytics) làm detector production duy nhất trong MVP. DETR để giai đoạn 2.

## Hệ quả

- Đường export TRT ngắn, vận hành đơn giản.
- Giai đoạn 2 cần `FusionPolicy` và weights model thứ hai.

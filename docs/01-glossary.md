# Thuật ngữ

**Trạng thái:** Sẵn sàng

| Thuật ngữ | Định nghĩa |
|-----------|------------|
| Slot | Chỗ đỗ được định nghĩa bằng polygon trong tọa độ ảnh. |
| Occupied (đã chiếm) | Trạng thái slot: có xe sau làm mượt. |
| Free (trống) | Không có xe gắn ổn định với slot. |
| Coasting | Trạng thái MOT: duy trì track khi thiếu detection vài frame. |
| Utilization | `occupied_count / total_slots * 100`. |
| Anti-flicker | Hysteresis + bỏ phiếu đa số theo frame cho mỗi slot. |
| DETR | Detection Transformer (giai đoạn 2). |
| TensorRT | Runtime inference NVIDIA (file `.engine`). |
| imgsz | Kích thước input model (vd. 640). |
| Dwell time | Thời gian xe ở trong slot (hook analytics). |
| Turnover | Số xe/giờ theo zone (KPI giai đoạn 2). |

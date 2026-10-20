# Tổng quan

**Trạng thái:** Sẵn sàng triển khai  
**Phạm vi:** MVP sản phẩm

## Tầm nhìn

Phân tích bãi đỗ xe bằng AI: đếm chỗ trống/đã chiếm thời gian thực, tracking ổn định dưới chói sáng/che khuất, giao diện analytics OpenCV, inference sẵn sàng TensorRT trên Ubuntu + GPU NVIDIA.

## Phạm vi MVP

- Nguồn file video và webcam USB.
- Detector chính YOLO11 (PyTorch hoặc TensorRT).
- Polygon slot từ JSON; công cụ calibrate.
- Làm mượt thời gian và MOT nhẹ có coasting.
- Panel analytics: tổng, % sử dụng, FPS, hook dwell.
- Export ONNX / script build TensorRT.

## Ngoài MVP (giai đoạn 2)

- Fusion DETR + YOLO aerial.
- Minimap 3D với cột mật độ.
- RTSP đa camera, API REST/WebSocket.

## Đối tượng sử dụng

- **Vận hành:** theo dõi occupancy tại hiện trường.
- **Kỹ sư:** calibrate slot, tinh chỉnh model, benchmark FPS.
- **Tích hợp:** đọc log KPI (CSV/JSON) cho dashboard.

## Use case

1. Bãi xe campus — % sử dụng theo zone.
2. Sự kiện — occupancy giờ cao điểm.
3. Bán lẻ — turnover và dwell (hook MVP, widget đầy đủ giai đoạn 2).

## Checklist review

- [x] Ranh giới MVP rõ
- [x] Giai đoạn 2 được ghi chú
- [x] Nền tảng: Ubuntu + GPU NVIDIA

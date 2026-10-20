# Công nghệ sử dụng

| Lớp | Công nghệ |
|-----|-----------|
| Ngôn ngữ | Python 3.10+ |
| ML — phát hiện xe | **Ultralytics YOLO11**, PyTorch |
| ML — tùy chọn | **DETR-R50-DC5** (`facebook/detr-resnet-50-dc5`) qua **Transformers** |
| Tăng tốc inference | **TensorRT** / ONNX, NVIDIA CUDA |
| Video & UI desktop | **OpenCV** |
| Số học / ảnh | **NumPy**, **Pillow** |
| Cấu hình & hợp đồng | **Pydantic**, **PyYAML** |
| Tracking | IoU tracker tùy chỉnh + làm mượt theo slot |
| Analytics | Log JSONL, widget KPI |
| Pipeline Inspector | **FastAPI**, **Uvicorn** (extra `inspector`) |
| Stream client (kịch bản B) | **ffmpeg**, **MediaMTX** (RTSP) |
| Huấn luyện | **Roboflow** (tùy chọn) |
| Giám sát | `logging` JSON, **psutil**, `INSPECTOR_STORE` |
| Kiểm thử | **pytest** |
| Hệ điều hành | **Ubuntu** + **NVIDIA GPU** (server); laptop client không cần GPU |

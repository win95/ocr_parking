# Xử lý sự cố

**Trạng thái:** Sẵn sàng

## libcuda.so not found

- Cài lại driver; kiểm tra `nvidia-smi`.
- Kiểm tra `LD_LIBRARY_PATH` có `/usr/local/cuda/lib64`.

## CUDA / PyTorch không khớp

- Cài wheel PyTorch khớp phiên bản CUDA hệ thống.

## OpenCV: không mở được display

- Cài `libgtk-3-0`; cần `DISPLAY` (local hoặc X11 forward).
- Headless: `ui.enabled: false`.

## Webcam bận

- Đóng app khác dùng `/dev/video0`.
- `v4l2-ctl --list-devices`

## Build TensorRT thất bại

- Khớp ONNX opset và `imgsz` cố định.
- `trtexec` trong PATH.

## Server không kéo RTSP từ laptop

- Ping laptop; mở firewall cổng 8554.
- `ffprobe -rtsp_transport tcp rtsp://IP:8554/parking`
- MediaMTX đang chạy trên laptop.

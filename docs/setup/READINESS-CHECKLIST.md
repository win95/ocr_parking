# Checklist sẵn sàng

**Trạng thái:** Sẵn sàng

| # | Kiểm tra | Lệnh |
|---|----------|------|
| 1 | Driver | `nvidia-smi` |
| 2 | PyTorch GPU | `python -c "import torch; print(torch.cuda.is_available())"` |
| 3 | Ultralytics | `yolo predict model=yolo11n.pt source=bus.jpg device=0` |
| 4 | OpenCV | `python -c "import cv2; print(cv2.__version__)"` |
| 5 | Video | `ffprobe data/sample.mp4` |
| 6 | Webcam | `ls /dev/video*` |
| 7 | TensorRT | `trtexec --version` |
| 8 | Dung lượng | `df -h .` ≥ 50 GB trống |

Tự động: `python scripts/verify_gpu_ready.py`

**Laptop client (B):** `ffprobe` RTSP local; **Server:** `ffprobe` tới IP laptop.

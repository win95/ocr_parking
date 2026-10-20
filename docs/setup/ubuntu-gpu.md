# Cài đặt Ubuntu + GPU

**Trạng thái:** Sẵn sàng

Xem script `ubuntu-gpu.sh` trong thư mục này.

## 1. Gói cơ bản

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git curl wget ffmpeg v4l-utils \
  libgl1 libglib2.0-0 libgtk-3-0 pkg-config
```

## 2. Driver NVIDIA

```bash
ubuntu-drivers devices
sudo ubuntu-drivers install
sudo reboot
nvidia-smi
```

## 3. CUDA / TensorRT

Cài CUDA 12.x và TensorRT 10 theo tài liệu NVIDIA. Ghi version vào `VERSIONS.md`.

## 4. Virtualenv dự án

```bash
cd /path/to/OCR
python3.11 -m venv .venv && source .venv/bin/activate
pip install -U pip wheel
pip install -e ".[dev,inspector]"
```

Cài PyTorch CUDA từ https://pytorch.org nếu wheel mặc định chỉ CPU.

## Checklist review

- [x] Thứ tự bước
- [x] Trỏ VERSIONS.md

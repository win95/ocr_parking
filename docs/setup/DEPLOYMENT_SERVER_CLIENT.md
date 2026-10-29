# Triển khai Server + Client

> **Hướng dẫn hợp nhất (setup + chạy + tra cứu script):** [RUN_AND_SETUP.md](RUN_AND_SETUP.md).
>
> **Triển khai chính:** [SCENARIO_B_LAPTOP_CLIENT.md](SCENARIO_B_LAPTOP_CLIENT.md) — **Server GPU** + **laptop client** (webcam hoặc **video MP4** qua RTSP).

Pipeline chạy trên **server**; **client** chỉ cung cấp video (RTSP / file copy).

```mermaid
flowchart LR
  subgraph client [Máy_client]
    Cam[Camera_hoac_MP4]
    FF[ffmpeg_RTSP]
    Cam --> FF
  end
  subgraph server [Server_GPU]
    App[smart_parking]
    Insp[Inspector_8765]
    App --> Insp
  end
  FF -->|RTSP| App
```

## Chọn kịch bản

| ID | Mô tả | Client | Server |
|----|--------|--------|--------|
| **A** | Edge — tất cả trên một máy | Camera + GPU + app | Không dùng |
| **B** | Tập trung — **khuyến nghị** | Laptop phát RTSP | GPU + `rtsp://client/...` |
| **C** | File trên server | `scp` video | `data/*.mp4` |

**Profile server:** `configs/deploy/server.yaml` — headless (`ui.enabled: false`), Inspector metric-only (không stream ảnh). Demo OpenCV trên server: `configs/deploy/server.view.yaml`.

---

## Mạng

| Cổng | Hướng | Dịch vụ |
|------|--------|---------|
| 8554/TCP | Laptop → LAN | RTSP (MediaMTX) |
| 8765/TCP | LAN / VPN | Pipeline Inspector (allowlist + token tùy chọn) |
| 22/TCP | Quản trị | SSH |

RTSP chỉ trong VLAN. Inspector mặc định localhost; khi mở LAN phải đặt
`inspector.allow_networks` đúng subnet và nên dùng token — xem
[security.md](../ops/security.md).

---

## Kịch bản A — Edge (một máy có GPU)

```bash
sudo bash docs/setup/ubuntu-gpu.sh
bash scripts/setup_client.sh --role edge --install-app
source .venv/bin/activate
pip install -e ".[dev,inspector]"
python scripts/verify_gpu_ready.py
python -m smart_parking --config configs/deploy/edge.yaml --source webcam:0
```

Config: [`configs/deploy/edge.yaml`](../../configs/deploy/edge.yaml).

---

## Kịch bản B — Chi tiết

Xem [SCENARIO_B_LAPTOP_CLIENT.md](SCENARIO_B_LAPTOP_CLIENT.md).

Tóm tắt:

**Laptop:** `bash scripts/client_laptop_start.sh webcam` hoặc `video /path/demo.mp4`  
**Server:** `configs/deploy/server-rtsp.yaml` → `server.local.yaml` + `bash scripts/server_start_rtsp.sh`

---

## Kịch bản C — File trên server

```bash
scp parking_demo.mp4 user@SERVER:/opt/smart-parking/data/
python -m smart_parking --config configs/deploy/server-file-local.yaml
```

---

## Systemd (tùy chọn)

```bash
sudo cp deploy/systemd/smart-parking-server.service /etc/systemd/system/
sudo systemctl enable --now smart-parking-server
```

Client: `deploy/systemd/rtsp-publish.service`

---

## Checklist sau setup

| # | Client / Laptop | Server |
|---|-----------------|--------|
| 1 | `v4l2-ctl` hoặc file MP4 OK | `nvidia-smi` OK |
| 2 | `ffprobe` RTSP local OK | `ffprobe` tới laptop OK |
| 3 | Firewall 8554 | `verify_gpu_ready.py` OK |
| 4 | Ghi resolution/FPS | `slots.json` khớp stream |
| 5 | — | Inspector + `logs/events.jsonl` |

---

## Khắc phục sự cố

| Triệu chứng | Gợi ý |
|-------------|--------|
| Server không mở RTSP | Ping laptop, firewall 8554 |
| FPS thấp | Giảm resolution laptop; TensorRT server |
| Slot lệch | Calibrate đúng resolution stream |
| Inspector trống log | `inspector.enabled: true`; app đang chạy |

Xem: [TROUBLESHOOTING.md](TROUBLESHOOTING.md), [HARDWARE.md](HARDWARE.md).

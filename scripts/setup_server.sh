#!/usr/bin/env bash
# =============================================================================
#  setup_server.sh — cài đặt máy SERVER GPU cho Smart Parking (kịch bản B)
#
#  Chạy từ thư mục gốc repo:
#    bash scripts/setup_server.sh
#    bash scripts/setup_server.sh --rtsp rtsp://192.168.100.234:8554/parking
#    bash scripts/setup_server.sh --systemd --start -y
#    bash scripts/setup_server.sh --check
#
#  Script làm được:
#    1. apt packages (ffmpeg, OpenCV libs, python3-venv, build tools)
#    2. kiểm tra NVIDIA driver (nvidia-smi)
#    3. tạo .venv + pip
#    4. cài PyTorch bản CUDA phù hợp (cu121 cho py3.8, cu124 cho py>=3.9)
#    5. cài smart-parking [dev,inspector,detr]
#    6. tạo config local với source RTSP (tuỳ chọn)
#    7. kiểm tra GPU + đọc thử RTSP
#    8. cài systemd service tự restart (tuỳ chọn)
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ------------------------------- defaults ------------------------------------
CONFIG="configs/deploy/server.detr.yaml"
LOCAL_CONFIG="configs/deploy/server.local.yaml"
RTSP_URL=""
TORCH_VARIANT="auto"
DO_APT=1
DO_SYSTEMD=0
DO_START=0
ONLY_CHECK=0
FORCE_CONFIG=0
RECREATE_VENV=0
USE_DISPLAY=1
DISPLAY_VALUE=":0"
ASSUME_YES=0

if [[ -t 1 ]]; then
  C=$'\033[1;36m'; Y=$'\033[1;33m'; R=$'\033[1;31m'; N=$'\033[0m'
else
  C=""; Y=""; R=""; N=""
fi

say()  { printf '%s\n' "$*"; }
step() { printf '\n%s==> %s%s\n' "$C" "$*" "$N"; }
warn() { printf '%sWARN:%s %s\n' "$Y" "$N" "$*" >&2; }
die()  { printf '%sERROR:%s %s\n' "$R" "$N" "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

usage() {
  cat <<'EOF'
Cài đặt một lệnh cho máy SERVER GPU (Ubuntu) — Smart Parking.

Usage: bash scripts/setup_server.sh [options]

  --config PATH        Config nền (mặc định: configs/deploy/server.detr.yaml)
  --rtsp URL           Ghi source RTSP vào config local (configs/deploy/server.local.yaml)
  --torch VARIANT      auto | cu121 | cu124 | cpu | skip   (mặc định: auto)
  --no-apt             Không cài gói apt
  --recreate           Xoá .venv rồi tạo lại
  --systemd            Cài systemd service + enable + start (tự restart khi crash)
  --start              Khởi động pipeline ở nền sau khi cài
  --no-display         Không set DISPLAY cho service (chạy headless)
  --display VALUE      DISPLAY cho service (mặc định: :0)
  --check              Chỉ kiểm tra môi trường, không cài
  --force-config       Ghi đè config local khi dùng --rtsp
  -y, --yes            Không hỏi xác nhận
  -h, --help           Hiện trợ giúp

Ví dụ:
  bash scripts/setup_server.sh --rtsp rtsp://192.168.100.234:8554/parking -y
  bash scripts/setup_server.sh --systemd --start -y
  bash scripts/setup_server.sh --check
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)       CONFIG="${2:?--config cần đường dẫn}"; shift 2 ;;
    --rtsp)         RTSP_URL="${2:?--rtsp cần URL}"; shift 2 ;;
    --torch)        TORCH_VARIANT="${2:?--torch cần giá trị}"; shift 2 ;;
    --no-apt)       DO_APT=0; shift ;;
    --recreate)     RECREATE_VENV=1; shift ;;
    --systemd)      DO_SYSTEMD=1; DO_START=1; shift ;;
    --start)        DO_START=1; shift ;;
    --no-display)   USE_DISPLAY=0; shift ;;
    --display)      DISPLAY_VALUE="${2:?--display cần giá trị}"; shift 2 ;;
    --check)        ONLY_CHECK=1; shift ;;
    --force-config) FORCE_CONFIG=1; shift ;;
    -y|--yes)       ASSUME_YES=1; shift ;;
    -h|--help)      usage; exit 0 ;;
    *)              printf 'Tham số không hợp lệ: %s\n\n' "$1" >&2; usage; exit 2 ;;
  esac
done

# ------------------------------ helpers --------------------------------------
SUDO=""
if [[ ${EUID} -ne 0 ]]; then
  if have sudo; then SUDO="sudo"; fi
fi

PY=".venv/bin/python"
PIP=("$PY" -m pip)

port_in_use() {
  local port="$1"
  have ss || return 1
  ss -ltn 2>/dev/null | awk 'NR > 1 { print $4 }' | grep -q ":${port}$"
}

inspector_port() {
  local cfg="${1:-$CONFIG}" port=""
  port="$(grep -A6 '^inspector:' "$cfg" 2>/dev/null \
    | awk '/^[[:space:]]*port:/{print $2; exit}' || true)"
  printf '%s\n' "${port:-8765}"
}

config_source() {
  local cfg="${1:-$CONFIG}"
  grep -m1 '^source:' "$cfg" 2>/dev/null | sed 's/^source:[[:space:]]*//' || true
}

probe_rtsp() {
  local url="$1"
  if [[ -z "$url" ]]; then
    warn "Config chưa có source — bỏ qua kiểm tra RTSP."
    return 1
  fi
  if [[ "$url" == *LAPTOP_IP* || "$url" == *CLIENT_IP* ]]; then
    warn "source còn placeholder ($url) — sửa IP laptop trước khi chạy."
    return 1
  fi
  if [[ "$url" != rtsp://* ]]; then
    if [[ -f "$url" ]]; then
      say "  source là file: $url"
    else
      warn "source không phải RTSP và file không tồn tại: $url"
      return 1
    fi
    return 0
  fi
  if ! have ffprobe; then
    warn "Không có ffprobe — bỏ qua kiểm tra RTSP."
    return 0
  fi

  say "  Đọc thử $url ..."
  local out
  if out="$(timeout 15 ffprobe -v error -rtsp_transport tcp -select_streams v:0 \
        -show_entries stream=codec_name,width,height,r_frame_rate \
        -of default=noprint_wrappers=1 "$url" 2>&1)"; then
    printf '%s\n' "$out" | sed 's/^/    /'
    return 0
  fi
  warn "Không đọc được RTSP (client đã bật stream chưa?)."
  printf '%s\n' "$out" | tail -5 | sed 's/^/    /'
  return 1
}

# ------------------------------- --check -------------------------------------
run_check() {
  step "Kiểm tra môi trường server"
  local fail=0

  say "  repo:   $ROOT"
  say "  config: $CONFIG"
  if [[ -f "$CONFIG" ]]; then
    say "  source: $(config_source)"
    say "  inspector port: $(inspector_port "$CONFIG")"
  else
    warn "Không thấy config $CONFIG"
    fail=1
  fi

  if have nvidia-smi; then
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader \
      | sed 's/^/  GPU:    /'
  else
    warn "Không thấy nvidia-smi (chưa cài driver NVIDIA?)"
    fail=1
  fi

  if [[ -x "$PY" ]]; then
    if ! "$PY" - <<'PY'
import sys
print("  python:      ", sys.version.split()[0])
try:
    import torch
    print("  torch:       ", torch.__version__, "| cuda", torch.version.cuda,
          "| available", torch.cuda.is_available())
    if not torch.cuda.is_available():
        sys.exit(1)
except Exception as exc:  # noqa: BLE001
    print("  torch:        LỖI:", exc)
    sys.exit(1)
for name in ("cv2", "ultralytics", "transformers", "timm", "fastapi"):
    try:
        mod = __import__(name)
        print("  %-13s" % (name + ":"), getattr(mod, "__version__", "?"))
    except Exception as exc:  # noqa: BLE001
        print("  %-13s" % (name + ":"), "LỖI:", exc)
        sys.exit(1)
try:
    import smart_parking  # noqa: F401
    print("  smart_parking: OK")
except Exception as exc:  # noqa: BLE001
    print("  smart_parking: LỖI:", exc)
    sys.exit(1)
PY
    then
      fail=1
    fi
  else
    warn "Chưa có .venv — chạy script không kèm --check để cài đặt."
    fail=1
  fi

  local port
  port="$(inspector_port "$CONFIG")"
  if port_in_use "$port"; then
    say "  tiến trình: đang chạy (cổng $port đã mở)"
    curl -fsS --max-time 3 "http://127.0.0.1:${port}/api/state" >/dev/null 2>&1 \
      && say "  /api/state: OK" \
      || warn "/api/state không trả lời trên cổng $port"
  else
    say "  tiến trình: chưa chạy (cổng $port trống)"
  fi

  if [[ -n "$RTSP_URL" ]]; then
    probe_rtsp "$RTSP_URL" || fail=1
  else
    probe_rtsp "$(config_source)" || true
  fi

  echo
  if [[ $fail -eq 0 ]]; then
    say "Kết quả: OK"
  else
    say "Kết quả: có mục cần xử lý (xem WARN ở trên)."
  fi
  return "$fail"
}

if [[ $ONLY_CHECK -eq 1 ]]; then
  run_check && exit 0 || exit 1
fi

# ------------------------------ xác nhận -------------------------------------
say ""
say "Smart Parking — cài đặt SERVER GPU"
say "  repo:   $ROOT"
say "  config: $CONFIG"
if [[ -n "$RTSP_URL" ]]; then
  say "  rtsp:   $RTSP_URL  →  $LOCAL_CONFIG"
else
  say "  rtsp:   (dùng source có sẵn trong config)"
fi
say "  apt:    $([[ $DO_APT -eq 1 ]] && echo có || echo không) | torch: $TORCH_VARIANT | systemd: $([[ $DO_SYSTEMD -eq 1 ]] && echo có || echo không)"
if [[ $ASSUME_YES -eq 0 && -t 0 ]]; then
  read -r -p "Tiếp tục? [y/N] " answer
  [[ "$answer" =~ ^[Yy]$ ]] || { say "Huỷ."; exit 1; }
fi

# ------------------------------- 1. apt --------------------------------------
APT_PKGS=(
  build-essential git curl wget ca-certificates pkg-config
  ffmpeg v4l-utils
  python3-venv python3-dev
  libgl1 libglib2.0-0 libgtk-3-0 libsm6 libxext6 libgomp1 libxcb-xinerama0
)

if [[ $DO_APT -eq 1 ]]; then
  step "Cài gói hệ thống (apt)"
  if [[ -z "$SUDO" && ${EUID} -ne 0 ]]; then
    warn "Không có sudo — bỏ qua apt. Cài thủ công: ${APT_PKGS[*]}"
  else
    $SUDO apt-get update
    $SUDO apt-get install -y "${APT_PKGS[@]}"
  fi
else
  step "Bỏ qua apt (--no-apt)"
fi

# ------------------------------- 2. GPU --------------------------------------
step "Kiểm tra NVIDIA GPU"
if have nvidia-smi; then
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader \
    | sed 's/^/  /'
else
  warn "Không thấy nvidia-smi."
  warn "Cài driver NVIDIA theo docs/setup/ubuntu-gpu.md rồi chạy lại script này."
  warn "Vẫn tiếp tục với PyTorch CPU (chỉ đủ để chạy test)."
fi

[[ -f "$CONFIG" ]] || die "Không thấy config $CONFIG"

# ------------------------------- 3. venv -------------------------------------
step "Tạo virtualenv (.venv)"
if [[ $RECREATE_VENV -eq 1 && -e .venv ]]; then
  say "  Xoá .venv cũ (--recreate)"
  rm -rf .venv
fi
if [[ ! -x "$PY" ]]; then
  python3 -m venv .venv
else
  say "  .venv đã có — dùng lại (--recreate để tạo mới)"
fi
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' \
  || die "Cần Python >= 3.8, đang có $("$PY" -V 2>&1)"

"${PIP[@]}" install -U pip wheel setuptools

# ------------------------------- 4. torch ------------------------------------
step "Cài PyTorch"
variant="$TORCH_VARIANT"
if [[ "$variant" == "auto" ]]; then
  if have nvidia-smi; then
    if "$PY" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 8) else 1)'; then
      variant="cu121"   # wheel CUDA mới nhất còn hỗ trợ Python 3.8
    else
      variant="cu124"
    fi
  else
    variant="cpu"
  fi
fi

case "$variant" in
  cu121|cu124) index="https://download.pytorch.org/whl/${variant}" ;;
  cpu)         index="https://download.pytorch.org/whl/cpu" ;;
  skip)
    say "  Bỏ qua (--torch skip)"
    index=""
    ;;
  *) die "Giá trị --torch không hợp lệ: $variant (auto|cu121|cu124|cpu|skip)" ;;
esac

if [[ -n "$index" ]]; then
  skip_torch=0
  if "$PY" -c 'import torch' >/dev/null 2>&1; then
    cur="$("$PY" -c 'import torch; print(torch.__version__, "cuda=" + str(torch.version.cuda), "avail=" + str(torch.cuda.is_available()))')"
    say "  torch hiện có: $cur"
    if [[ "$variant" == "cpu" ]]; then
      skip_torch=1
    elif "$PY" -c 'import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)' >/dev/null 2>&1; then
      skip_torch=1
    else
      warn "  torch hiện có không dùng được CUDA — cài lại bản $variant"
    fi
  fi
  if [[ $skip_torch -eq 1 ]]; then
    say "  Giữ nguyên torch hiện có."
  else
    "${PIP[@]}" install torch torchvision --index-url "$index"
  fi
fi

# ---------------------------- 5. smart-parking -------------------------------
step "Cài smart-parking (editable: dev, inspector, detr)"
"${PIP[@]}" install -e ".[dev,inspector,detr]"
if [[ -f requirements-gpu.txt ]]; then
  "${PIP[@]}" install -r requirements-gpu.txt
fi

# ------------------------------- 6. config -----------------------------------
step "Chuẩn bị thư mục + config"
mkdir -p data models logs logs/artifacts configs/slots

RUN_CONFIG="$CONFIG"
if [[ -n "$RTSP_URL" ]]; then
  if [[ ! -f "$LOCAL_CONFIG" || $FORCE_CONFIG -eq 1 ]]; then
    cp "$CONFIG" "$LOCAL_CONFIG"
    say "  Tạo $LOCAL_CONFIG từ $CONFIG"
  else
    say "  Dùng lại $LOCAL_CONFIG (--force-config để ghi đè)"
  fi

  escaped="$(printf '%s' "$RTSP_URL" | sed -e 's/[&|\\]/\\&/g')"
  if grep -q '^source:' "$LOCAL_CONFIG"; then
    sed -i -E "s|^source:.*|source: ${escaped}|" "$LOCAL_CONFIG"
  else
    printf 'source: %s\n' "$RTSP_URL" | cat - "$LOCAL_CONFIG" > "${LOCAL_CONFIG}.tmp"
    mv "${LOCAL_CONFIG}.tmp" "$LOCAL_CONFIG"
  fi
  say "  source = $RTSP_URL"
  RUN_CONFIG="$LOCAL_CONFIG"
else
  say "  Config: $RUN_CONFIG (source: $(config_source "$RUN_CONFIG"))"
  say "  Muốn đổi nguồn: sửa 'source:' hoặc chạy lại với --rtsp rtsp://..."
fi

# ------------------------------ 7. kiểm tra ----------------------------------
step "Kiểm tra GPU / thư viện"
"$PY" scripts/verify_gpu_ready.py || warn "verify_gpu_ready.py báo lỗi."

step "Kiểm tra nguồn video"
probe_rtsp "$(grep -m1 '^source:' "$RUN_CONFIG" | sed 's/^source:[[:space:]]*//')" \
  || warn "Chưa đọc được nguồn — kiểm tra lại client/RTSP trước khi demo."

# ------------------------------ 8. systemd -----------------------------------
install_systemd() {
  step "Cài systemd service (tự restart)"
  if [[ -z "$SUDO" && ${EUID} -ne 0 ]]; then
    die "Cần sudo để cài systemd service."
  fi

  local user="${SUDO_USER:-$USER}"
  local home
  home="$(getent passwd "$user" | cut -d: -f6)"
  local unit="/etc/systemd/system/smart-parking-server.service"
  local env_display=""

  if [[ $USE_DISPLAY -eq 1 ]]; then
    env_display="Environment=DISPLAY=${DISPLAY_VALUE}
Environment=XAUTHORITY=${home}/.Xauthority"
  fi

  $SUDO tee "$unit" >/dev/null <<EOF
[Unit]
Description=Smart Parking Analytics (server)
After=network-online.target display-manager.service
Wants=network-online.target display-manager.service

[Service]
Type=simple
User=${user}
WorkingDirectory=${ROOT}
Environment=SMART_PARKING_CONFIG=${RUN_CONFIG}
Environment=PYTHONUNBUFFERED=1
${env_display}
ExecStart=${ROOT}/.venv/bin/python -m smart_parking
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

  $SUDO systemctl daemon-reload
  $SUDO systemctl enable smart-parking-server.service

  if [[ $DO_START -eq 1 ]]; then
    local port
    port="$(inspector_port "$RUN_CONFIG")"
    if port_in_use "$port"; then
      warn "Cổng $port đang được dùng — service sẽ lỗi bind. Dừng instance chạy tay trước:"
      warn "  ps -eo pid,cmd | grep 'smart_parking --config'"
      warn "  kill <PID>"
    fi
    $SUDO systemctl restart smart-parking-server.service
    sleep 5
    $SUDO systemctl --no-pager --lines=5 status smart-parking-server.service || true
  fi

  say "  Unit:   $unit"
  say "  Log:    journalctl -u smart-parking-server -f"
  if [[ $USE_DISPLAY -eq 1 ]]; then
    say "  DISPLAY=${DISPLAY_VALUE} — cần phiên đăng nhập đồ họa đang mở để thấy cửa sổ."
    say "  Chạy không cửa sổ: đặt 'ui.enabled: false' trong config + dùng --no-display."
  fi
}

start_app() {
  step "Khởi động pipeline (nền)"
  local port
  port="$(inspector_port "$RUN_CONFIG")"
  if port_in_use "$port"; then
    warn "Cổng $port đang được dùng — bỏ qua khởi động (đã có instance?)."
    return 0
  fi

  local logfile="logs/app.log"
  if [[ $USE_DISPLAY -eq 1 ]]; then
    setsid env DISPLAY="$DISPLAY_VALUE" "$ROOT/.venv/bin/python" -m smart_parking \
      --config "$RUN_CONFIG" >>"$logfile" 2>&1 < /dev/null &
  else
    setsid "$ROOT/.venv/bin/python" -m smart_parking \
      --config "$RUN_CONFIG" >>"$logfile" 2>&1 < /dev/null &
  fi
  sleep 6

  local pid
  pid="$(pgrep -f "smart_parking --config ${RUN_CONFIG}" | head -1 || true)"
  if [[ -z "$pid" ]]; then
    warn "Không thấy tiến trình sau khi start — xem $logfile"
    return 1
  fi
  if curl -fsS --max-time 3 "http://127.0.0.1:${port}/api/state" >/dev/null 2>&1; then
    say "  Đang chạy (pid $pid) — dashboard OK."
  else
    say "  Đang chạy (pid $pid) — dashboard chưa trả lời, xem $logfile"
  fi
}

if [[ $DO_SYSTEMD -eq 1 ]]; then
  install_systemd
elif [[ $DO_START -eq 1 ]]; then
  start_app || true
fi

# ------------------------------- summary -------------------------------------
port="$(inspector_port "$RUN_CONFIG")"
lan_ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"

step "Hoàn tất"
say "  Repo:       $ROOT"
say "  Config:     $RUN_CONFIG"
say "  Dashboard:  http://${lan_ip:-127.0.0.1}:${port}/"
say "  Log:        logs/app.log (hoặc journalctl -u smart-parking-server -f)"
say ""
say "  Chạy thủ công:"
say "    source .venv/bin/activate"
say "    python -m smart_parking --config $RUN_CONFIG"
say "  Kiểm tra lại:  bash scripts/setup_server.sh --check"

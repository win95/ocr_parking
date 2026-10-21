#!/usr/bin/env bash
# Server — hiển thị camera của client laptop lên màn hình server
#
# Usage:
#   bash scripts/server_show_camera.sh          # ffplay: camera thô (không overlay)
#   bash scripts/server_show_camera.sh --app    # app smart_parking: camera + YOLO + occupancy + minimap
#   bash scripts/server_show_camera.sh --both   # cả hai
#
# Env:
#   RTSP_URL     URL RTSP từ client (mặc định: lấy `source` trong config)
#   CFG          config dùng cho app (mặc định configs/deploy/server.view.yaml)
#   DISPLAY      X display của server (mặc định :0)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CFG="${CFG:-configs/deploy/server.view.yaml}"
export DISPLAY="${DISPLAY:-:0}"

# python trong venv nếu có, không thì python3 hệ thống
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="$(command -v python3 || command -v python)"
fi
if [[ -z "$PY" ]]; then
  echo "Không tìm thấy python — cài: bash scripts/setup_server.sh"
  exit 1
fi

MODE="ffplay"
if [[ "${1:-}" == "--app" ]]; then MODE="app"; fi
if [[ "${1:-}" == "--both" ]]; then MODE="both"; fi

# --- 1. lấy URL RTSP -------------------------------------------------------
if [[ -z "${RTSP_URL:-}" ]]; then
  if [[ -f "$CFG" ]]; then
    RTSP_URL="$("$PY" -c "import yaml,sys; print(yaml.safe_load(open(sys.argv[1]))['source'])" "$CFG")"
  else
    echo "Thiếu config $CFG — đặt RTSP_URL=... hoặc tạo config."
    exit 1
  fi
fi
echo "RTSP: $RTSP_URL"

# --- 2. kiểm tra stream ----------------------------------------------------
if ! command -v ffprobe >/dev/null 2>&1; then
  echo "Thiếu ffprobe — cài: sudo apt install ffmpeg   (hoặc: bash scripts/client_prepare_local.sh)"
  exit 1
fi
if ! ffprobe -rtsp_transport tcp -v error -select_streams v:0 \
     -show_entries stream=codec_name,width,height -of csv=p=0 "$RTSP_URL"; then
  echo "Không tới được RTSP. Kiểm tra client đã chạy MediaMTX + publisher chưa?"
  exit 1
fi

mkdir -p "$ROOT/logs"

# --- 3. đưa cửa sổ lên trước ----------------------------------------------
# Lưu ý: với GNOME/Mutter, chỉ "raise" (restack) có thể không đủ — compositor
# vẫn giữ texture cũ của cửa sổ. Nên ta unmap → map lại rồi activate.
raise_window() {
  local title="$1"
  if "$PY" -c "import Xlib" 2>/dev/null; then
    "$PY" "$ROOT/scripts/raise_window.py" "$title" --remap && return 0
  fi
  if command -v xdotool >/dev/null 2>&1; then
    local wid
    wid="$(xdotool search --name "$title" | tail -1)"
    if [[ -n "$wid" ]]; then
      xdotool windowunmap "$wid" 2>/dev/null || true
      sleep 0.5
      xdotool windowmap "$wid" 2>/dev/null || true
      xdotool windowactivate --sync "$wid" 2>/dev/null || true
      return 0
    fi
  fi
  if command -v wmctrl >/dev/null 2>&1; then
    wmctrl -a "$title" 2>/dev/null || true
    return 0
  fi
  echo "  (không có python-xlib/xdotool/wmctrl — cửa sổ có thể bị che;"
  echo "   thủ công: xdotool search --name \"$title\" windowactivate)"
}

# --- 4. ffplay: camera thô -------------------------------------------------
if [[ "$MODE" == "ffplay" || "$MODE" == "both" ]]; then
  if ! command -v ffplay >/dev/null 2>&1; then
    echo "Thiếu ffplay — cài: sudo apt install ffmpeg"
  else
    echo "Mở ffplay: camera thô từ client."
    nohup ffplay -rtsp_transport tcp \
      -window_title "SERVER - parking camera (RTSP from client)" \
      -i "$RTSP_URL" >"$ROOT/logs/ffplay_server.log" 2>&1 &
    sleep 2
    raise_window "SERVER - parking camera"
  fi
fi

# --- 5. app smart_parking: camera + overlay + minimap ----------------------
if [[ "$MODE" == "app" || "$MODE" == "both" ]]; then
  if [[ ! -f "$CFG" ]]; then
    echo "Thiếu config $CFG"
    exit 1
  fi
  echo "Chạy app (camera + overlay + minimap) với $CFG"
  nohup "$PY" -m smart_parking --config "$CFG" >"$ROOT/logs/app_view.log" 2>&1 &
  sleep 3
  raise_window "Smart Parking"
fi

echo "OK. Đóng cửa sổ: nhấn 'q' trong cửa sổ ffplay, hoặc Ctrl-C trong app."

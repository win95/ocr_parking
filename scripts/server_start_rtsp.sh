#!/usr/bin/env bash
# Server — smart_parking (RTSP) + tùy chọn MLflow UI
#
#   bash scripts/server_start_rtsp.sh
#   bash scripts/server_start_rtsp.sh --with-mlflow
#   bash scripts/server_start_rtsp.sh --mlflow-only
#
# Env:
#   SMART_PARKING_CONFIG   default configs/deploy/server.local.yaml
#   MLFLOW_TRACKING_URI    default $ROOT/mlruns
#   MLFLOW_EXPERIMENT_NAME default smart-parking
#   MLFLOW_UI_HOST         default 127.0.0.1
#   MLFLOW_UI_PORT         default 5000
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CFG="${SMART_PARKING_CONFIG:-configs/deploy/server.local.yaml}"
WITH_MLFLOW=0
MLFLOW_ONLY=0
SKIP_APP=0

for arg in "$@"; do
  case "$arg" in
    --with-mlflow) WITH_MLFLOW=1 ;;
    --mlflow-only) WITH_MLFLOW=1; MLFLOW_ONLY=1; SKIP_APP=1 ;;
    -h|--help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (use --help)"
      exit 1
      ;;
  esac
done

MLFLOW_TRACKING_URI="${MLFLOW_TRACKING_URI:-$ROOT/mlruns}"
MLFLOW_EXPERIMENT_NAME="${MLFLOW_EXPERIMENT_NAME:-smart-parking}"
MLFLOW_UI_HOST="${MLFLOW_UI_HOST:-127.0.0.1}"
MLFLOW_UI_PORT="${MLFLOW_UI_PORT:-5000}"
MLFLOW_PID=""

cleanup() {
  if [[ -n "$MLFLOW_PID" ]] && kill -0 "$MLFLOW_PID" 2>/dev/null; then
    kill "$MLFLOW_PID" 2>/dev/null || true
    wait "$MLFLOW_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

start_mlflow_ui() {
  if ! command -v mlflow >/dev/null 2>&1; then
    echo "MLflow not installed. Run: pip install -e \".[mlflow]\""
    exit 1
  fi
  mkdir -p "$MLFLOW_TRACKING_URI" logs
  export MLFLOW_TRACKING_URI MLFLOW_EXPERIMENT_NAME
  echo "MLflow tracking: $MLFLOW_TRACKING_URI (experiment: $MLFLOW_EXPERIMENT_NAME)"
  mlflow ui \
    --host "$MLFLOW_UI_HOST" \
    --port "$MLFLOW_UI_PORT" \
    --backend-store-uri "$MLFLOW_TRACKING_URI" \
    >"$ROOT/logs/mlflow_ui.log" 2>&1 &
  MLFLOW_PID=$!
  sleep 1
  if ! kill -0 "$MLFLOW_PID" 2>/dev/null; then
    echo "MLflow UI failed — see logs/mlflow_ui.log"
    exit 1
  fi
  echo "MLflow UI: http://${MLFLOW_UI_HOST}:${MLFLOW_UI_PORT}/"
}

if [[ "$WITH_MLFLOW" -eq 1 ]]; then
  start_mlflow_ui
fi

if [[ "$SKIP_APP" -eq 1 ]]; then
  echo "MLflow-only mode — Ctrl+C to stop."
  wait "$MLFLOW_PID"
  exit 0
fi

if [[ ! -f "$CFG" ]]; then
  echo "Create $CFG from configs/deploy/server-rtsp.yaml and set client IP"
  exit 1
fi

if grep -qE 'LAPTOP_IP|CLIENT_IP' "$CFG"; then
  echo "Replace LAPTOP_IP/CLIENT_IP in $CFG with client LAN address"
  exit 1
fi

source .venv/bin/activate
RTSP_URL="$(python -c "import yaml; print(yaml.safe_load(open('$CFG'))['source'])")"
echo "Probing $RTSP_URL ..."
ffprobe -rtsp_transport tcp -v error -select_streams v:0 -show_entries stream=codec_name,width,height -of csv=p=0 "$RTSP_URL" || {
  echo "Cannot reach RTSP. Start laptop client first."
  exit 1
}
export MLFLOW_TRACKING_URI MLFLOW_EXPERIMENT_NAME
exec python -m smart_parking --config "$CFG"

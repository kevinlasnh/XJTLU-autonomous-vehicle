#!/bin/bash
set -euo pipefail

DEFAULT_HOST="jetson@100.97.227.24"
DEFAULT_INDOOR_WIFI="XJTLU"
DEFAULT_OUTDOOR_WIFI="Pixel"
LOG_FILE="/tmp/wifi-switch.log"
RECONNECT_WAIT_SECONDS=12
RETRY_WAIT_SECONDS=10
MAX_RETRIES=2

MODE=""
HOST="$DEFAULT_HOST"
STATUS_ONLY=0
TARGET_INPUT=""

usage() {
  cat <<'EOF'
Usage:
  bash scripts/switch_jetson_wifi.sh [target]
  bash scripts/switch_jetson_wifi.sh --status
  bash scripts/switch_jetson_wifi.sh [target] --host <user@host>
  bash scripts/switch_jetson_wifi.sh [target] --local

Targets:
  outdoor | 手机 | 热点 | Pixel  -> Pixel
  indoor  | 学校 | XJTLU | 回去了 -> XJTLU
  toggle  | (no argument)          -> XJTLU <-> Pixel
  any other string                 -> use as NetworkManager connection name

Notes:
  - On a workstation, the script uses Tailscale SSH to switch Jetson WiFi remotely.
  - On Jetson itself, the script schedules the switch locally and may drop the current SSH shell.
  - Every switch also restarts ToDesk on Jetson.
EOF
}

is_local_jetson() {
  [[ -f /etc/nv_tegra_release ]] || grep -qi "jetson" /proc/device-tree/model 2>/dev/null
}

run_active_wifi_query() {
  nmcli -t -f NAME,TYPE,DEVICE connection show --active | grep ':wireless:' | cut -d: -f1,3 | head -1 || true
}

run_active_wifi_name_query() {
  nmcli -t -f NAME,TYPE connection show --active | grep ':wireless$' | cut -d: -f1 | head -1 || true
}

run_remote_query() {
  local command="$1"
  ssh -o ConnectTimeout=10 "$HOST" "$command"
}

current_wifi_line() {
  if [[ "$MODE" == "local" ]]; then
    run_active_wifi_query
  else
    run_remote_query "nmcli -t -f NAME,TYPE,DEVICE connection show --active | grep ':wireless:' | cut -d: -f1,3 | head -1 || true"
  fi
}

current_wifi_name() {
  if [[ "$MODE" == "local" ]]; then
    run_active_wifi_name_query
  else
    run_remote_query "nmcli -t -f NAME,TYPE connection show --active | grep ':wireless$' | cut -d: -f1 | head -1 || true"
  fi
}

resolve_target() {
  local requested="$1"
  local current="$2"

  case "$requested" in
    ""|"toggle")
      if [[ "$current" == "$DEFAULT_INDOOR_WIFI" ]]; then
        echo "$DEFAULT_OUTDOOR_WIFI"
      else
        echo "$DEFAULT_INDOOR_WIFI"
      fi
      ;;
    outdoor|Outdoor|OUTDOOR|手机|热点|Pixel|pixel|PIXEL|phone|Phone)
      echo "$DEFAULT_OUTDOOR_WIFI"
      ;;
    indoor|Indoor|INDOOR|学校|XJTLU|xjtlu|回去了|campus|Campus)
      echo "$DEFAULT_INDOOR_WIFI"
      ;;
    *)
      echo "$requested"
      ;;
  esac
}

schedule_local_switch() {
  local target="$1"
  nohup bash -lc 'sleep 2 && sudo nmcli connection up id "$1" > "$2" 2>&1 && sudo systemctl restart todeskd >> "$2" 2>&1 && systemctl is-active todeskd >> "$2" 2>&1' _ "$target" "$LOG_FILE" >/dev/null 2>&1 &
}

schedule_remote_switch() {
  local target="$1"
  local target_q
  local log_q

  printf -v target_q '%q' "$target"
  printf -v log_q '%q' "$LOG_FILE"

  ssh "$HOST" "nohup bash -lc 'sleep 2 && sudo nmcli connection up id \"\$1\" > \"\$2\" 2>&1 && sudo systemctl restart todeskd >> \"\$2\" 2>&1 && systemctl is-active todeskd >> \"\$2\" 2>&1' _ $target_q $log_q > /dev/null 2>&1 &"
}

print_status() {
  local wifi_line="$1"
  echo "=== Jetson WiFi Status ==="
  echo "Mode: $MODE"
  if [[ "$MODE" == "remote" ]]; then
    echo "Host: $HOST"
  fi
  if [[ -n "$wifi_line" ]]; then
    echo "Active WiFi: $wifi_line"
  else
    echo "Active WiFi: None"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --status)
      STATUS_ONLY=1
      shift
      ;;
    --local)
      MODE="local"
      shift
      ;;
    --remote)
      MODE="remote"
      shift
      ;;
    --host)
      [[ $# -ge 2 ]] || { echo "--host requires an argument" >&2; exit 1; }
      HOST="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      if [[ -n "$TARGET_INPUT" ]]; then
        echo "Only one target argument is supported" >&2
        usage >&2
        exit 1
      fi
      TARGET_INPUT="$1"
      shift
      ;;
  esac
done

if [[ -z "$MODE" ]]; then
  if is_local_jetson; then
    MODE="local"
  else
    MODE="remote"
  fi
fi

CURRENT_WIFI_LINE="$(current_wifi_line)"
CURRENT_WIFI_NAME="$(current_wifi_name)"

print_status "$CURRENT_WIFI_LINE"

if [[ "$STATUS_ONLY" -eq 1 ]]; then
  exit 0
fi

TARGET_WIFI="$(resolve_target "$TARGET_INPUT" "$CURRENT_WIFI_NAME")"

echo "Resolved target: $TARGET_WIFI"
if [[ "$CURRENT_WIFI_NAME" == "$TARGET_WIFI" ]]; then
  echo "Target WiFi is already active; continuing to reinitialize the connection and ToDesk."
fi

if [[ "$MODE" == "local" ]]; then
  schedule_local_switch "$TARGET_WIFI"
  echo "Switch scheduled locally."
  echo "If this shell is over SSH/Tailscale, it may disconnect during handover."
  echo "Switch log: $LOG_FILE"
  echo "After reconnect, verify with:"
  echo "  cat $LOG_FILE"
  echo "  nmcli -t -f NAME,TYPE,DEVICE connection show --active | grep ':wireless:'"
  exit 0
fi

echo "Sending remote switch command..."
schedule_remote_switch "$TARGET_WIFI"
echo "Waiting ${RECONNECT_WAIT_SECONDS}s for Tailscale reconnect..."
sleep "$RECONNECT_WAIT_SECONDS"

for ((attempt = 1; attempt <= MAX_RETRIES; attempt++)); do
  REMOTE_WIFI_LINE="$(current_wifi_line 2>/dev/null || true)"
  REMOTE_WIFI_NAME="$(current_wifi_name 2>/dev/null || true)"
  if [[ "$REMOTE_WIFI_NAME" == "$TARGET_WIFI" ]]; then
    echo "=== WiFi switch OK ==="
    echo "Active WiFi: ${REMOTE_WIFI_LINE:-$REMOTE_WIFI_NAME}"
    run_remote_query "cat $LOG_FILE 2>/dev/null || true" || true
    TODESK_STATE="$(run_remote_query "systemctl is-active todeskd 2>/dev/null || true" || true)"
    if [[ "$TODESK_STATE" == "active" ]]; then
      echo "ToDesk: active"
    else
      echo "ToDesk: $TODESK_STATE"
    fi
    exit 0
  fi

  if [[ "$attempt" -lt "$MAX_RETRIES" ]]; then
    echo "Reconnect check $attempt/$MAX_RETRIES did not reach $TARGET_WIFI yet. Waiting ${RETRY_WAIT_SECONDS}s..."
    sleep "$RETRY_WAIT_SECONDS"
  fi
done

echo "WiFi handover did not confirm target '$TARGET_WIFI' within the retry window." >&2
echo "Last seen active WiFi: ${REMOTE_WIFI_LINE:-None}" >&2
echo "If the link already moved, reconnect and inspect $LOG_FILE on Jetson." >&2
exit 1

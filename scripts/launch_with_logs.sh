#!/bin/bash
set -euo pipefail

MODE="${1:-explore}"
SESSION=$(date +%Y-%m-%d-%H-%M-%S)
SESSION_DIR="$HOME/fyp_runtime_data/logs/$SESSION"
TEGRA_PID=""
CLEANUP_DONE=0

mkdir -p "$SESSION_DIR/console"
mkdir -p "$SESSION_DIR/data"
mkdir -p "$SESSION_DIR/system"
ln -sfn "$SESSION_DIR" "$HOME/fyp_runtime_data/logs/latest"

export ROS_LOG_DIR="$SESSION_DIR/console"
export FYP_LOG_SESSION_DIR="$SESSION_DIR/data"

cleanup() {
  if [[ "$CLEANUP_DONE" == "1" ]]; then
    return
  fi
  CLEANUP_DONE=1

  if [[ -n "${TEGRA_PID:-}" ]]; then
    kill "$TEGRA_PID" 2>/dev/null || true
    wait "$TEGRA_PID" 2>/dev/null || true
  fi

  if [[ -f "$SESSION_DIR/system/session_info.yaml" ]]; then
    echo "end_time: $(date -Iseconds)" >> "$SESSION_DIR/system/session_info.yaml"
  fi
}
trap cleanup EXIT INT TERM

tegrastats --interval 1000 --logfile "$SESSION_DIR/system/tegrastats.log" &
TEGRA_PID=$!

cat > "$SESSION_DIR/system/session_info.yaml" <<EOF
mode: $MODE
start_time: $(date -Iseconds)
session_dir: $SESSION_DIR
git_branch: $(cd ~/fyp_autonomous_vehicle && git branch --show-current 2>/dev/null || echo unknown)
git_commit: $(cd ~/fyp_autonomous_vehicle && git rev-parse --short HEAD 2>/dev/null || echo unknown)
ros_log_dir: $SESSION_DIR/console
data_log_dir: $SESSION_DIR/data
system_log_dir: $SESSION_DIR/system
EOF

echo "=== Log session: $SESSION ==="
echo "  Console: $SESSION_DIR/console/"
echo "  Data:    $SESSION_DIR/data/"
echo "  System:  $SESSION_DIR/system/"
echo "=== Launching mode: $MODE ==="

set +u
source /opt/ros/humble/setup.bash
source ~/fyp_autonomous_vehicle/install/setup.bash
set -u

case "$MODE" in
  slam)         LAUNCH_FILE="system_slam.launch.py" ;;
  explore)      LAUNCH_FILE="system_explore.launch.py" ;;
  corridor)     LAUNCH_FILE="system_gps_corridor.launch.py" ;;
  travel)       LAUNCH_FILE="system_travel.launch.py" ;;
  explore-gps)  LAUNCH_FILE="system_explore_gps.launch.py" ;;
  nav-gps)      LAUNCH_FILE="system_nav_gps.launch.py" ;;
  *)            echo "Unknown mode: $MODE"; exit 1 ;;
esac

LAUNCH_ARGS=()
if [[ "$MODE" == "corridor" ]]; then
  if [[ -n "${FYP_USE_RVIZ:-}" ]]; then
    LAUNCH_ARGS+=("use_rviz:=${FYP_USE_RVIZ}")
  elif [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]]; then
    LAUNCH_ARGS+=("use_rviz:=true")
  else
    LAUNCH_ARGS+=("use_rviz:=false")
  fi
fi

ros2 launch bringup "$LAUNCH_FILE" "${LAUNCH_ARGS[@]}"

#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-$HOME/XJTLU-autonomous-vehicle}"
OUTPUT_ROOT="${1:-$HOME/fyp_runtime_data/bags/run_$(date +%Y%m%d_%H%M%S)}"
BAG_PATH="$OUTPUT_ROOT/rosbag2"

mkdir -p "$OUTPUT_ROOT"
source /opt/ros/humble/setup.bash
source "$WORKSPACE_ROOT/install/setup.bash"

topics=(
  /livox/lidar
  /livox/imu
  /fix
  /gnss
  /fastlio2/lio_odom
  /pgo/optimized_odom
  /tf
  /tf_static
  /cmd_vel
  /pgo/loop_markers
)

echo "Recording bag to $BAG_PATH"
exec ros2 bag record -o "$BAG_PATH" "${topics[@]}"

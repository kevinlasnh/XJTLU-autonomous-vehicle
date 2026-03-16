# CLAUDE.md

## Repository

This is a ROS2 Humble monorepo for an autonomous vehicle on Jetson Orin NX.

## Build

```bash
cd ~/fyp_autonomous_vehicle
colcon build --symlink-install --parallel-workers 1
source install/setup.bash
```

## Structure

- `src/sensor_drivers/` — LiDAR, IMU, GNSS, serial drivers
- `src/perception/` — FAST-LIO2, PGO, pointcloud processing
- `src/planning/` — GPS global path planning, coordinate transforms
- `src/navigation/` — Custom Nav2 plugins
- `src/bringup/` — Launch files, configs, maps, rviz
- `docs/devlog/` — Developer logs

## Critical Rules

1. NEVER modify YAML parameters without documenting the reason
2. ALWAYS use `--parallel-workers 1` for colcon build
3. ROS2 Humble only — clone `humble` branches
4. Nav2 is in `src/third_party/` via dependencies.repos — do NOT modify it

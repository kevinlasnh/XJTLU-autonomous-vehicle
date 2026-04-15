# Launch Memo

## Development Modules

### Highest Priority (Issues requiring immediate resolution, directly impacting system operation)

### Medium Priority (Issues to resolve in the short term, no direct impact on system operation)

### Low Priority (Better if resolved, acceptable if not)

## Miscellaneous
1.

## Console Commands

### Miscellaneous
1. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 launch ros2_launch_file system_entire_launch_pgo.py
2. cd /home/jetson/2025_FYP/car_ws && colcon build --packages-select ros2_launch_file --symlink-install

# Launch Development Log

## 2025.11.11
1. None

## 2025.11.22
1. Confirmed that YAML file parameters in the entire system launch file have been updated
2. Added serial reader node startup to the launch file, to provide lower-level C board odometry data to the `velocity_smoother` node
3. Added a new Nav2 navigation framework launch file

## 2025.12.01
1. Point cloud to scan node has been commented out in the explore launch file, temporarily disabled
2. Nav2 section in the explore launch file temporarily commented out and switched to manual startup for easier debugging

# FYP Autonomous Vehicle

> ROS2 Humble Monorepo for Jetson Orin NX Autonomous Navigation Vehicle

## Quick Start

```bash
# SSH to Jetson
ssh jetson@100.97.227.24

# Enter workspace
cd ~/fyp_autonomous_vehicle

# First-time setup (pull third-party deps + install rosdep)
make setup

# Build all packages
make build

# Source workspace
source install/setup.bash

# Launch (pick one)
make launch-slam      # SLAM mapping mode
make launch-explore   # Real-time obstacle avoidance (main mode)
make launch-travel    # Static map navigation (WIP)
```

## Repository Structure

```
src/
├── sensor_drivers/   Livox LiDAR, WIT IMU, GNSS, serial drivers
├── perception/       FAST-LIO2, PGO, pointcloud processing
├── planning/         GPS global path planning, coordinate transforms
├── navigation/       waypoint_collector, waypoint_nav_tool
├── bringup/          Launch files, Nav2 configs, maps, rviz configs
└── third_party/      Nav2, slam_toolbox (via dependencies.repos)

docs/                 Project documentation (see docs/index.md)
scripts/              Utility scripts (init_runtime_data.sh)
```

## Documentation

See [docs/index.md](docs/index.md) for the full documentation index:
- [System Architecture](docs/architecture.md)
- [Command Reference](docs/commands.md)
- [Development Conventions](docs/conventions.md)
- [Workflow Guide](docs/workflow.md)
- [Known Issues](docs/known_issues.md)
- [FASTLIO2 Algorithm](docs/knowledge/fastlio2.md)
- [PGO Algorithm](docs/knowledge/pgo.md)

## Development Workflow

1. Create branch from `main`: `git checkout -b feature/your-feature`
2. Build & test: `make build && source install/setup.bash`
3. Commit with descriptive English messages
4. Push & create PR: requires review from @kevinlasnh
5. See [docs/workflow.md](docs/workflow.md) for the complete guide

## Hardware

- **Compute**: Jetson Orin NX (16GB RAM, aarch64)
- **LiDAR**: Livox MID360
- **IMU**: WIT BWT901CL
- **GNSS**: RTK module
- **Controller**: PS2 wireless (manual override, highest priority)

## Key Rules

1. **NEVER** modify YAML parameters without documenting the reason
2. **ALWAYS** use `--parallel-workers 1` for colcon build (memory constraint)
3. **ALWAYS** test on the real vehicle before merging
4. **NEVER** push directly to `main` — use Pull Requests

# FYP Autonomous Vehicle

> ROS 2 Humble monorepo for the Jetson Orin NX autonomous vehicle project.

## Current State

- Main deployment target: Jetson Orin NX running Ubuntu 22.04 and ROS 2 Humble
- Main operating mode: `make launch-explore`
- GPS-assisted mode available: `make launch-explore-gps`
- Runtime data lives outside the repo under `~/fyp_runtime_data`
- Runtime parameters are centralized in `src/bringup/config/master_params.yaml`
- Session logs are created by `scripts/launch_with_logs.sh`

## Quick Start

```bash
# SSH to Jetson
ssh jetson@100.97.227.24

# Enter workspace
cd ~/XJTLU-autonomous-vehicle

# First-time setup
make setup
make build
source install/setup.bash
bash scripts/init_runtime_data.sh

# Launch one operating mode
make launch-slam
make launch-explore
make launch-explore-gps
make launch-travel
```

## Repository Structure

```text
src/
├── sensor_drivers/   Livox LiDAR, WIT IMU, GNSS, serial drivers
├── perception/       FAST-LIO2, PGO GPS fusion, pointcloud processing
├── planning/         GNSS global planning, coordinate transforms
├── navigation/       waypoint_collector and navigation tools
├── bringup/          launch files, Nav2 configs, maps, RViz assets
└── third_party/      vendored dependencies from dependencies.repos

docs/                 Active engineering documentation
scripts/              Runtime helpers and data-collection tools
```

## Operating Modes

1. `make launch-slam`
   FAST-LIO2 + PGO + SLAM Toolbox mapping workflow
2. `make launch-explore`
   FAST-LIO2 + PGO + Nav2 local navigation
3. `make launch-explore-gps`
   Explore mode with GNSS bringup and PGO GPS factor enabled
4. `make launch-travel`
   Static-map navigation workflow, currently paused

All four `make launch-*` targets go through `scripts/launch_with_logs.sh`, which creates a per-session log directory under `~/fyp_runtime_data/logs/`.

## Documentation

The active project docs live under [`docs/`](docs/index.md).

- [Documentation Index](docs/index.md)
- [System Architecture](docs/architecture.md)
- [Command Reference](docs/commands.md)
- [Development Conventions](docs/conventions.md)
- [Workflow Guide](docs/workflow.md)
- [Known Issues](docs/known_issues.md)
- [PGO Notes](docs/knowledge/pgo.md)
- [GPS Planning Notes](docs/knowledge/gps_planning.md)

## Development Workflow

1. Sync `main` and create a branch from it.
2. Implement and verify on the branch.
3. Rebuild with `--parallel-workers 1`.
4. `source install/setup.bash` after every build.
5. Push the branch and open a PR to `main`.
6. Merge through PR, then sync Jetson back to `main`.
7. Update affected docs before the session is considered complete.

See [`docs/workflow.md`](docs/workflow.md) for the full executor workflow and documentation trigger rules.

## Hardware Snapshot

- Compute: Jetson Orin NX, 16 GB RAM
- LiDAR: Livox MID360
- IMU: WIT IMU
- GNSS: basic GPS receiver, about 2.5 m class accuracy, no RTK in the current stack
- Drive interface: serial link to STM32 lower controller board
- Manual override: PS2 wireless controller, highest priority

## Key Rules

1. Do not modify tuned YAML parameters without documenting why.
2. Always build with `--parallel-workers 1`.
3. Always source `install/setup.bash` after a build.
4. Do not modify vendored Nav2 under `src/third_party/navigation2`.
5. Do not push directly to `main`; use PRs.

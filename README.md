# FYP Autonomous Vehicle

> ROS 2 Humble monorepo for the Jetson Orin NX autonomous vehicle project.

## Current State

- Main deployment target: Jetson Orin NX running Ubuntu 22.04 and ROS 2 Humble
- Main operating mode: `make launch-explore`
- GPS-assisted mode available: `make launch-explore-gps`
- Runtime data lives inside the workspace under `~/XJTLU-autonomous-vehicle/runtime-data`
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

docs-CN/              Active engineering documentation (Chinese)
docs-EN/              Active engineering documentation (English)
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

All four `make launch-*` targets go through `scripts/launch_with_logs.sh`, which creates a per-session log directory under `~/XJTLU-autonomous-vehicle/runtime-data/logs/`.

## Documentation

Project docs are maintained in two languages:
- **Chinese**: [`docs-CN/`](docs-CN/index.md)
- **English**: [`docs-EN/`](docs-EN/index.md)

Both directories have identical structure. When updating docs, update both.

- [Documentation Index](docs-EN/index.md)
- [System Architecture](docs-EN/architecture.md)
- [Command Reference](docs-EN/commands.md)
- [Development Conventions](docs-EN/conventions.md)
- [Workflow Guide](docs-EN/workflow.md)
- [Known Issues](docs-EN/known_issues.md)
- [PGO Notes](docs-EN/knowledge/pgo.md)
- [GPS Planning Notes](docs-EN/knowledge/gps_planning.md)

## Development Workflow

1. Sync `main` and create a branch from it.
2. Implement and verify on the branch.
3. Rebuild with `--parallel-workers 1`.
4. `source install/setup.bash` after every build.
5. Push the branch and open a PR to `main`.
6. Merge through PR, then sync Jetson back to `main`.
7. Update affected docs in **both** `docs-CN/` and `docs-EN/` before the session is considered complete.

See [`docs-EN/workflow.md`](docs-EN/workflow.md) for the full executor workflow and documentation trigger rules.

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

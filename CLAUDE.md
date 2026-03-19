# CLAUDE.md

## Repository Purpose

This repository contains the ROS 2 Humble runtime stack for the FYP autonomous vehicle deployed on the Jetson Orin NX.

## Runtime Roots

- Workspace: `~/fyp_autonomous_vehicle`
- Runtime data: `~/fyp_runtime_data`
- Active docs: `~/fyp_autonomous_vehicle/docs`

## Operating Modes

- `make launch-slam`
- `make launch-explore`
- `make launch-explore-gps`
- `make launch-travel`

All `make launch-*` targets go through `scripts/launch_with_logs.sh`, which writes:

- console logs to `~/fyp_runtime_data/logs/<session>/console`
- custom node logs to `~/fyp_runtime_data/logs/<session>/data`
- system logs to `~/fyp_runtime_data/logs/<session>/system`

## Build Rules

```bash
cd ~/fyp_autonomous_vehicle
colcon build --packages-select <pkg> --symlink-install --parallel-workers 1
source install/setup.bash
```

## Critical Rules

1. Do not change tuned YAML parameters without documenting the reason.
2. Always source `install/setup.bash` after a build.
3. ROS 2 Humble only.
4. Do not modify `src/third_party/navigation2`.
5. Do not push directly to `main`; open a PR.

## GitHub CLI Note

PR operations require a valid `gh auth status` on the machine performing them. If Jetson `gh` auth is invalid, the PR can be created and merged from an authenticated workstation against the pushed branch, then Jetson should sync back to `main`.

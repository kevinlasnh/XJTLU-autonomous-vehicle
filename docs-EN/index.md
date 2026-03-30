# FYP Autonomous Navigation Vehicle Documentation Index

> Last updated: 2026-03-30

## Current System Summary

- Current primary operating mode: `make launch-explore`
- GPS fusion mode deployed: `make launch-explore-gps`
- GPS goal navigation mode software deployment completed on `feature/gps-navigation-v4`, passed indoor smoke test: `make launch-nav-gps`
- **GPS Corridor v2 standalone Global Aligner architecture deployed on `gps-rpp` branch**: `make launch-corridor`
  - Waypoint 1 reached reliably; runtime fine-tuning closed out
  - **FAST-LIO2 fatal Jacobian bug fixed** (commit `e4945f4`): `lidar_processor.cpp:245` `hat(t_wi)` -> `hat(t_il)`, eliminating root cause of rotation estimate divergence with distance
  - Odom divergence watchdog + ESKF degradation protection deployed and retained as general safety measures
  - Calibration handshake mechanism deployed, but wp1 calibration failed due to 30m GPS deviation
  - Current status: **Jacobian fix awaiting on-vehicle verification; GPS anchoring issue to be re-evaluated after Jacobian fix is verified**
- Current navigation and mapping stack: FAST-LIO2 + PGO + Nav2
- Runtime data root directory: `~/XJTLU-autonomous-vehicle/runtime-data`
- Unified parameter entry point: `src/bringup/config/master_params.yaml`
- Unified logging entry point: `scripts/launch_with_logs.sh`

## Core Documentation

| Topic | File |
|-------|------|
| System architecture and data flow | [architecture.md](architecture.md) |
| Common commands | [commands.md](commands.md) |
| Development conventions | [conventions.md](conventions.md) |
| Execution workflow | [workflow.md](workflow.md) |
| Known issues and current blockers | [known_issues.md](known_issues.md) |
| Hardware specifications | [hardware_spec.md](hardware_spec.md) |

## Technical Deep-Dive Documentation

| Topic | File |
|-------|------|
| FAST-LIO2 internals | [knowledge/fastlio2.md](knowledge/fastlio2.md) |
| PGO + GPS Factor | [knowledge/pgo.md](knowledge/pgo.md) |
| Nav2 tuning and runtime constraints | [knowledge/nav2_tuning.md](knowledge/nav2_tuning.md) |
| GPS global navigation and route planning | [knowledge/gps_planning.md](knowledge/gps_planning.md) |

## Development Log

| Period | File |
|--------|------|
| 2025-11 | [devlog/2025-11.md](devlog/2025-11.md) |
| 2025-12 | [devlog/2025-12.md](devlog/2025-12.md) |
| 2026-03 | [devlog/2026-03.md](devlog/2026-03.md) |

## Repository-Level Auxiliary Documentation

| File | Purpose |
|------|---------|
| [`../README.md`](../README.md) | Repository overview and quick start |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Contribution process and PR requirements |
| [`../CLAUDE.md`](../CLAUDE.md) | Agent-side execution constraints summary |

## Archive Notes

- `docs/devlog/legacy/` contains archived historical documents, kept for reference only and not maintained under the current structure.
- Upstream documentation under `src/third_party/` is outside the scope of this project's self-maintained documentation.

## Maintenance Principles

1. When code, launch files, parameters, system environment, or workflows change, update the corresponding documentation accordingly.
2. Monthly development records are appended to `devlog/YYYY-MM.md`.
3. New issues or status changes are synced to `known_issues.md`.
4. Command and workflow documentation must reflect the current executable state of the repository, not historical conventions.

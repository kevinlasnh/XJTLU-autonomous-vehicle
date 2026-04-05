# FYP Autonomous Navigation Vehicle Documentation Index

> Last updated: 2026-04-02

## Current System Summary

- Current primary operating mode: `make launch-explore`
- **Indoor click-to-go navigation without GPS**: `make launch-indoor-nav` (RViz goal publishing, no GNSS required)
- GPS fusion mode deployed: `make launch-explore-gps`
- GPS goal navigation mode software deployment completed on `feature/gps-navigation-v4`, passed indoor smoke test: `make launch-nav-gps`
- **GPS Corridor v2 switched to MPPI controller (`gps-mppi` branch)**: `make launch-corridor`
  - Controller switched from RotationShim + RPP to MPPI (commit `9d71823`), gaining native sampling-based obstacle avoidance
  - Costmap vehicle-height filtering tuned (commit `ce5226f`): only obstacles within vehicle body height range retained, false obstacles eliminated
  - Obstacle map coverage expanded to 15m (commit `2c2b8e6`), matching Livox MID360 range
  - Corridor speed cap raised to 1.5 m/s (commit `c0ea847`)
  - FAST-LIO2 publish cloud pre-height-filtering (commit `f619fa6`), C++ level filtering before downstream consumption
  - **GPS live alignment deployed** (commit `ebc26e2` + `fe3933e` + `e73c2bf`):
    - Calibration switched to translation-only, avoiding rotation flips
    - Startup directly absorbs stable GPS offset
    - Runner uses real-time alignment to recompute subgoals, removed per-waypoint frozen mechanism
  - **Indoor on-vehicle verification passed**: MPPI successfully navigated around a person, full corridor loop with no drift, memory stable at ~2.67GB, high-speed obstacle avoidance normal
  - **GPS outdoor regression test closed out** (2026-04-01): live alignment mechanism deployed, basic alignment issues fixed
  - **Dynamic obstacle avoidance recovery and replanning optimized** (2026-04-05): Global replanning raised to 5Hz, Navfn A* search enabled; BT recovery upgraded to 5-level progressive escalation (partial clear -> wait -> spin -> full clear -> backup 1m).
  - Current status: **Indoor navigation verified; GPS corridor basically functional; all future development on `gps-mppi` branch**
  - Known residual: serpentine corrections on clear straight path tracking, awaiting next round MPPI stability tuning
- Current navigation and mapping stack: FAST-LIO2 + PGO + Nav2 (MPPI)
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
| 2026-04 | [devlog/2026-04.md](devlog/2026-04.md) |

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

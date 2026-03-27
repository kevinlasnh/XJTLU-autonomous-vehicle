# Project Workflow Guide

> Current standard: Both code and documentation changes go through branches + PRs; `main` only receives verified results.

## 1. Role Division

| Role | Responsibility |
|------|----------------|
| kevinlasnh | Defines requirements, makes final decisions, executes on-vehicle tests |
| Claude | Architecture, research, solution design, result review |
| Codex | Implementation execution, build verification, commits, PRs, documentation sync |
| Team developers | Collaborate under the same branch and PR rules |

## 2. Standard Development Flow

### 2.1 Session Start

```bash
ssh jetson@100.97.227.24
cd ~/fyp_autonomous_vehicle
git status
git checkout main
git pull --ff-only
git branch -v
git log --oneline -5
```

If a previous build exists and you are continuing to debug:

```bash
source install/setup.bash
```

### 2.2 Create Branch

```bash
git checkout -b gps
```

Branch naming uses descriptive names directly, without prefixes:

- Examples: `gps`, `nav-tuning`, `lidar-fix`, `docs-sync`

### 2.3 Research and Implementation

1. First verify the actual code state, launch chain, and current parameters.
2. Then make changes -- do not write from historical memory alone.
3. If changes affect system behavior, first confirm which operating modes are impacted.
4. When adding new launch files / modes / parameter profiles, update documentation concurrently rather than leaving it for later.

### 2.4 Build

```bash
colcon build --packages-select <pkg> --symlink-install --parallel-workers 1
source install/setup.bash
```

Rules:

1. `--parallel-workers 1` is a hard requirement.
2. `source install/setup.bash` must be re-executed after every build.
3. Python packages can skip rebuilding under `--symlink-install`, but runtime verification is still required.
4. `build-navigation` currently includes `waypoint_collector`, `waypoint_nav_tool`, `gps_waypoint_dispatcher`.

### 2.5 Launch and Verify

Choose the appropriate mode based on the scope of changes:

```bash
make launch-slam
make launch-explore
make launch-explore-gps
make launch-nav-gps
make launch-travel
```

At minimum, verify the following:

- All relevant nodes are online
- Key topics / actions have data
- `map -> odom -> base_link` TF chain is complete
- Session logs are landing in `~/fyp_runtime_data/logs/latest/`

Changes related to on-vehicle behavior require a follow-up with manual on-site test conclusions.

### 2.6 GPS Navigation-Specific Verification

If changes involve `nav-gps`, at minimum add these checks:

1. Whether `build_scene_runtime.py` successfully generates `current_scene/` compiled artifacts
2. Whether `gps_anchor_localizer` enters `NAV_READY`
3. Whether `gps_waypoint_dispatcher` successfully reads `scene_points.yaml`
4. Whether `/compute_route` / `/follow_path` / `/navigate_to_pose` actions are online
5. Whether `goto_name` / `list_destinations` / `stop` behave correctly
6. Whether mock / replay `/fix` can be used for software smoke testing when there is no live fix indoors

## 3. AI Collaboration Flow

When tasks are jointly executed by Claude + Codex, the control plane is not in this repository but maintained in the PC command-center repository:

- `task_plan.md`
- `findings.md`
- `progress.md`

This Jetson repository is responsible for actual implementation, building, running, and archiving documentation.

## 4. Commits and PRs

### 4.1 Commits

```bash
git add path/to/file1 path/to/file2
git commit -m "Explain what changed and why"
git push -u origin feature/your-topic
```

Requirements:

1. Only add specific files.
2. Do not commit unrelated changes.
3. Commit messages must be in English.

### 4.2 PRs and Merges

```bash
gh auth status
gh pr create
gh pr merge --merge --delete-branch
git checkout main
git pull --ff-only
git fetch --prune
```

If `gh auth status` on the Jetson returns an invalid token, you can run `gh pr create` / `gh pr merge` on a local workstation already logged into GitHub CLI for the same branch, then have the Jetson pull `main` back.

## 5. Documentation Trigger Rules

When the following changes occur, modifying only code without updating documentation is not allowed:

| Change Type | Minimum Documentation to Sync |
|-------------|-------------------------------|
| Node source code | `devlog`, related `knowledge`, `architecture.md` when necessary |
| Launch files | `devlog`, `commands.md`, `workflow.md`, `architecture.md` when necessary |
| YAML parameters | `devlog`, corresponding knowledge document |
| Scripts and tools | `devlog`, `commands.md`, `workflow.md` when necessary |
| Bug fixes / new bugs | `devlog`, `known_issues.md` |
| System environment changes | `devlog`, `commands.md`, `workflow.md` |
| Workflow changes | `workflow.md`, `conventions.md` |

## 6. Session End Checklist

A session is not considered closed until all of the following are complete:

1. Changes have been verified.
2. Related documentation has been synced.
3. Branch has been pushed.
4. PR has been created and merged, or there is a clear record of why only a feature branch was left.
5. Jetson is back on the latest `main`, or there is a clear record of the current branch and reason for staying.
6. If there are new system facts, issues, or blockers, they have been written to the development log and issue tracker.


## 2.7 Fixed-Launch GPS Corridor Workflow

When the task objective narrows to "fixed launch position -> GPS route endpoint" corridor verification, prefer using:

1. Collect corridor multi-waypoint route:
   - `python3 scripts/collect_gps_route.py`
2. Return the vehicle to the fixed Launch Pose, align the heading
3. Launch directly:
   - `make launch-corridor`
   - or `bash scripts/launch_with_logs.sh corridor`
4. Observe:
   - `/gps_corridor/status`
5. `gps_global_aligner_node` + `gps_route_runner_node` automatically:
   - Standalone aligner estimates smoothed `ENU->map` transform
   - Checks whether current `/fix` is close to `start_ref`
   - Bootstrap startup (`yaw0 + launch_yaw_deg`)
   - GPS waypoints -> ENU -> map conversion
   - Freeze alignment within waypoint, split subgoals per segment
   - Sequential `NavigateToPose`

This workflow no longer requires:
- `nav_gps_menu.py`
- `goto_name`
- `route_server`
- `scene_gps_bundle.yaml`

# Development Conventions and Operating Procedures

## 1. General Development Rules

1. Understand the chain before modifying code or parameters.
2. Do not modify the primary operating chain without verifying the impact scope.
3. The third-party directory `src/third_party/` is not used for project-specific development.
4. Critical modifications must explain what, why, and risk.

## 2. Git and PR Rules

1. `main` is a protected stable branch; do not push directly.
2. All changes enter through feature branches, named directly with descriptive names without prefixes:
   - Examples: `gps`, `nav-tuning`, `lidar-fix`, `docs-sync`
3. Do not use `git add -A` or `git add .`.
4. Commit messages must be in English, stating what changed and why.
5. PRs must clearly describe:
   - What was changed
   - Why it was changed
   - How it was tested
   - Which layers are affected

## 3. Build Rules

1. `colcon build` on the Jetson must include `--parallel-workers 1`.
2. `source install/setup.bash` must be re-executed after every build.
3. Python packages under `--symlink-install` typically do not need rebuilding for source changes, but launch files, CMake, and install rule changes still require verification.
4. After modifying `CMakeLists.txt` or install rules, confirm that the target files actually exist in `install/`.

## 4. Parameter and YAML Rules

1. Modifying already-tuned YAML parameters without a documented reason is not allowed.
2. Parameter changes must be simultaneously recorded in the relevant documentation.
3. The current unified parameter entry point is `src/bringup/config/master_params.yaml`.
4. Nav2 primary configuration files are:
   - `nav2_default.yaml`
   - `nav2_explore.yaml`
   - `nav2_travel.yaml`

## 5. Runtime Data and Logging Rules

Runtime data is separated from the code repository in `~/fyp_runtime_data/`:

```text
~/fyp_runtime_data/
├── config/
├── gnss/
├── logs/
│   ├── <timestamp>/
│   │   ├── console/
│   │   ├── data/
│   │   └── system/
│   └── latest -> <timestamp>
├── maps/
├── perf/
└── planning/
```

Additional rules:

1. `make launch-*` automatically creates session log directories.
2. `console/` stores ROS 2 console logs.
3. `data/` stores per-node custom logs, driven by `FYP_LOG_SESSION_DIR`.
4. `system/` stores `tegrastats.log` and `session_info.yaml`.
5. When using `ros2 launch` directly, some legacy log fallback paths may still exist, such as `logs/twist_log/`.

## 6. GNSS Current Constraints

1. The current GNSS stack operates at basic GPS accuracy level, not maintained as an RTK workflow.
2. Indoors without satellite reception, `/fix` showing `status=-1` or `NaN` is expected behavior.
3. `gnss_calibration` does not write a valid `gnss_offset.txt` under no-fix conditions.
4. On the current Jetson runtime, `~/fyp_runtime_data/gnss/` may contain `gnss_offset.invalid_*.txt` as invalid sample traces.

## 7. On-Vehicle Safety Rules

1. The PS2 gamepad must always be kept available.
2. During autonomous driving, someone must always be ready to press the `X` button to disable motors.
3. The red emergency stop button on the vehicle body always takes priority over software commands.
4. The `B` button is prohibited as an emergency braking method because it causes severe wheel reversal.

## 8. System Environment Rules

1. The current Jetson wired connection `Wired connection 1` is set to auto-connect with priority `100`; do not disable it casually.
2. Check `gh auth status` on the machine performing PR operations.
3. If the Jetson's `gh` login session expires, PRs and merges can be completed on a local workstation already logged into GitHub CLI, then have the Jetson pull `main` back.

## 9. Documentation Maintenance Rules

1. When modifying code, launch files, parameters, scripts, system configuration, or workflows, update the documentation accordingly.
2. Monthly factual records are written to `docs/devlog/YYYY-MM.md`.
3. New issues, status changes, and fixed issues are synced to `docs/known_issues.md`.
4. Documentation descriptions must reflect the current actual executable state and must not retain outdated commands as "standard procedures."

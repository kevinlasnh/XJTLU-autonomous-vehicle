# 开发规范与操作规程

## 1. 通用开发规则

1. 先理解链路，再改代码或参数。
2. 不要在未验证影响面的情况下改动主运行链。
3. 第三方目录 `src/third_party/` 不作为项目自定义开发区。
4. 关键修改必须能说明 what、why、risk。

## 2. Git 与 PR 规则

1. `main` 是受保护稳定分支，不直接推送。
2. 所有改动从功能分支进入，分支命名直接用描述名，不加前缀：
   - 示例: `gps`、`nav-tuning`、`lidar-fix`、`docs-sync`
3. 不使用 `git add -A` 或 `git add .`。
4. Commit message 使用英文，写明改了什么和为什么。
5. PR 必须写清楚：
   - 改了什么
   - 为什么改
   - 怎么测的
   - 影响哪些层

## 3. 构建规则

1. Jetson 上 `colcon build` 必须带 `--parallel-workers 1`。
2. 每次构建完成后必须重新执行 `source install/setup.bash`。
3. Python 包在 `--symlink-install` 下改源码通常无需重编，但 launch、CMake、安装规则改动后仍要验证。
4. 修改 `CMakeLists.txt` 或安装规则后，要确认 `install/` 中目标文件实际存在。

## 4. 参数与 YAML 规则

1. 不允许无原因改动已调好的 YAML 参数。
2. 参数变更必须同时记录到相关文档。
3. 当前统一参数入口是 `src/bringup/config/master_params.yaml`。
4. Nav2 主配置文件是：
   - `nav2_default.yaml`
   - `nav2_explore.yaml`
   - `nav2_travel.yaml`

## 5. 运行时数据与日志规则

运行时数据与代码仓分离在 `~/fyp_runtime_data/`：

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

补充规则：

1. `make launch-*` 会自动创建 session 日志目录。
2. `console/` 存 ROS 2 控制台日志。
3. `data/` 存节点自定义日志，由 `FYP_LOG_SESSION_DIR` 驱动。
4. `system/` 存 `tegrastats.log` 和 `session_info.yaml`。
5. 直接 `ros2 launch` 时，部分旧日志 fallback 路径仍会存在，例如 `logs/twist_log/`。

## 6. GNSS 当前约束

1. 当前 GNSS 栈按基础 GPS 精度使用，不按 RTK 工作流维护。
2. 室内无卫星条件下，`/fix` 为 `status=-1` 或 `NaN` 是预期现象。
3. `gnss_calibration` 在 no-fix 情况下不会写有效 `gnss_offset.txt`。
4. 当前 Jetson 运行时 `~/fyp_runtime_data/gnss/` 中可出现 `gnss_offset.invalid_*.txt` 作为无效样本留痕。

## 7. 实车安全规则

1. PS2 手柄始终保持可用。
2. 自动驾驶时必须有人随时准备按 `X` 键失能电机。
3. 车身红色急停按钮始终优先于软件命令。
4. `B` 键禁用为紧急刹车手段，因为会导致车轮严重反转。

## 8. 系统环境规则

1. 当前 Jetson 有线连接 `Wired connection 1` 处于自动连接状态，优先级为 `100`，不要随意关闭。
2. 在执行 PR 操作的机器上先检查 `gh auth status`。
3. 如果 Jetson 的 `gh` 登录态失效，可以在已登录 GitHub CLI 的本地工作站上完成 PR/merge，再让 Jetson 回拉 `main`。

## 9. 文档维护规则

1. 改代码、launch、参数、脚本、系统配置或工作流时，同步更新文档。
2. 月度事实记录写入 `docs/devlog/YYYY-MM.md`。
3. 新问题、状态变化和已修复问题同步到 `docs/known_issues.md`。
4. 文档描述必须反映当前真实可执行状态，不能保留过时命令当“标准流程”。

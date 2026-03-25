# FYP Autonomous Vehicle - Progress Log

**最后更新**: 2026-03-25

---

## 当前状态

**Corridor 最新 best-so-far 版本已部署到 GitHub + Jetson，最新实车日志已分析并写入 L2；等待 CC 文档阶段。**

| 项目 | 状态 |
|------|------|
| Corridor 最新实车收口（2026-03-25 晚） | **Step 29-31 已完成，L2 已更新** |
| Corridor 最新车端提交 | **`abf05a4` 已部署到 Jetson** |
| 系统优化批次（subgoal/legacy/cleanup/QoS） | **已部署到 GitHub + Jetson；等待现场验证** |
| collect_gps_route.py 改进 | **已部署到 GitHub + Jetson；等待现场交互验证** |
| Corridor v2 独立 aligner 架构 | **已部署** |
| 运行期微调 v2（修正） | **已部署到 Jetson；等待 GPS fix** |
| 当前分支 | `gps` |

---

## 最近完成 (2026-03-25)

### Codex Corridor 实车收口（Step 29-31，2026-03-25 晚）

- [x] 继续部署并推送 3 个 corridor 运行期微调提交：
  - `f98fa81` `Fix corridor subgoal numbering and disable spin recovery`
  - `3f21d16` `Increase corridor costmap inflation for safer obstacle clearance`
  - `abf05a4` `Relax corridor point cloud height filters`
- [x] Jetson 完成：
  - `git pull --ff-only origin gps`
  - `colcon build --packages-select bringup --symlink-install --parallel-workers 1`
  - `source install/setup.bash`
- [x] Jetson 启动级 smoke test 通过：
  - `timeout -s INT 8s bash scripts/launch_with_logs.sh corridor`
  - 启动后退出正常
  - `ros2 daemon` 无残留
  - `/dev/serial_twistctl` 与 `/dev/wheeltec_gps` 无占用
- [x] 用户完成最新一轮实车测试，最佳 session：
  - `/home/jetson/fyp_runtime_data/logs/2026-03-25-17-46-15/`
- [x] 已在该 session 根目录写入显式标记文件：
  - `BEST_SO_FAR_NOTE.txt`
- [x] 最新日志分析结论已收敛：
  - waypoint 1 已稳定到达
  - 第二段能完成直角转弯并推进较长距离
  - 第二段中途切到最终子目标 `(47.48, -52.41)` 是**正常分段推进**，不是随机 GPS goal 跳变
  - 真正的后段失稳发生在大量 `collision ahead` / recovery 之后，随后 `lio_odom` 明显发散
- [x] 最新异常点已明确记录给下一轮：
  - route runner 最终子目标编号日志仍显示 `1/2`
  - runtime 里 `behavior_server` 仍执行 `spin`，与 corridor BT 文件内容不一致
  - 障碍物表达主链确认是 `/fastlio2/body_cloud -> STVL -> Denoise -> Inflation`
- [x] 按用户要求，不再继续新增代码修改，转入 L2 收口

### 当前收口断点（交给 CC）

- [x] Step 29：最新 session 全量日志分析完成
- [x] Step 30：问题性质已判断，当前不再继续现场迭代
- [x] Step 31：L2 文件已更新，可直接交给 CC 写文档
- [ ] 下一位执行者（CC）如果要继续：
  - 先以 `2026-03-25-17-46-15` 作为当前最佳基线
  - 文档里把主问题表述为“绿色路径贴边 + recovery/odom 后段失稳”，而不是“GPS 目标随机跳变”

### Codex 系统优化部署（Step 17-25）

- [x] 读取 `task_plan.md` / `progress.md` / `docs/index.md` / `docs/workflow.md`
- [x] 确认真实活跃任务已切换为“系统优化批次（4 项）”
- [x] 审查部署性：
  - legacy PGO handoff 参数只剩 runner 声明 + `master_params.yaml` 残留
  - `segment_length_m` fallback 只需修改 `collect_gps_route.py` 与 `gps_route_runner_node.py`
  - 未发现需要回退给 CC 的新 blocker
- [x] 本地修改：
  - `scripts/collect_gps_route.py`: `SEGMENT_LENGTH_M 8.0 -> 30.0`
  - `gps_route_runner_node.py`: 删除 7 个 legacy 参数声明，3 处 fallback `8.0 -> 30.0`
  - `master_params.yaml`: 删除 `/gps_route_runner` 下 7 个 legacy 参数
  - `scripts/launch_with_logs.sh`: cleanup 补 `pointcloud_to_laserscan`、`monitor_corridor_status`、`ros2 daemon stop`、串口释放
  - `Makefile`: `kill-runtime` 同步补 pkill 列表与串口释放
  - `fastlio2/src/lio_node.cpp`: `body_cloud/world_cloud` publisher depth `10000 -> 500`
- [x] 本地静态验证通过：
  - `python -m py_compile scripts/collect_gps_route.py src/navigation/gps_waypoint_dispatcher/gps_waypoint_dispatcher/gps_route_runner_node.py`
  - `yaml.safe_load(src/bringup/config/master_params.yaml)`
  - `bash -n scripts/launch_with_logs.sh`
- [x] 提交并推送：
  - commit `9a1420d` `Trim corridor overhead and harden runtime cleanup`
- [x] Jetson `git pull --ff-only origin gps`
  - 成功快进：`75541a3 -> 9a1420d`
  - 无关脏文件 `src/perception/pgo_gps_fusion/rviz/pgo.rviz` 未阻塞 pull
- [x] Jetson build + source：
  - `colcon build --packages-select gps_waypoint_dispatcher bringup fastlio2 --symlink-install --parallel-workers 1`
  - `source install/setup.bash`
  - `ros2 pkg prefix gps_waypoint_dispatcher bringup fastlio2` 正常
- [x] Jetson 启动级 smoke test：
  - `timeout -s INT 8s bash scripts/launch_with_logs.sh corridor`
  - 系统启动链正常拉起
  - cleanup 后 `ros2 daemon` 已停止
  - cleanup 后 `/dev/serial_twistctl`、`/dev/wheeltec_gps` 无占用
  - cleanup 后无关键残留进程
- [ ] 待用户现场验证：
  - 30m subgoal 是否减少频繁小段切换
  - FAST-LIO2 内存占用是否明显收敛
  - `gps_global_aligner_node` 的 `SIGINT` traceback 是否需要单独修

### CC 系统优化调研（Step 8-16）

- [x] SSH 确认 Jetson 仓库状态
- [x] 读取 `gps_route_runner_node.py` 全文（707 行）— subgoal 分段逻辑
- [x] 读取 `gps_global_aligner_node.py` 全文（605 行）
- [x] 读取 `nav2_explore.yaml` — global costmap 70×70m → 半径 35m
- [x] 确认 subgoal 间距公式：35m - 5m buffer = 30m（合理）
- [x] 识别 legacy PGO 参数：runner 87-94 行 + master_params 177-190 行
- [x] 派子代理调研启动链和清理机制
  - 发现：cleanup 缺 `ros2 daemon stop`、缺 `pointcloud_to_laserscan` 和 `monitor` 在 pkill 列表、缺串口释放验证
- [x] 派子代理调研内存占用
  - 发现：FAST-LIO2 QoS 队列深度 10000（lio_node.cpp:151-152），严重过大
- [x] 用户确认本轮 4 项改动：subgoal 30m / legacy 清理 / Ctrl+C 完整清理 / QoS 500
- [x] 输出计划到 task_plan.md
- [x] planning-with-files 记录

### CC 文档阶段 — 系统优化批次（Step 33-38）

- [x] `git diff --stat cfc4b94..HEAD` — 9 个文件变更
- [x] 更新文档：
  - `docs/devlog/2026-03.md`: 新增系统优化批次条目
  - `docs/commands.md`: Section 14 补 subgoal 间距说明 + Ctrl+C 自动清理说明
  - `docs/knowledge/gps_planning.md`: 更新 segment_length_m 默认值说明
- [x] planning-with-files 记录
- [x] git commit + push
  - commit `c870814` `Sync docs for system optimization batch deployment`

### CC 文档阶段 — 采集脚本改进（Step 33-38）

- [x] 读 L2 文件 + `git diff --stat a7dc2fd..HEAD`
- [x] 读 `docs/index.md`
- [x] 判断文档类型：无需新增，更新 3 个现有文件
- [x] 更新文档：
  - `docs/commands.md`: Section 14 重写 — GPS 采集命令突出显示 + 交互流程说明
  - `docs/devlog/2026-03.md`: 新增 03-25 条目（采集脚本改进）
  - `docs/index.md`: 日期更新到 2026-03-25
- [x] planning-with-files 记录
- [x] git commit + push
  - commit `cfc4b94` `Sync docs for GPS route collector improvements`

### Codex 采集脚本部署（Step 17-25）

- [x] 读取 `task_plan.md` / `progress.md` / `findings.md` / `WORKFLOW.md`
- [x] session catchup：确认真实断点是 `collect_gps_route.py` 的 Codex Step 17-25
- [x] 审查计划可部署：未发现需要回退给 CC 的新 blocker
- [x] 修改 `scripts/collect_gps_route.py`
  - 默认 waypoint 命名改为 `wp1/wp2/...`
  - 单点采样后新增 `Accept / Retry`
  - 新增高度异常告警
  - 新增 ENU 预览（导入失败时自动降级）
  - 新增保存前路线摘要 + 最后一个 waypoint 可重命名为 `goal`
- [x] 本地验证通过
  - `python -m py_compile scripts/collect_gps_route.py`
  - 脱 ROS stub import smoke test
- [x] 提交并推送
  - commit `41f88d9` `Improve GPS route collection review and preview for safer capture`
- [x] Jetson `git pull --ff-only origin gps`
  - 成功快进：`a7dc2fd -> 41f88d9`
  - 远端无关脏文件 `src/perception/pgo_gps_fusion/rviz/pgo.rviz` 未阻塞 pull
- [x] Jetson 静态 smoke test
  - `python3 -m py_compile scripts/collect_gps_route.py` 通过
  - 本轮为独立脚本改动，不需要 `colcon build`
- [ ] 待用户现场验证
  - 在 Jetson 运行 `python3 scripts/collect_gps_route.py`
  - 确认新的交互流程与路线摘要符合预期

### CC 采集脚本改进计划（Step 8-16）

- [x] SSH 到 Jetson 确认现有路线文件：`~/fyp_runtime_data/gnss/current_route.yaml`
  - 路线 `v1`，采集于 2026-03-22
  - 2 个 waypoint：`right-top-corner` → `right-bottom-corner`
  - start_ref spread 0.14m，GPS 坐标质量好
- [x] 读取 `collect_gps_route.py` 全文（374 行）
- [x] 读取 runner `_load_route()` 校验逻辑（验证 enu_origin 匹配 + 必填字段）
- [x] 读取 `scene_runtime.py`：确认 `FixedENUProjector` 可复用
- [x] 识别 5 个改进点：
  1. waypoint 默认命名逻辑反了
  2. 无单点重采选项
  3. 高度异常无告警
  4. 无 ENU 坐标预览
  5. 无保存前路线摘要
- [x] 输出完整改进计划
- [x] 用户确认（Step 15）
- [x] planning-with-files 记录（Step 16）

---

## 最近完成 (2026-03-24)

## 最近完成 (2026-03-24)

### CC 文档阶段（Step 33-38）

- [x] 读 L2 文件（progress.md + task_plan.md + findings.md）
- [x] git diff 看 docs 增量
- [x] 读 docs/index.md 了解当前文档结构
- [x] 判断文档类型：无需新增，按触发矩阵更新 9 个现有文件
- [x] 更新所有相关文档：
  - `devlog/2026-03.md`: +46 行，03-23 运行期微调全过程 + 03-24 Jetson 恢复部署
  - `architecture.md`: Section 5.3 重写为独立 global aligner 数据流图
  - `gps_planning.md`: Section 12 重写，PGO handoff → 独立 aligner + 修正 v2 参数表
  - `pgo.md`: Section 10 重写，标记 PGO 侧对齐已淘汰，记录架构演变
  - `nav2_tuning.md`: collision time 1.0→0.6 + 修正 v2 上下文
  - `known_issues.md`: #20 更新独立 aligner 状态，#21 标记已解决，#22 更新降频缓解
  - `workflow.md`: Section 2.2 + 2.7 对齐分支命名 + v2 采集/启动命令
  - `conventions.md`: 分支命名改为描述名
  - `index.md`: 日期 → 2026-03-24，系统摘要补充独立 aligner
- [x] 调用 planning-with-files 记录进度
- [ ] git commit + push

### Codex 恢复部署（修正 v2，继续 Step 23-25）

- [x] 重新读取 L2 文件，确认上次真实断点在 `Step 23`
- [x] 复核锁定执行口径：
  - 本地最新提交为 `a7dc2fd` `Revert unsafe corridor tuning and tighten waypoint guard`
  - 目标参数仍是：
    - `max_allowed_time_to_collision_up_to_carrot: 0.6`
    - local `denoise_layer.minimal_group_size: 4`
    - `/gps_route_runner.waypoint_start_progress_guard_m: 5.0`
    - global STVL `transform_tolerance: 0.5`
- [x] Jetson 网络恢复：
  - `Test-NetConnection 100.97.227.24 -Port 22` 成功
  - `ssh jetson@100.97.227.24` 可登录
- [x] Jetson 仓库状态确认：
  - 分支 `gps`
  - 旧 HEAD 为 `1898655`
  - 工作树仅有无关脏文件：`src/perception/pgo_gps_fusion/rviz/pgo.rviz`
- [x] Jetson `git pull --ff-only origin gps`
  - 成功快进：`1898655 -> a7dc2fd`
  - 目标提交不触碰 `pgo.rviz`，因此 pull 未与远端脏文件冲突
- [x] Jetson `colcon build --packages-select gps_waypoint_dispatcher bringup --symlink-install --parallel-workers 1`
- [x] Jetson `source install/setup.bash`
  - `ros2 pkg prefix bringup` 正常
  - `ros2 pkg prefix gps_waypoint_dispatcher` 正常
- [x] 进行零运动 corridor smoke test：
  - session: `/home/jetson/fyp_runtime_data/logs/2026-03-24-12-34-31/`
  - 方式：临时生成 `deploy_smoke_route.yaml`，把唯一 waypoint 设为 `start_ref`，用于验证 corridor 全链路但不发实际导航目标
- [x] 自定义 smoke harness 首轮失败已定位：
  - `source /opt/ros/humble/setup.bash` 在 `set -u` 下报 `AMENT_TRACE_SETUP_FILES: unbound variable`
  - 按仓库现有 `launch_with_logs.sh` 口径改为 `source` 前 `set +u`，随后重跑成功进入启动监控
- [x] smoke test 启动链验证通过：
  - `lifecycle_manager_navigation`: `Managed nodes are active`
  - `controller_server`: `Controller frequency set to 15.0000Hz`
  - `gps_global_aligner`: `ALIGNER_WAITING_FOR_STABLE_FIX`
  - `gps_route_runner`: `WAITING_FOR_STABLE_FIX`
- [x] 当前阻塞再次确认仍是 GPS `NO_FIX`：
  - `GNGGA ... fix=0`
  - `GNRMC ... V`
  - `GPGSV/BDGSV ... 00`
  - `GPTXT ... ANTENNA OK`
- [x] 当前结论：
  - Step 23 已完成
  - Step 24 已完成
  - Step 25 已完成零运动启动级 smoke test
  - 真实 corridor 启动仍等待现场恢复 stable GPS fix；之后才能继续用户 Step 26 实车测试

---

## 最近完成 (2026-03-23)

### 运行期微调方案调研（Step 8-16）

- [x] 重新读取 L2 文件，确认当前真实问题
- [x] 派 3 个子代理并行调研：
  - Collision ahead 误触发解决方案
  - Waypoint 边界 alignment 漂移解决方案
  - TF extrapolation 和 costmap 优化方案
- [x] 自审调研结论，验证数据来源
- [x] 整合完整部署方案
- [x] 输出到 task_plan.md

### 调研结论

**问题 1：Collision ahead 误触发（236 次）**
- 根因：`max_allowed_time_to_collision: 0.6s` 过短，STVL 衰减慢
- 方案：延长到 1.2s，加速衰减到 0.8s

**问题 2：Waypoint 边界 alignment 漂移（16.51m）**
- 根因：Global aligner 持续修正，waypoint 边界切换时坐标反投影偏移
- 方案：提高保护阈值到 10.0m，修改保护逻辑

**问题 3：TF extrapolation（51 次）+ Controller 掉频**
- 根因：`transform_tolerance: 0.35s` 偏严，20Hz 超算力边界
- 方案：放宽到 0.5s，降频到 15Hz

### 部署方案摘要

**Phase 1：Nav2 参数调优**
1. `max_allowed_time_to_collision: 1.2`
2. `voxel_decay: 0.8`
3. `transform_tolerance: 0.5` (controller/costmap)
4. `transform_tolerance: 0.8` (planner)
5. `controller_frequency: 15.0`

**Phase 2：Runner waypoint 边界保护**
1. `waypoint_start_progress_guard_m: 10.0`
2. `waypoint_start_cross_track_guard_m: 5.0`
3. 修改保护逻辑：优先使用更接近 0 的 alignment

**构建**: `colcon build --packages-select gps_waypoint_dispatcher bringup`

### Codex 部署性审查（运行期微调方案，Step 17-19）

- [x] 读取 `task_plan.md`、`findings.md`、`progress.md`
- [x] 核对当前 `nav2_explore.yaml` 实际参数值
- [x] 核对 `gps_route_runner_node.py` 保护逻辑与参数读取路径
- [x] 核对 `system_gps_corridor.launch.py` 的参数注入链
- [x] 发现部署缺口：Phase 2 若只改 Python 默认值，运行时会被 `master_params.yaml` 中 `/gps_route_runner` 的旧值覆盖
- [x] 在不改变架构前提下微调计划：
  - Phase 2 同步修改 `src/bringup/config/master_params.yaml`
  - 保留修改 `gps_route_runner_node.py` 默认值作为一致性清理
- [x] 复核 planner 项：`planner_server.transform_tolerance` 当前实际是 `0.5`，计划中的 `0.8` 方向成立
- [x] 结论：**运行期微调方案经微调后可部署，Step 19 通过**

### Codex 部署与系统测试（运行期微调方案，Step 21-25）

- [x] 修改 `nav2_explore.yaml`
  - `controller_server.transform_tolerance: 0.35 -> 0.5`
  - `controller_frequency: 20.0 -> 15.0`
  - `FollowPath.transform_tolerance: 0.35 -> 0.5`
  - `max_allowed_time_to_collision_up_to_carrot: 0.6 -> 1.2`
  - `local stvl_layer.voxel_decay: 1.2 -> 0.8`
  - `local stvl_layer.transform_tolerance: 0.35 -> 0.5`
  - `planner_server.transform_tolerance: 0.5 -> 0.8`
- [x] 修改 `master_params.yaml`
  - `/gps_route_runner.waypoint_start_progress_guard_m: 4.0 -> 10.0`
  - `/gps_route_runner.waypoint_start_cross_track_guard_m: 3.0 -> 5.0`
- [x] 修改 `gps_route_runner_node.py`
  - 默认 guard 值同步到 `10.0 / 5.0`
  - `previous_is_better` 逻辑改为优先保留更接近段起点的 alignment
- [x] 本地静态检查通过
  - `py_compile` 通过
  - `nav2_explore.yaml` / `master_params.yaml` YAML 解析通过
- [x] 提交并推送
  - commit `1898655` `Tune corridor runtime thresholds to reduce stop-go and waypoint drift`
- [x] Jetson `git pull --ff-only origin gps`
- [x] Jetson `colcon build --packages-select gps_waypoint_dispatcher bringup --symlink-install --parallel-workers 1`
- [x] Jetson 启动 smoke test：`scripts/launch_with_logs.sh corridor`
- [x] 结论：
  - Nav2 生命周期成功激活，controller/planner/bt_navigator 正常起
  - 新参数已被实际读入，日志中明确显示 `Controller frequency set to 15.0000Hz`
  - corridor 未进入 `RUNNING_ROUTE` 的原因是 GPS 一直无 fix，不是本轮参数改动导致的启动错误

### 当前阻塞（2026-03-23 部署后）

- 最新 smoke test session: `/home/jetson/fyp_runtime_data/logs/2026-03-23-11-22-31/`
- `gps_global_aligner` 与 `gps_route_runner` 都停在 `WAITING_FOR_STABLE_FIX`
- `nmea_navsat_driver` 持续输出：
  - `GNGGA ... fix=0`
  - `GNRMC ... V`
  - `GPGSV/BDGSV ... 00`
- 说明当前环境下 GPS 天线在线，但没有卫星 fix
- 下一步需要在有 GPS 条件的现场继续 Step 25/26

### CC 复审：运行期微调 v1 → 修正 v2（2026-03-23 下午）

- [x] 读取 Codex 实际部署的代码 diff
- [x] 派 3 个子代理并行验证方案对症性：
  - 子代理 1：验证 `max_allowed_time_to_collision` 参数语义
  - 子代理 2：代码级验证 waypoint 保护逻辑
  - 子代理 3：验证降频和 TF tolerance 综合效果
- [x] **关键发现 1**：`max_allowed_time_to_collision: 0.6 → 1.2` 方向反了
  - 增大 = 检测窗口更远 = 更灵敏 = 更多停车
  - 来源：Nav2 RPP 源码 `collision_checker.cpp` 的 while 循环逻辑
- [x] **关键发现 2**：collision ahead 236 次的主因是 `min_obstacle_height: 0.05`
  - 地面不平/点云噪声被标记为障碍
  - 碰���检测参数只是放大器，不是根因
- [x] **关键发现 3**：`waypoint_start_progress_guard_m: 10.0` 太宽松
  - GPS 2.5m 精度 2-sigma = 5m，正常 progress 不超过 4m
  - 10.0 只拦极端跳变，4-10m 中等偏移放过
- [x] 派 2 个子代理深挖修正方案：
  - 子代理 4：collision ahead 根因 + 正确修��参数
  - 子代理 5：waypoint 保护阈值合理性分析
- [x] 整合修正方案 v2，写入 task_plan.md
- [x] v2 修正内容：
  - `min_obstacle_height`: 0.05 → 0.15（Local + Global）
  - `pointcloud_clear.min_z`: 0.05 → 0.10（Local + Global）
  - `max_allowed_time_to_collision`: 1.2 → 0.8
  - `denoise_layer.minimal_group_size`: 3 → 4
  - `waypoint_start_progress_guard_m`: 10.0 → 5.0
  - Global STVL `transform_tolerance`: 0.35 → 0.5

### Codex 部署性审查（修正 v2，Step 17-19）

- [x] 重新读取 `task_plan.md`、`findings.md`、`progress.md`
- [x] 核对 v1 已部署代码基线：
  - `src/bringup/config/nav2_explore.yaml`
  - `src/bringup/config/master_params.yaml`
  - `src/navigation/gps_waypoint_dispatcher/gps_waypoint_dispatcher/gps_route_runner_node.py`
- [x] 发现部署阻塞 1：`task_plan.md` 同时保留修正 v2 与旧 v1 指令，执行口径冲突
- [x] 发现部署阻塞 2：`min_obstacle_height: 0.15` 与仓库现有 `body_cloud` 高度参考冲突，若直接用于 Local + Global 可能过滤约 `50cm` 低墙
- [x] 复核其余 v2 改动的参数注入链：字段和覆盖路径都真实存在
- [x] 结论：**修正 v2 当前不可直接部署，Step 19 未通过；等待 CC 收敛最终方案后再复审**

### Codex 收敛修正（修正 v2，Step 19 闭环）

- [x] 用户授权由 Codex 直接收敛方案，不再等待 CC 二次整理
- [x] 重读：
  - `task_plan.md`
  - `findings.md`
  - `progress.md`
  - `corridor_v2_runtime_issues_analysis.md`
  - `docs/hardware_spec.md`
- [x] 重新比对现有高度参考与 STVL 参数语义
- [x] 收敛修正 1：将 `min_obstacle_height/min_z` 从锁定批次中移除
  - 原因：`0.15` 与仓库现有 `body_cloud` 高度参考冲突，可能过滤约 `50cm` 低墙
  - 原因：当前没有足够项目证据支撑把 `pointcloud_clear.min_z` 从 `0.05` 提到 `0.10/0.15`
- [x] 收敛修正 2：将 `max_allowed_time_to_collision_up_to_carrot` 锁定为 `1.2 -> 0.6`
  - 原因：`1.2` 方向错误
  - 原因：`0.8` 仍比最近一次实际 route 基线 `0.6` 更敏感；在高度门限不动的前提下不宜上调
- [x] 保留可直接部署的低风险项：
  - local `denoise_layer.minimal_group_size: 3 -> 4`
  - `/gps_route_runner.waypoint_start_progress_guard_m: 10.0 -> 5.0`
  - global STVL `transform_tolerance: 0.35 -> 0.5`
- [x] 重写 `task_plan.md` 顶部为单一“Codex 收敛锁定版”执行口径，并把旧方案改为历史存档
- [x] 结论：**修正 v2 经 Codex 收敛后可部署，Step 19 通过；等待用户 Step 20 锁定**

### Codex 部署执行（修正 v2，Step 21-25）

- [x] 本地修改：
  - `src/bringup/config/nav2_explore.yaml`
  - `src/bringup/config/master_params.yaml`
  - `src/navigation/gps_waypoint_dispatcher/gps_waypoint_dispatcher/gps_route_runner_node.py`
- [x] 本地静态检查通过：
  - `py_compile` 通过
  - `nav2_explore.yaml` / `master_params.yaml` YAML 解析通过
- [x] 提交并推送：
  - commit `a7dc2fd` `Revert unsafe corridor tuning and tighten waypoint guard`
- [x] Jetson `git pull --ff-only origin gps`
- [x] Jetson `colcon build --packages-select gps_waypoint_dispatcher bringup --symlink-install --parallel-workers 1`
- [x] Jetson `source install/setup.bash`
- [x] corridor 启动级 smoke test（零运动临时 route）
- [x] 阻塞定位：
  - `ssh jetson@100.97.227.24` 现已恢复
  - 当前 smoke test 仍卡在 `WAITING_FOR_STABLE_FIX`
  - `nmea_navsat_driver` 继续输出 `fix=0 / satellites=0 / ANTENNA OK`
- [x] 当前结论：**修正 v2 已完成 Jetson 部署；当前剩余阻塞不再是部署链，而是现场 GPS 仍无 fix**

---

## 最近完成 (2026-03-22)

### CC 微调优化计划（Step 8-16）

- [x] 读取当前分支代码，理解系统现状
- [x] 加载 Superpowers skill
- [x] 审核用户需求：3 个微调问题（PGO 接管门槛、costmap 残留、频率掉频）
- [x] 派第一轮子代理调研（误分析了未启用节点）
- [x] 用户纠正：检查实际启用节点
- [x] 派第二轮子代理调研（分析实际运行节点）
- [x] 自审计划：发现 costmap raytrace 方案有高风险
- [x] 派多个子代理联网验证：
  - FAST-LIO2 参数优化（可行性：中等）
  - Costmap raytrace 优化（可行性：中低，建议用 STVL）
  - Controller 频率优化（可行性：高）
  - Jetson 20Hz 方案验证（可行性：低，推荐最高 5Hz）
- [x] 与用户讨论 Global Costmap 刷新率重要性
- [x] 用户确认方案 B（激进频率提升：Local 12Hz, Global 5Hz）
- [x] 输出完整优化计划（Step 14）
- [x] 用户确认计划（Step 15）
- [x] planning-with-files 记录进度（Step 16）

### Codex 部署性审查（方案 B）

- [x] 读取 CC 新方案及 L2 增量
- [x] 核对当前代码状态：PGO 门槛、Nav2 频率、BT 插件链
- [x] 核对 Jetson 运行环境：STVL 包当前未安装，但 apt 可用
- [x] 核对 Nav2 Humble 默认 BT：planner replan 仍是 `1Hz`
- [x] 发现部署缺口 1：`global_costmap 5Hz` 不能直接实现"绿色 /plan 更快"
- [x] 发现部署缺口 2：STVL 配置块不完整，且缺失安装前置步骤
- [x] 在不改变架构前提下补充部署约束：
  - `global_costmap 5Hz` 改为 staged rollout
  - STVL 补 apt install + 完整 MID360 参数块
- [x] 结论：**方案 B 经微调后可部署，Step 19 通过**

### CC 文档阶段（Step 33-38）

- [x] 读 L2 文件（git diff 看 Codex 更新）
- [x] 读 docs/index.md
- [x] 判断文档类型：无需新增，更新现有文档
- [x] 更新所有相关文档：
  - `devlog/2026-03.md`: 新增 corridor v2 部署与实车测试条目
  - `known_issues.md`: 更新 GPS RF 状态、costmap 残留新发现、新增 PGO handoff 和 controller/planner 掉频问题、更新 corridor v1→v2 状态
  - `knowledge/nav2_tuning.md`: 新增 corridor RPP 控制器参数、更新 costmap 参数与实车发现
  - `knowledge/gps_planning.md`: 更新当前状态、新增 corridor v2 架构与实车验证章节
  - `knowledge/pgo.md`: 更新 GPS topic `/gnss`→`/fix`、新增 corridor v2 ENU→map 对齐机制章节
  - `commands.md`: 新增 corridor quiet 模式说明
  - `index.md`: 更新日期与当前系统摘要
- [x] 调用 planning-with-files 记录进度
- [x] 准备 git commit + push

### Codex 部署与实车闭环

- [x] 完成 corridor v2 首轮代码部署到 `gps`
- [x] 完成 Jetson `pull + colcon build --packages-select gps_waypoint_dispatcher bringup --symlink-install --parallel-workers 1`
- [x] 完成 quiet corridor 前台监控，前台只显示简化状态
- [x] 完成多轮实车测试与日志回读
- [x] 当前已确认：系统能正常进入 `RUNNING_ROUTE`

### 最新 Step 29 分析结论

- [x] 最新实车 session `2026-03-22-15-16-00` 已推进到第一个 waypoint 的倒数第二个 subgoal
- [x] PGO 本轮已 ready，但 route runner 没有实际切换到 `pgo`，当前切换门槛对现场约 `~1Hz` 的更新频率仍然过严
- [x] Nav2 的绿色路径 `/plan` 确认由 planner 基于 global costmap 生成；local controller 再结合 local costmap 跟踪
- [x] 最新问题性质判断：**不是架构 blocker，而是 Step 21 小问题**
- [x] 用户结束本轮实车测试，当前进入会话收尾

### 最新架构调研触发点（2026-03-22 Night）

- [x] 用户再次实测，确认：bootstrap 阶段车辆可较直地推进第一个 waypoint
- [x] 一旦切到 PGO，对齐源开始继续漂移，subgoal 链被重算，车辆出现回头/倒车 recovery
- [x] 已从日志确认：
  - 切换前：`1/1|41.70|-1.84|bootstrap`
  - 切换后：`1/2|46.13|-5.28|pgo`
  - `pgo_node` 在接管后仍持续 `alignment updated`
  - `serial_twistctl_node` 实际发出 `linear.x=-0.050`
- [x] 用户要求 Codex 暂代 CC，深度调研"GPS 是否还应继续融合进 PGO，还是改成独立 global aligner"

### 最新架构调研结论（2026-03-22 Night）

- [x] 已基于最新日志、当前代码和官方资料完成首轮架构调研
- [x] 结论不是"去掉 GPS"，而是：
  - GPS 仍应参与全局纠偏
  - 但不应继续以当前这种 live PGO handoff 方式直接进入 corridor 控制闭环
- [x] 已确认当前更合理方向：
  - 保留 FAST-LIO2 作为局部连续里程计主链
  - 引入独立 `global_aligner`，平滑发布 `ENU -> map`
  - runner 继续消费 `alignment_topic`
  - 不在当前 subgoal 中途因对齐源变化而重算已执行进度
- [x] 已确认"整包替换成另一套 GPS 紧耦合 SLAM"当前并非低风险方案
  - 官方 LIO-SAM 与当前 ROS2 Humble + MID360 栈不构成低成本 drop-in replacement
  - 若要尽量复用现成件，更接近正确方向的是 `robot_localization + navsat_transform` 这类分层全局定位模块
- [x] 已形成首轮可部署方案：
  - 新增 `gps_global_aligner_node`
  - corridor 模式下关闭 `pgo.gps.enable`
  - route runner 改成消费稳定 alignment，不再做 live PGO handoff
  - route runner 保持 ENU 域进度，不在 alignment 更新时回跳 subgoal

### CC 复审（针对 Codex 部署性审查发现）

- [x] 确认 Codex 发现 1-5（部署性补充）全部合理
- [x] 确认 Codex 发现 6（启动死锁）是真实 blocker
- [x] 调研 FAST-LIO2 yaw 初始化机制（imu_processor.cpp 源码分析）
- [x] 关键发现：yaw0 在相同物理放置下变化 < 0.1°（FromTwoVectors 确定性）
- [x] **裁决：采用方案 A（固定 yaw bootstrap），淘汰 10m 预热方案**
- [x] 更新 task_plan.md：Section 2.7 + 3.3 重写
- [x] 移除 startup_forward_prewarm_m 相关内容

### Codex 二次部署性审查（Bootstrap 方案 A）

- [x] 核对 FAST-LIO2: `gravity_align: true` 与 `imu_processor.cpp` 的 `FromTwoVectors` 代码路径存在
- [x] 核对启动 TF 链: FAST-LIO2 发布 `odom -> base_link`，PGO 发布 `map -> odom`，runner 读取 `map -> base_link` 的链路成立
- [x] 核对 Phase 3 包依赖: `gps_waypoint_dispatcher` 已声明 `python3-pyproj`
- [x] 发现并补充一个部署约束: `launch_yaw_deg` 不能在短首段上静默自动生成，采集脚本必须显式确认/必要时手填
- [x] 结论: **新计划可部署，Step 19 通过**

### 独立 Global Aligner 架构部署与实车验证

- [x] commit `e51a46a`: 新增 `gps_global_aligner_node.py`
- [x] commit `7d77f10`: 冻结 waypoint 内 alignment，扩大 costmap 窗口
- [x] commit `3f66c5a`: 收紧 aligner 更新限速，平滑 waypoint 边界切换
- [x] commit `2bb6fbf`: 修复 runtime 清理链，补杀残留进程
- [x] session `2026-03-22-21-05-17`: **waypoint 1 已稳定到达**
- [x] 架构改进生效：从"无法起跑"推进到"waypoint 1 完成"

### 文档更新（2026-03-23）

- [x] 更新 `devlog/2026-03.md`: 补充独立 global aligner 架构部署与实车验证
- [x] 更新 `known_issues.md`: 更新 costmap 问题状态，记录 waypoint 1 到达
- [x] 更新 `knowledge/gps_planning.md`: 更新 corridor v2 架构描述
- [x] 更新 `docs/index.md`: 更新日期到 2026-03-23
- [x] 更新 L2 进度文件

### 之前完成

- [x] 深度调研 5 个问题 + PGO 源码分析 + 算法设计
- [x] 三轮自审迭代 + 代码级审计
- [x] 用户审批通过 → Codex 两轮部署性审查 → 发现启动死锁 → 交回 CC

### CC 微调优化计划（Step 8-16）

- [x] 读取当前分支代码，理解系统现状
- [x] 加载 Superpowers skill
- [x] 审核用户需求：3 个微调问题（PGO 接管门槛、costmap 残留、频率掉频）
- [x] 派第一轮子代理调研（误分析了未启用节点）
- [x] 用户纠正：检查实际启用节点
- [x] 派第二轮子代理调研（分析实际运行节点）
- [x] 自审计划：发现 costmap raytrace 方案有高风险
- [x] 派多个子代理联网验证：
  - FAST-LIO2 参数优化（可行性：中等）
  - Costmap raytrace 优化（可行性：中低，建议用 STVL）
  - Controller 频率优化（可行性：高）
  - Jetson 20Hz 方案验证（可行性：低，推荐最高 5Hz）
- [x] 与用户讨论 Global Costmap 刷新率重要性
- [x] 用户确认方案 B（激进频率提升：Local 12Hz, Global 5Hz）
- [x] 输出完整优化计划（Step 14）
- [x] 用户确认计划（Step 15）
- [x] planning-with-files 记录进度（Step 16）

### Codex 部署性审查（方案 B）

- [x] 读取 CC 新方案及 L2 增量
- [x] 核对当前代码状态：PGO 门槛、Nav2 频率、BT 插件链
- [x] 核对 Jetson 运行环境：STVL 包当前未安装，但 apt 可用
- [x] 核对 Nav2 Humble 默认 BT：planner replan 仍是 `1Hz`
- [x] 发现部署缺口 1：`global_costmap 5Hz` 不能直接实现“绿色 /plan 更快”
- [x] 发现部署缺口 2：STVL 配置块不完整，且缺失安装前置步骤
- [x] 在不改变架构前提下补充部署约束：
  - `global_costmap 5Hz` 改为 staged rollout
  - STVL 补 apt install + 完整 MID360 参数块
- [x] 结论：**方案 B 经微调后可部署，Step 19 通过**

### CC 文档阶段（Step 33-38）

- [x] 读 L2 文件（git diff 看 Codex 更新）
- [x] 读 docs/index.md
- [x] 判断文档类型：无需新增，更新现有文档
- [x] 更新所有相关文档：
  - `devlog/2026-03.md`: 新增 corridor v2 部署与实车测试条目
  - `known_issues.md`: 更新 GPS RF 状态、costmap 残留新发现、新增 PGO handoff 和 controller/planner 掉频问题、更新 corridor v1→v2 状态
  - `knowledge/nav2_tuning.md`: 新增 corridor RPP 控制器参数、更新 costmap 参数与实车发现
  - `knowledge/gps_planning.md`: 更新当前状态、新增 corridor v2 架构与实车验证章节
  - `knowledge/pgo.md`: 更新 GPS topic `/gnss`→`/fix`、新增 corridor v2 ENU→map 对齐机制章节
  - `commands.md`: 新增 corridor quiet 模式说明
  - `index.md`: 更新日期与当前系统摘要
- [x] 调用 planning-with-files 记录进度
- [x] 准备 git commit + push

### Codex 部署与实车闭环

- [x] 完成 corridor v2 首轮代码部署到 `gps`
- [x] 完成 Jetson `pull + colcon build --packages-select gps_waypoint_dispatcher bringup --symlink-install --parallel-workers 1`
- [x] 完成 quiet corridor 前台监控，前台只显示简化状态
- [x] 完成多轮实车测试与日志回读
- [x] 当前已确认：系统能正常进入 `RUNNING_ROUTE`

### 最新 Step 29 分析结论

- [x] 最新实车 session `2026-03-22-15-16-00` 已推进到第一个 waypoint 的倒数第二个 subgoal
- [x] PGO 本轮已 ready，但 route runner 没有实际切换到 `pgo`，当前切换门槛对现场约 `~1Hz` 的更新频率仍然过严
- [x] Nav2 的绿色路径 `/plan` 确认由 planner 基于 global costmap 生成；local controller 再结合 local costmap 跟踪
- [x] 最新问题性质判断：**不是架构 blocker，而是 Step 21 小问题**
- [x] 用户结束本轮实车测试，当前进入会话收尾

### 最新架构调研触发点（2026-03-22 Night）

- [x] 用户再次实测，确认：bootstrap 阶段车辆可较直地推进第一个 waypoint
- [x] 一旦切到 PGO，对齐源开始继续漂移，subgoal 链被重算，车辆出现回头/倒车 recovery
- [x] 已从日志确认：
  - 切换前：`1/1|41.70|-1.84|bootstrap`
  - 切换后：`1/2|46.13|-5.28|pgo`
  - `pgo_node` 在接管后仍持续 `alignment updated`
  - `serial_twistctl_node` 实际发出 `linear.x=-0.050`
- [x] 用户要求 Codex 暂代 CC，深度调研“GPS 是否还应继续融合进 PGO，还是改成独立 global aligner”

### 最新架构调研结论（2026-03-22 Night）

- [x] 已基于最新日志、当前代码和官方资料完成首轮架构调研
- [x] 结论不是“去掉 GPS”，而是：
  - GPS 仍应参与全局纠偏
  - 但不应继续以当前这种 live PGO handoff 方式直接进入 corridor 控制闭环
- [x] 已确认当前更合理方向：
  - 保留 FAST-LIO2 作为局部连续里程计主链
  - 引入独立 `global_aligner`，平滑发布 `ENU -> map`
  - runner 继续消费 `alignment_topic`
  - 不在当前 subgoal 中途因对齐源变化而重算已执行进度
- [x] 已确认“整包替换成另一套 GPS 紧耦合 SLAM”当前并非低风险方案
  - 官方 LIO-SAM 与当前 ROS2 Humble + MID360 栈不构成低成本 drop-in replacement
  - 若要尽量复用现成件，更接近正确方向的是 `robot_localization + navsat_transform` 这类分层全局定位模块
- [x] 已形成首轮可部署方案：
  - 新增 `gps_global_aligner_node`
  - corridor 模式下关闭 `pgo.gps.enable`
  - route runner 改成消费稳定 alignment，不再做 live PGO handoff
  - route runner 保持 ENU 域进度，不在 alignment 更新时回跳 subgoal

### CC 复审（针对 Codex 部署性审查发现）

- [x] 确认 Codex 发现 1-5（部署性补充）全部合理
- [x] 确认 Codex 发现 6（启动死锁）是真实 blocker
- [x] 调研 FAST-LIO2 yaw 初始化机制（imu_processor.cpp 源码分析）
- [x] 关键发现��yaw0 在相同物理放置下变化 < 0.1°（FromTwoVectors 确定性）
- [x] **裁决：采用方案 A（固定 yaw bootstrap），淘汰 10m 预热方案**
- [x] 更新 task_plan.md：Section 2.7 + 3.3 重写
- [x] 移除 startup_forward_prewarm_m 相关内容

### Codex 二次部署性审查（Bootstrap 方案 A）

- [x] 核对 FAST-LIO2: `gravity_align: true` 与 `imu_processor.cpp` 的 `FromTwoVectors` 代码路径存在
- [x] 核对启动 TF 链: FAST-LIO2 发布 `odom -> base_link`，PGO 发布 `map -> odom`，runner 读取 `map -> base_link` 的链路成立
- [x] 核对 Phase 3 包依赖: `gps_waypoint_dispatcher` 已声明 `python3-pyproj`
- [x] 发现并补充一个部署约束: `launch_yaw_deg` 不能在短首段上静默自动生成，采集脚本必须显式确认/必要时手填
- [x] 结论: **新计划可部署，Step 19 通过**

### 之前完成

- [x] 深度调研 5 个问题 + PGO 源码分��� + 算法设计
- [x] 三轮自审迭代 + 代码级审计
- [x] 用户审批通过 → Codex 两轮部署性审查 → 发现启动死锁 → 交回 CC

---

## Codex 需要知道的

1. **启动死锁已解决**: Runner 用 `yaw0_from_TF - radians(launch_yaw_deg)` 在上电瞬间算出初始 ENU→map，无需等 PGO valid
2. **10m 预热方案已淘汰**: 数学上不需要，浪费距离和时间
3. **route YAML 的 launch_yaw_deg 是必填字段**: 对直线 corridor 可复用 bearing_deg，但多点路线采集时必须显式确认
4. **Codex 发现 1-5 全部认可**: 已体现在更新后的 task_plan.md 中
5. **当前最新断点不是计划审查，而是运行期微调**
6. **不要再默认继续拉高 costmap 刷新率**：最新日志已经显示 controller/planner 掉频
7. **PGO 已能在运行中算出 valid ENU->map**，但 handoff gate 仍未和现场更新频率匹配
8. **最新问题已不再只是调参**：PGO 接管后 runner 会重算剩余 subgoal，且 `map->odom` 在接管后仍继续漂移
9. **当前新断点是架构调研**：评估 `GPS-in-PGO` 与“独立 global aligner + runner 消费 `ENU->map`”两条路径
10. **架构调研已有首轮结论**：推荐方向是“保留 FAST-LIO2，拆出独立 global aligner”，而不是继续强化当前 live PGO handoff
11. **若用户要求尽量用现成包**：优先考虑 `robot_localization/navsat_transform` 作为全局对齐模块骨架，而不是直接整包换 SLAM
12. **新方案的最大实现风险不在定位数学，而在 runner 进度语义**：必须避免 alignment 更新时重切当前剩余 subgoal 链
13. **修正 v2 已部署到 Jetson**：远端 `gps` 分支已快进到 `a7dc2fd`，`gps_waypoint_dispatcher` + `bringup` build 通过
14. **2026-03-24 零运动 smoke test 仍卡在 GPS**：session `/home/jetson/fyp_runtime_data/logs/2026-03-24-12-34-31/` 中 Nav2 生命周期正常激活，但 `nmea_navsat_driver` 仍持续输出 `fix=0 / satellites=0 / ANTENNA OK`

---

## 断点位置

**Step 33-38 文档阶段已完成（9 个文件 + L2 更新 + commit）。下一步等待现场恢复 stable GPS fix 后，用真实 route 完成 corridor 启动验证（Step 25 最终验证），再交给用户进入 Step 26 实车测试。**

---

## 优化方案 B 摘要

### Phase 1（锁定后首轮部署）
1. PGO 接管门槛：`pgo_switch_min_stable_updates: 3`（从 4 降到 3）
2. Costmap 频率：Local 12Hz（从 10），Global 3Hz（首轮），5Hz 作为二轮实验值
3. STVL 障碍清除：需先安装 `ros-humble-spatio-temporal-voxel-layer`，并补完整 MID360 参数
4. Controller：保持 20Hz

### Phase 2（可选）
5. FAST-LIO2：`det_range: 55.0`（从 60）
6. PGO 回环：`loop_search_radius: 1.5`（从 1.0）

### 风险与回退
- Phase 1.2 有中高风险（Jetson 可能掉频）
- 回退方案：Local 10Hz / Global 3Hz

---

## 历史摘要

2026-03-21: corridor v1 概念→实车验证
2026-03-21~22: 深度调研 + 算法设计 + 计划编写 + 审计
2026-03-22: 用户审批 → Codex 两轮审查（发现启动死锁）→ CC 复审（锁定方案 A bootstrap）→ Codex 二次审查通过
2026-03-22: Codex 完成 corridor v2 首轮部署 → 多轮实车测试 → 问题收敛到 costmap / planner / controller / PGO handoff 微调
2026-03-22 晚: 独立 global aligner 架构已部署；最新实车已首次完整到达 waypoint 1，并开始执行 waypoint 2；当前问题后移到 waypoint 2 边界 alignment 漂移 + Nav2 stop-go

---

## 最新运行断点（2026-03-22 21:05 session）

- session: `/home/jetson/fyp_runtime_data/logs/2026-03-22-21-05-17/`
- 已确认：
  - waypoint 1 已到达
  - runner 进入 `WAYPOINT_TARGET|2|2|right-bottom-corner`
  - 第二个 waypoint 开始即发送 `subgoal 3/7`，且 `progress=16.51/49.21`
- 当前判断：
  - 第二段一开始就“已经走了 16.5m”不合理，说明 waypoint 边界冻结到的 alignment 已偏
  - stop-go 主因是 controller `collision ahead` + TF future extrapolation，不是电机硬件
- 下一轮优先级：
  1. 收紧/限幅 global aligner 在 waypoint 边界的漂移，避免第二段起始投影跳入建筑或跳过前两个 subgoal
  2. 只通过 Nav2 参数微调提升平顺性：降低误触发 collision ahead，减少 future extrapolation 对 controller 的扰动

---

## 工作流收口断点（2026-03-22 夜）

- 已完成：
  - `3f66c5a`：收紧 global aligner + waypoint 边界 guard + Nav2 平顺性微调
  - `2bb6fbf`：修复 runtime 清理链，补杀 `gps_global_aligner`，并在每次 corridor 启动前预清理残留节点
- 已确认根因：
  - “一启动直接 SUCCEEDED” 主要由旧 `gps_global_aligner` 残留进程污染新一轮 runner 引起
  - RViz 偶发空白更像该残留 bug 的连带现象，不是 RViz 自身启动失败
- 当前阻塞：
  - Jetson SSH 暂时超时，尚未完成 `2bb6fbf` 的现场 pull、残留进程清理和复验
- 下次恢复工作流时的首步：
  1. Jetson `git pull --ff-only origin gps`
  2. `make kill-runtime`
  3. 重新实车测试 corridor
  4. 重点复核“第一段持续右偏”和“第二段仍朝建筑偏”是否在干净运行环境下依然存在

# FYP Autonomous Vehicle - Findings

**最后更新**: 2026-03-24

---

## 2026-03-24 Codex 恢复部署后的现场发现

### 1. 修正 v2 已真正部署到 Jetson，原 Step 23 阻塞已解除

- Jetson 当前可通过 `ssh jetson@100.97.227.24` 访问
- 远端 `gps` 分支原先停在 `1898655`
- 本轮已成功执行 `git pull --ff-only origin gps`，快进到 `a7dc2fd`
- `a7dc2fd` 的变更集只涉及：
  - `src/bringup/config/nav2_explore.yaml`
  - `src/bringup/config/master_params.yaml`
  - `src/navigation/gps_waypoint_dispatcher/gps_waypoint_dispatcher/gps_route_runner_node.py`
  - L2 文件
- Jetson 现存脏文件仅为 `src/perception/pgo_gps_fusion/rviz/pgo.rviz`，与本轮修正无关，没有阻塞 pull

结论：
- 之前的“Jetson 不可达，部署卡在 Step 23”已不再成立
- 修正 v2 代码已经真实落到车端工作区

### 2. 修正 v2 的车端 build 已通过，当前没有新的构建级回归

- Jetson 已执行：
  - `colcon build --packages-select gps_waypoint_dispatcher bringup --symlink-install --parallel-workers 1`
  - `source install/setup.bash`
- `ros2 pkg prefix bringup` 与 `ros2 pkg prefix gps_waypoint_dispatcher` 都正常返回 `~/fyp_autonomous_vehicle/install/...`

结论：
- 本轮参数回退与 guard 收紧没有引入新的 build/package 级断裂

### 3. 2026-03-24 零运动 corridor smoke test 证明启动链正常，阻塞点仍是 GPS `NO_FIX`

- 为避免在用户不在场时触发真实行驶，本轮使用临时 `deploy_smoke_route.yaml`
  - 唯一 waypoint 直接设为 `start_ref`
  - 用于验证 corridor 全链路启动，不发实际导航目标
- smoke test session：`/home/jetson/fyp_runtime_data/logs/2026-03-24-12-34-31/`
- 启动日志确认：
  - `lifecycle_manager_navigation`: `Managed nodes are active`
  - `controller_server`: `Controller frequency set to 15.0000Hz`
  - `gps_global_aligner`: `ALIGNER_WAITING_FOR_STABLE_FIX`
  - `gps_route_runner`: `WAITING_FOR_STABLE_FIX`

- 同一 session 中，`nmea_navsat_driver` 仍持续输出：
  - `GNGGA ... 0,00,...`
  - `GNRMC,,V,...`
  - `GPGSV,1,1,00`
  - `BDGSV,1,1,00`
  - `GPTXT ... ANTENNA OK`

结论：
- 本轮没有看到 launch / lifecycle / plugin / build 级回归
- 当前阻塞再次确认仍是：
  - 天线在线
  - 但 GPS 无 fix、可见卫星数 0
- 因此真实 corridor 启动与后续 Step 26 实车测试，仍需等现场具备 stable GPS fix

---

## 2026-03-22 微调优化调研发现

### 1. Nav2 绿色路径 `/plan` 的生成机制

- **来源**: Planner Server 基于 **Global Costmap** 规划
- **算法**: NavfnPlanner（当前配置）
- **更新频率**: 受 Global Costmap 更新频率限制（当前 2Hz）
- **影响**: Global Costmap 更新慢 → 绿色路径滞后 → 可能指向错误位置

**关键发现**: Local Controller 有双层防护机制，会基于 Local Costmap 实时避障，不会盲目跟随绿色路径。

### 2. Costmap 障碍清除机制

**标准 VoxelLayer 的局限**:
- 依赖 raytrace 清除（需要传感器提供"障碍后方无物体"的证据）
- `raytrace_min_range` 创建死区，死区内障碍无法被 raytrace 清除
- 增大 `raytrace_min_range` 会扩大死区，可能漏检近距离障碍

**STVL（Spatio-Temporal Voxel Layer）优势**:
- 每个 voxel 存储时间戳，超时自动移除
- 不依赖 raytrace，通过时间衰减自动清除
- `voxel_decay: 2.0` 可实现 ~0.5 秒清除（vs 标准层 ~2 秒）
- 专为动态环境设计

### 3. Jetson Orin NX 算力边界

**当前状态**:
- Local Costmap 10Hz + Global Costmap 2Hz + Controller 20Hz 已出现掉频
- Controller 反复 miss 20Hz 目标
- Planner 降至 ~2Hz

**社区实践**:
- Global Costmap 典型值: 1-2Hz
- 嵌入式平台最高: 3-5Hz
- **从未见过 20Hz Global Costmap 案例**

**20Hz 全局方案风险**:
- Global Costmap 从 2Hz → 20Hz = 10 倍负载
- 会导致系统崩溃或严重掉频

**推荐最高频率**:
- Local Costmap: 10-12Hz
- Global Costmap: 3-5Hz
- Controller: 20Hz（如果 Costmap 不掉频）

### 4. Nav2 频率配置最佳实践

**1:2 比例原则**:
- Costmap : Controller = 1:2
- 例如: Local Costmap 10Hz, Controller 20Hz

**Planner 频率**:
- 架构设计为低频（1Hz）
- 由 Behavior Tree 控制重规划时机
- 即使设置 20Hz，实际仍是 1Hz

### 5. 联网验证结论汇总

| 优化项 | 可行性 | 推荐方案 |
|--------|--------|----------|
| FAST-LIO2 det_range 50m | 中等 | 55m 更保守 |
| Costmap raytrace 扩大死区 | 低 | 用 STVL 替代 |
| Controller 18Hz | 高 | 可行 |
| Global Costmap 20Hz | 低 | 最高 5Hz |
| Local Costmap 12Hz | 中 | 可尝试，有风险 |

---

## 2026-03-23 Codex 对修正方案 v2 的收敛修正

### 1. 高度门限改动被从锁定批次中移除

- 原始修正 v2 试图把 local/global `min_obstacle_height` 统一抬到 `0.15`，并把 `pointcloud_clear.min_z` 抬到 `0.10`
- 但仓库内现有高度参考写明：
  - `base_link` 离地约 `0.403m`
  - `body_cloud` 中地面 `z ≈ -0.40m`
  - `10cm` 马路牙 `z ≈ -0.30m`
  - `50cm` 矮墙 `z ≈ +0.10m`
- 因此若把 `min_obstacle_height` 直接抬到 `0.15`，会有过滤约 `50cm` 低矮真实障碍的风险
- 另外，STVL 官方 README 中 `min_z` 是 clearing source 的 z 过滤参数；当前项目没有足够证据证明把它从 `0.05` 抬到 `0.10/0.15` 会更安全

结论：
- 这组高度门限改动不进入当前锁定部署批次
- 当前锁定版保持 local/global `min_obstacle_height=0.05`、`pointcloud_clear.min_z=0.05`

### 2. `max_allowed_time_to_collision_up_to_carrot` 锁定为回退到 `0.6`，而不是改到 `0.8`

- `1.2` 已确认方向错误：检测更远碰撞，导致更多停车
- 但 `0.8` 仍比最近一次实际跑通路线时的 `0.6` 更敏感
- 在高度门限改动被移出本轮后，当前没有足够现场证据支持把 collision time 从 `0.6` 上调到 `0.8`

结论：
- 当前锁定版把 `max_allowed_time_to_collision_up_to_carrot` 从 `1.2` 回退到 `0.6`
- 这不是“最激进优化”，但它是当前证据下更稳妥的部署口径

### 3. 当前可直接部署的修正 v2 子集

- `max_allowed_time_to_collision_up_to_carrot: 1.2 -> 0.6`
- local `denoise_layer.minimal_group_size: 3 -> 4`
- `/gps_route_runner.waypoint_start_progress_guard_m: 10.0 -> 5.0`
- global STVL `transform_tolerance: 0.35 -> 0.5`

审查结论：
- **原始修正 v2 文本：不可直接部署**
- **经 Codex 收敛后的锁定版：可部署**
- 当前 Step 19 已闭环，可以进入 Step 20 等用户锁定

---

## 2026-03-23 Codex 对修正方案 v2 的部署性审查发现

### 1. `task_plan.md` 当前同时保留了修正 v2 和旧 v1 指令，存在直接执行歧义

- 顶部修正 v2 要求：
  - `max_allowed_time_to_collision_up_to_carrot: 0.8`
  - `waypoint_start_progress_guard_m: 5.0`
- 但同一文件后半仍保留旧 v1：
  - `max_allowed_time_to_collision_up_to_carrot: 1.2`
  - `waypoint_start_progress_guard_m: 10.0`

结论：
- 不先收敛文本，部署执行口径不唯一

### 2. `min_obstacle_height: 0.15` 与仓库现有高度参考冲突，存在过滤真实低矮障碍的风险

- `task_plan.md` 当前已记录的坐标参考写明：
  - `base_link` 离地约 `0.403m`
  - `body_cloud` 中地面 `z ≈ -0.40m`
  - `10cm` 马路牙 `z ≈ -0.30m`
  - `50cm` 矮墙 `z ≈ +0.10m`
- 因此若把 `pointcloud_mark.min_obstacle_height` 提到 `0.15`，按现有参考会把约 `50cm` 低墙也从 Local + Global STVL 中过滤掉
- 这不是代码注入问题，而是参数目标与已知实测参考不一致

### 3. 其余 v2 修改项本身没有发现新的部署链断点

- `nav2_explore.yaml` 中目标字段都真实存在：
  - local/global `min_obstacle_height`
  - local/global `min_z`
  - `max_allowed_time_to_collision_up_to_carrot`
  - `denoise_layer.minimal_group_size`
  - global STVL `transform_tolerance`
- `master_params.yaml` 和 `gps_route_runner_node.py` 也都能承接 `5.0` 的 waypoint guard 调整

审查结论：
- **修正方案 v2 原文：不可直接部署**
- 原因不是拉不起来，而是计划口径冲突 + 低矮障碍过滤风险未闭合
- 需要 CC 先输出收敛后的单一版本方案，再进入 Step 20 锁定

---

## 2026-03-23 Codex 对运行期微调方案的部署性审查发现

### 1. Phase 2 计划当前少了一处真正的生效文件

- `system_gps_corridor.launch.py` 启动 `gps_route_runner` 时，会先加载 `master_params.yaml`
- 当前 `master_params.yaml` 中 `/gps_route_runner` 仍写着：
  - `waypoint_start_progress_guard_m: 4.0`
  - `waypoint_start_cross_track_guard_m: 3.0`
- 因此若只改 `gps_route_runner_node.py` 里的 `declare_parameter()` 默认值，运行时仍会被 YAML 覆盖

结论：
- 这不是“建议最好改”的问题，而是**不补 `master_params.yaml` 就不会生效**

### 2. Planner `transform_tolerance` 这一项本身没有部署冲突

- 当前仓库里：
  - `planner_server.transform_tolerance = 0.5`
  - 搜索里另一个 `1.0` 来自 `amcl`
- 因此计划里的 `planner 0.5 -> 0.8` 是对的，不存在“把 1.0 错降到 0.8”的风险

### 3. 运行期微调方案经微调后可部署

- 原计划存在 1 个部署缺口：
  - Phase 2 少改 `master_params.yaml`
- 在不改变架构的前提下补齐后：
  - Nav2 参数调优部分可直接部署
  - Runner waypoint 边界保护也可直接部署

审查结论：
- **原文：不可直接部署**
- **补齐 `/gps_route_runner` 参数覆盖后：可部署**

---

## 2026-03-23 部署后 Jetson Smoke Test 发现

### 1. 本轮改动没有破坏 Nav2 启动链

- 最新 smoke test session：`/home/jetson/fyp_runtime_data/logs/2026-03-23-11-22-31/`
- `controller_server`、`planner_server`、`bt_navigator`、`lifecycle_manager` 全部正常启动并进入 active
- `controller_server` 日志明确显示：`Controller frequency set to 15.0000Hz`
- local/global STVL 均正常初始化，没有出现参数不识别或插件加载失败

结论：
- 本轮运行期微调至少通过了 Jetson 启动级验证
- 当前没有证据表明新参数引入了 launch / lifecycle / plugin 级回归

### 2. corridor 没进入 `RUNNING_ROUTE` 的直接原因仍是 GPS `NO_FIX`

- `gps_global_aligner` 状态停在 `ALIGNER_WAITING_FOR_STABLE_FIX`
- `gps_route_runner` 状态停在 `WAITING_FOR_STABLE_FIX`
- `nmea_navsat_driver` 持续输出：
  - `$GNGGA ... 0,00,...` → fix quality `0`
  - `$GNRMC,,V,...` → navigation status `V`（void）
  - `$GPGSV,1,1,00` / `$BDGSV,1,1,00` → 可见卫星数 `0`
  - `$GPTXT ... ANTENNA OK` → 天线连接正常

结论：
- 当前启动超时不是本轮参数改动造成的
- 是现场/环境条件下没有 GPS fix，系统因此按设计停在 stable fix 等待阶段

---

## 2026-03-22 Codex 对方案 B 的部署性审查发现

### 1. `pgo_switch_min_stable_updates: 3` 是真实对症项

- 当前代码里 hold bootstrap 的直接原因已经不是“PGO 没 ready”，而是 recent update 数不够
- 最新实车日志反复出现 `have 3/4 recent PGO updates`
- 因此把门槛从 `4` 降到 `3`，是基于现网日志的低风险修正，不是拍脑袋调参

### 2. Global Costmap `5Hz` 不会自动让绿色 `/plan` 提到 `5Hz`

- 当前仓库没有自定义 BT XML 覆盖默认 NavigateToPose 行为树
- Jetson 本机 `/opt/ros/humble/share/nav2_bt_navigator/behavior_trees/` 下默认 XML 仍使用 `RateController hz="1.0"`
- 因此 planner 重规划仍是约 `1Hz`
- 这意味着：
  - `global_costmap 2Hz -> 5Hz` 可能改善障碍图新鲜度
  - 但**不会直接把绿色 `/plan` 的刷新率提升到 5Hz**

### 3. 现场掉频事实与 `5Hz` 首轮 mandatory 冲突

- 最新日志里 controller 已反复 miss `20Hz`
- planner 还出现过 loop rate 掉到约 `2Hz`
- 所以 `global 5Hz` 若作为首轮 mandatory，会和当前已知性能边界正面冲突

结论：
- `global 5Hz` 更适合作为二轮实验值
- 首轮部署应先落在 `3Hz` 级别

### 4. STVL 当前不具备“开箱即用”条件

- Jetson 上当前没有安装 `ros-humble-spatio-temporal-voxel-layer`
- apt 源里存在候选包，因此可安装，但必须把安装步骤明确写进部署计划

### 5. STVL 配置块当前写法不完整

- STVL 不是当前 `VoxelLayer` 的参数原样复用
- 官方 README 的最小可用示例要求：
  - layer-level `voxel_size`
  - `obstacle_range`
  - `observation_sources`
  - marking / clearing 双 source
  - `model_type`
  - `horizontal_fov_angle`
  - `vertical_fov_angle`
  - 对 3D lidar 的 `vertical_fov_offset`
  - `clear_after_reading`
- 当前计划只写了 `plugin + voxel_decay + decay_model + decay_acceleration + raytrace_min_range`
- 这不足以直接部署

### 6. Livox MID360 需要显式 FOV 偏置处理

- STVL 官方 README 在 3D lidar clearing 示例里明确提到：
  - MID360 的 vertical FOV 约 `-7°` 到 `52°`
  - 对应 `vertical_fov_offset ≈ +22.5° (0.3927 rad)`
- 若切到 STVL 且忽略这个偏置，清障 frustum 可能与真实传感器视场不对齐

结论：
- 方案 B 保留架构前提下可以部署
- 但必须把 `global 5Hz` 改成 staged rollout，并把 STVL 前置条件和完整参数块补齐

## 2026-03-22 Codex Bootstrap A 复审结论

### 1. 新的启动 bootstrap 在当前代码栈上可落地

- `master_params.yaml` 已启用 `gravity_align: true`，FAST-LIO2 初始化确实走 `FromTwoVectors` 重力对齐。
- FAST-LIO2 当前会发布 `odom -> base_link`，PGO 当前会发布 `map -> odom` 并输出 `map` 帧优化里程计，因此 route runner 等待 `map -> base_link` 后读取启动姿态这一链路是成立的。
- `system_explore.launch.py` 现有就把同一份 `master_params.yaml` 同时传给 FAST-LIO2 与 PGO，bootstrap A 不需要额外引入新的底层启动组件。

结论：
- **就部署性而言，CCE 这版“固定 yaw bootstrap”已经闭合了静止启动死锁。**
- 它不再要求车辆先人工/自动预热走一段距离，系统可以在 startup check 完成后直接起跑。

### 2. `launch_yaw_deg` 的采集必须显式确认，不能静默从短首段自动估

- 现有两点 corridor 采集脚本确实已经会输出 `bearing_deg`，直线 corridor 可以直接复用。
- 但多点路线若“起点到第一个 waypoint”基线太短，直接用这段 GPS bearing 生成 `launch_yaw_deg`，会把 GPS 噪声放大成启动角误差。
- 因此新的 `collect_gps_route.py` 必须把 `launch_yaw_deg` 作为显式字段处理：
  - 可以给出自动建议值
  - 但必须让用户确认
  - 若首段过短或不可靠，应要求手工输入（例如手机指南针）

这属于部署性微调，不改变 bootstrap A 架构。

### 3. 对 CC 技术论证的代码侧确认边界

- 本地代码能直接确认的是：重力对齐开启、`FromTwoVectors` 存在、以及 startup 时 `map -> odom -> base_link` TF 链可读。
- 本地代码**不能直接证明**“yaw0 启动间变化 < 0.1°”这一具体数值；这是 CC 的调研结论，不是仓库代码里可直接验证的事实。
- 但这不影响部署性审查结论，因为 bootstrap A 真正依赖的是“启动时可读到稳定的 `map -> base_link` 零参考”，不是 IMU 直接给出地理航向。

---

## 2026-03-22 Codex 部署性审查补充

### 1. Phase 1 构建命令需要收紧

- 计划里原先写的 `colcon build --packages-select nav2_costmap_2d nav2_regulated_pure_pursuit_controller nav2_rotation_shim_controller bringup` 不适合当前仓库。
- 本仓库内没有上述 Nav2 源码包；它们是 Jetson 系统里的运行时依赖。
- Phase 1 只改 `bringup` 侧 YAML / launch，实际构建目标应收紧为 `bringup`。

### 2. Corridor 日志方案必须挂接现有 session logging

- 仓库已经有统一入口 `scripts/launch_with_logs.sh`，会创建 `~/fyp_runtime_data/logs/<session>/{console,data,system}`，并维护 `logs/latest`。
- 因此 `system_gps_corridor.launch.py` 不应自行再造一套“独立时间戳目录 + launch.log”规范。
- 正确做法：bag 落到当前 session 根目录下的 `bag/`，节点日志继续使用 `ROS_LOG_DIR` 与 `FYP_LOG_SESSION_DIR`。

### 3. GPS warmup 不是只靠参数就能落地

- 当前 `SimplePGO::addGPSFactor()` 会优先采用 `NavSatFix.position_covariance`，并把 sigma clamp 到 `0.3~5.0m`。
- 所以计划里的“前 5 个 GPS factor 用 `sigma_xy=10.0m` 热身”如果不改 C++ 逻辑，实际上不会生效。
- 这不是架构问题，但属于必须在实现前锁死的部署细节。

### 4. Phase 3 还需要补齐启动入口

- 现有 `gps_waypoint_dispatcher` 包已经有 `gps_corridor_runner_node`，但多点路线新节点如果只新建 `.py` 文件还不够。
- 还必须同步改 `setup.py` 注册 console script，以及 `system_gps_corridor.launch.py` 切换到新 runner。
- 若要继续沿用 Step 25 的统一启动点和 session logging，最好再补 `scripts/launch_with_logs.sh` / `Makefile` 的 corridor 入口。

### 5. Phase 3 参数注入链当前不闭合

- 现有 `master_params.yaml` 里只有 `/gps_waypoint_dispatcher` 参数块。
- 但 `system_gps_corridor.launch.py` 当前启动的节点名是 `gps_corridor_runner_node`，而且只传了内联参数，没有把 `master_params.yaml` 传给该节点。
- 因此如果 Phase 3 的 route runner 依赖固定 ENU 原点参数，当前计划必须补两件事：
  1. 给 route runner 定义独立参数命名空间，并通过 launch 显式注入 `master_params_file`
  2. 启动时校验 route YAML 里的 `enu_origin` 与运行时固定原点一致
- 这仍然是部署性微调，不涉及架构变更。

### 6. 当前计划在固定起点静止启动时存在启动死锁

- Phase 2 规定：PGO 只有在配对数和空间展幅满足阈值后，才把 `/gps_corridor/enu_to_map` 置为 valid。
- Phase 3 规定：runner 要等 `/gps_corridor/enu_to_map` valid 后，才开始发导航目标。
- 因此在“固定物理位置启动，车原地不动等待自动开始”场景下，会出现：
  - 车不动，配对展幅不够
  - PGO 变换始终不 valid
  - runner 始终等待
  - 系统不会自动起跑

结论：
- **按当前原文，这个计划还不能满足‘固定起点放车后自动进入有效态并起跑’。**
- 若要保持现有总体架构不变，必须补一个启动 bootstrap。
- 由于项目已知“固定启动位 + 固定启动朝向”，最小可部署修正是：
  - route YAML 增加 `launch_yaw_deg`
  - runner 用 `start_ref + launch_yaw_deg` 先构造临时 ENU→map，发出第一段短导航
  - 待 PGO 正式对齐有效后，再切换到 PGO 变换

这个修正属于部署性闭环补全，不改变“PGO 最终发布正式 ENU→map，runner 消费它”的主架构。

---

### 7. 用户提出新的启动方案：自动前向 10m 预热

用户新增要求：

- 车辆固定放在启动位
- 车辆固定朝向启动
- 系统启动后先自动沿固定朝向直行约 10m
- 然后再从该位置切入正式 GPS 路线导航

Codex 审查结论：

- 这条方案从部署上能解决“静止启动不产生展幅”的问题
- 但它改变了启动阶段的系统行为，不只是参数级微调
- 它会引入新的架构语义问题，需要 CC 复审，例如：
  - 这 10m 直行是由 route runner 管，还是由单独的启动状态机管
  - 这 10m 是否算正式路线的一部分
  - 若 10m 内仍未得到 valid `enu_to_map`，系统应 abort 还是继续直行
  - 预热阶段是否沿固定朝向无条件直行，还是仍要受 Nav2/避障约束

因此当前最合理的流程是：
- Codex 已记录该方案
- 暂不把它视为已锁定实施计划
- 交回 CC 做架构/方案复审后，再返回 Codex 部署

---

## 2026-03-23 CC 复审发现：运行期微调 v1 参数方向错误

### 1. `max_allowed_time_to_collision_up_to_carrot` 方向反了

Nav2 RPP 源码 `collision_checker.cpp` 确认：
- 该参数定义碰撞前瞻检测的**时间窗口**
- while 循环在 `i * projection_time < max_allowed_time` 内逐步向前模拟
- 任何一步检测到碰撞就返回 true，触发停车
- **增大值 = 检测更远 = 更多碰撞被发现 = 更多停车**
- 从 0.6 → 1.2 ���导致 collision ahead **更频繁**，而不是更少
- 正确方向：应减小到 0.8

来源：Nav2 官方文档 + RPP 源码 + StackExchange 讨论

### 2. collision ahead 236 次的真正主因是 `min_obstacle_height: 0.05`

STVL 的 `min_obstacle_height` 相对 `robot_base_frame`（base_link）：
- 0.05m 相对 base_link = 离地约 45cm
- 室外不平路面上，FAST-LIO2 body_cloud 因 IMU 姿态补偿微小延迟，地面点 z 波动
- 波动到 0.05m 以上时被标记为障碍
- `pointcloud_clear.min_z: 0.05` 导致低层体素无法被清除，虚假障碍残留
- 推荐修正：`min_obstacle_height: 0.15`（离地约 55cm）

### 3. `waypoint_start_progress_guard_m: 10.0` 太宽松

- GPS 2.5m 精度 + theta 残差 2-3 度，正常 progress 不超过 4m
- 10.0 只拦极端跳变，4-10m 中等偏移放过
- GPS 2-sigma = 5m，推荐阈值 5.0m

### 4. Global STVL `transform_tolerance` 遗漏

- Codex v1 只改了 local STVL（0.35→0.5），global 仍是 0.35s
- 应同���修改到 0.5s

---

## 2026-03-22 调研最终结论

### 1. 导航定位链路

Nav2 全程用 SLAM（FAST-LIO2 via PGO）定位，GPS 在导航期间不参与：

```
Livox MID360 → FAST-LIO2 → PGO → map→base_link TF → Nav2
GPS: 仅在 corridor runner 启动时做 sanity check（距 start_ref < 6m）
```

### 2. PGO GPS 融合深度分析

**源码**: `src/perception/pgo_gps_fusion/src/pgo_node.cpp` (926行) + `pgos/simple_pgo.cpp`

| 组件 | 实现 |
|------|------|
| GPS→ENU | GeographicLib::LocalCartesian（WGS84 椭球），固定原点 (31.274927, 120.737548) |
| GPS Factor | gtsam::GPSFactor — 只约束平移，不约束旋转 |
| 里程计因子 | BetweenFactor，噪声方差 1e-4~1e-6 |
| 首帧先验 | 方差 1e-12（基本锁死） |

**三个结构性缺陷**:
1. Topic `/gnss` vs 实际 `/fix` — 数据收不到
2. ENU→map 无旋转估计 — GPS ENU (x=东,y=北) 被直接当 map 坐标，但 map yaw 随机
3. 权重失衡 — GPS 权重比里程计低 62,500 倍，融合无效

**关键代码位置**:
- GPS factor 添加: `tryAddGPSFactor()` 第 753-807 行
- 旋转估计最佳插入点: 第 787 行（ENU 转换完成后）、第 790 行（addGPSFactor 前）
- SLAM 位姿: `m_pgo->keyPoses()[idx].t_global`（map 帧）
- offset 更新: `smoothAndUpdate()` 第 185-187 行（用 ISAM2 优化后位姿）
- 首帧先验: `addKeyPose()` 第 49 行

**跳变风险评估**: GPS factor 延迟引入（旋转估计完成后才加入）不会导致地图跳变，因为首帧先验锁死 + GPS 权重极低。但这也意味着 GPS 几乎无效，需要同步放松先验。

### 3. 已有 GPS Offset 实现

`gps_anchor_localizer_node`（`src/sensor_drivers/gnss/gnss_calibration/`）:
- /fix → pyproj ENU → 锚点匹配 → offset → /gnss
- PGO 订阅 /gnss（设计管道完整，但 corridor launch 未启动此节点）
- **新方案不使用此节点** — PGO 自行估计完整 ENU→map 变换，更简洁

### 4. 终点精度根因

**yaw0 不确定性**（非 GPS 漂移）。body_vector 被 yaw0 旋转后偏向。5° yaw 误差在 50m = 4.4m 偏差。

### 5. Nav2 路径质量

- **折弯/卷团**: DWB RotateToGoal/GoalAlign scale=300 → 解决方案: RPP 控制器
- **幻影障碍**: costmap 0.02m + min_obstacle_height=-0.3 → 解决方案: 0.05m + 0.15m + VoxelLayer
- **全局过重**: 625万格 → 解决方案: 0.10m/30×30 = 9万格

### 6. Nav2 插件可用性（Jetson 已编译确认）

- `libnav2_regulated_pure_pursuit_controller.so` ✓
- `libnav2_rotation_shim_controller.so` ✓
- `libvoxel_grid.so` ✓
- `nav2_costmap_2d::DenoiseLayer`（costmap2d 库内）✓

### 7. 旋转估计算法验证

2D 最小二乘旋转估计（cross-covariance → atan2）:
- 架构兼容: PGO 的 `t_global` 可获取 map 帧位姿，与 ENU 配对 ✓
- offset 计算自然受益: 优化后 global 位姿反映 GPS 拉力 ✓
- 跳变安全: 当前权重下延迟引入无跳变风险 ✓

---

## 已归档发现

---

## 2026-03-22 Latest Step 29 Runtime Findings

### 1. 当前系统已经能起跑，但还未跑通第一个 waypoint

- 最新实车 session: `~/fyp_runtime_data/logs/2026-03-22-15-16-00/`
- route runner 已成功进入 `RUNNING_ROUTE`
- 先后发出了第一个 waypoint `right-top-corner` 的多个 subgoal:
  - `1/6` at `(7.03, -0.31)`
  - `1/5` at `(13.71, -0.55)`
  - `1/4` at `(20.46, -0.80)`
  - `1/3` at `(27.36, -1.03)`
  - `1/2` at `(34.36, -1.32)`
- 用户是在路径异常向后绕行后主动结束会话；这轮不是“启动失败”，而是“运行中 path/costmap/controller 质量不稳”

### 2. PGO 本轮已经 ready，但 runner 实际上没有切过去

- PGO 在日志中明确进入 `ENU->map alignment ready`
- runner 也连续收到了有效的 `/gps_corridor/enu_to_map`
- 但最新日志没有 `SWITCHED_TO_PGO_ALIGNMENT`
- hold reason 反复是：
  - `have 3/4 recent PGO updates`
  - `have 2/4 recent PGO updates`

结论：
- 当前 `pgo_switch_min_stable_updates=4` + `pgo_switch_stable_window_s=3.0` 对现场约 `~1Hz` 的 PGO 更新频率仍然偏严
- 这不是“PGO 算不出来”，而是“切换门槛设成了现场几乎达不到的组合”

### 3. 绿色路径 `/plan` 确实是根据代价地图生成的

- planner 每约 `1Hz` 重算一次 path，controller 日志持续打印 `Passing new path to controller`
- 这属于 Nav2 默认 replan 机制，不是 route runner 每秒乱发目标
- 绿色路径的来源是全局 planner 基于:
  - 当前目标点
  - global costmap
  - 当前 robot pose
  计算出来的 `/plan`
- local controller 再结合 local costmap 对 `/plan` 做近场跟踪和避障

因此：
- **如果 global costmap 里保留了陈旧障碍，绿色路径会先被带弯**
- **如果 local costmap 里残留或误报了近场障碍，controller 会出现 `collision ahead` 和 stop-go**

### 4. 本轮已经看到 global/local costmap 都在参与问题，但权重不同

**global/planner 侧证据**
- planner 报过:
  - `Failed to create a plan from potential when a legal potential was found`
  - `GridBased: failed to create plan with tolerance 0.50`
  - `Planning algorithm GridBased failed to generate a valid path to (13.71, -0.55)`
- 随后 global costmap 收到 `clear entirely` 请求

**local/controller 侧证据**
- controller 持续 `Passing new path to controller`
- 在异常段开始连续报:
  - `RegulatedPurePursuitController detected collision ahead!`
  - `Failed to make progress`
- 随后 local costmap 也被 clear

结论：
- global costmap 的陈旧障碍/误判会先把 `/plan` 带偏
- local costmap 的近场碰撞判定又把这个问题放大成 stop-go、绕行和 recovery
- 这两层都要修，但下一轮优先级应是“先把 global/live obstacle 的陈旧障碍问题收住，再清 local 的 collision ahead 误报”

### 5. 不能简单靠继续提高刷新率解决

- controller 反复报 `Control loop missed its desired rate of 20Hz`
- planner 也报过 `Current loop rate is 2.0759 Hz`
- controller 还出现了 `transformPoseInTargetFrame` future extrapolation

结论：
- 当前系统已经存在计算/时间同步压力
- 继续一味提高 global/local costmap 刷新率，只会增加掉频风险
- 下一轮应优先修：
  - obstacle layer 的 clearing / marking 语义
  - global/local 点云职责边界
  - PGO handoff 门槛
  - TF 时间容忍与控制链延迟

### v7 scene graph（已废弃）

- v7 主链对单 corridor 需求过重
- v7 部署到 Jetson 后被 GPS NO_FIX 阻塞
- GPS 蘑菇头硬件连接正常，室内无信号

---

## 2026-03-22 Night Runtime Findings: PGO 接管后退化

### 1. bootstrap 阶段本身可以稳定推进第一个 waypoint

- 最新 session `~/fyp_runtime_data/logs/2026-03-22-19-34-40/` 中，runner 在 bootstrap 下连续推进：
  - `1/6 -> (6.96, -0.30)`
  - `1/5 -> (13.67, -0.49)`
  - `1/4 -> (20.43, -0.78)`
  - `1/3 -> (27.32, -1.02)`
  - `1/2 -> (34.35, -1.33)`
  - `1/1 -> (41.70, -1.84)`
- 用户现场观察与日志一致：在未切到 PGO 前，车辆能较直地朝第一个 waypoint 推进。

结论：
- 当前 corridor v2 的“前半段能跑”主要来自 fixed-launch bootstrap，而不是 PGO 接管。

### 2. 切到 PGO 的瞬间，当前 subgoal 会被重新计算

- 同一 session 中，runner 在 `1774179440.262` 打印：
  - `Switching to PGO alignment: stable over 5 updates ... bootstrap delta 5.30deg`
  - 随后立即变成 `NAVIGATING_SUBGOAL|right-top-corner|1|2|46.13|-5.28|pgo`
- 切换前最后一个 bootstrap 子目标是 `1/1|41.70|-1.84|bootstrap`

代码原因：
- `gps_route_runner_node.py` 当前在 `_run_waypoint()` 里每一轮都会：
  - 重新选 alignment
  - 重新计算当前 waypoint 的 `target_xy`
  - 重新从 `current_xy -> target_xy` 切分剩余 `subgoals`
  - 永远发送新的 `subgoals[0]`
- 因此切换参考系时，不只是“显示编号回跳”，而是实际剩余子目标链被重建。

结论：
- 这不是 UI 问题，而是 runner 语义问题：PGO 接管会让已经接近完成的 waypoint 重新分段。

### 3. PGO 接管后参考系仍在继续漂移

- `pgo_node` 在切换后继续输出大量 `ENU->map alignment updated`
- 切换后数十秒内，`theta` 大约从 `77.4deg` 持续变化到 `82.1deg`
- 同时 GPS factor 对应的 `map` 投影也持续移动，而不是稳定收敛到单一刚体变换

结论：
- 当前不是“切换到一个已经稳定的全局对齐”，而是“切换到一个仍在运行中漂移的对齐源”。
- 这会直接破坏 Nav2 所依赖的 `map` 坐标稳定性。

### 4. “往回走”不是错觉，系统确实发了倒车恢复

- `serial_twistctl_node` 日志中存在大量 `linear.x=-0.050`
- 时间段与 controller 的 `collision ahead` / `Controller patience exceeded` 对齐

结论：
- 用户看到的“切到 PGO 后开始回头/往回走”不是纯视觉误判
- Nav2 controller 在 recovery / backup 行为中确实发出了负速度

### 5. 当前架构级疑问已形成

- 现象上，bootstrap 阶段明显比 PGO 接管后更稳定
- 但中长期又确实存在一个合理需求：如果 FAST-LIO / odom 跑久了有全局漂移，需要某种 GPS 驱动的全局校正源

因此当前真正需要评估的问题不是“要不要 GPS”，而是：
- GPS 是否应该继续直接耦合进当前 PGO，并在运行中接管 corridor
- 还是应该拆成一个独立的 global aligner，仅负责平滑发布 `ENU -> map`，由 runner 消费

这已经超出普通运行期调参，进入架构级调研范围。

---

## 2026-03-22 Night Architecture Research: GPS-in-PGO vs 独立 Global Aligner

### 1. 官方坐标系语义并不支持“把会跳的全局修正直接当局部控制参考”

- REP-105 明确规定：
  - `odom` 应该连续、平滑、短期准确，但允许长期漂移
  - `map` 应该全局更准，但允许离散跳变
- `robot_localization` 官方文档也沿用这一语义：
  - 融合 GPS 这类可能跳变的全局量测时，`world_frame` 应该是 `map`
  - 同时必须有“别的东西”继续提供 `odom -> base_link`

结论：
- GPS 驱动的全局修正不是不能做
- 但它天然属于“全局层”，不适合在当前 subgoal 中途直接改动局部控制正在追的参考

### 2. ROS 官方推荐范式本身就是“局部连续估计 + 全局绝对修正”分层

- `navsat_transform_node` 的标准链路是：
  1. 局部 odometry / filter 先提供机器人当前局部位姿
  2. GPS 被转换到世界坐标系下的 odometry
  3. 第二个全局估计器再融合 GPS，得到全局一致的定位结果
- 这说明 GPS 参与纠偏是对的，但它本来就更像“额外的全局对齐模块”，而不是唯一的局部连续估计主链

结论：
- “GPS 必须参与全局校正” 和 “GPS 必须直接耦合进当前 PGO 接管 corridor” 不是同一件事

### 3. Nav2 并不要求全局来源必须是 PGO

- Nav2 官方 GPS 文档明确说明：
  - GPS waypoint following 需要一个 global localization source
  - 这个 source 可以来自 `robot_localization + navsat_transform`
  - 也可以来自其他来源

结论：
- 当前 corridor runner 需要的只是一个稳定的 `ENU -> map` 或等价全局对齐源
- 这个源从架构上完全可以独立于当前 PGO

### 4. 当前代码真正的问题不是“有没有 GPS”，而是“GPS 通过 PGO 进入闭环的方式”

当前实现链路是：
- `pgo_node.cpp`
  - 广播 `map -> odom`
  - 同时发布 `/gps_corridor/enu_to_map`
- `gps_route_runner_node.py`
  - 在 `_run_waypoint()` 每一轮重新选择 alignment
  - 重新计算当前 waypoint 的 `target_xy`
  - 重新切剩余 `subgoals`

这会导致：
1. PGO 接管时，不只是 TF 变了，当前 waypoint 的剩余子目标链也被重建
2. PGO 接管后若继续漂移，会同时影响：
   - 机器人在 `map` 中的位置
   - waypoint 投到 `map` 中的位置
3. 结果是 controller 实际在追一个运行中继续变化的全局参考

结论：
- 当前退化不是“GPS 理论错误”
- 而是“PGO + route runner + Nav2”目前构成了一个不稳定的运行时闭环

### 5. 结合当前项目约束，最合理的方向不是继续强化 GPS-in-PGO 接管

#### 推荐方向 A：独立 Global Aligner（推荐）

- 保留 FAST-LIO2 作为局部连续里程计主链
- corridor 运行时不再让 live PGO 对齐直接接管正在执行的 waypoint
- 新增独立 `global_aligner`
  - 输入：`/fix`、当前局部位姿、固定 ENU 原点、固定启动朝向 / datum
  - 输出：平滑的 `/gps_corridor/enu_to_map`
- runner 继续消费 `alignment_topic`，但消费的是这个更平滑的全局对齐源

优点：
- 最符合当前代码结构：runner 已经抽象成从 `alignment_topic` 读对齐源
- 不需要整包替换 FAST-LIO2 / Nav2
- 保留 GPS 的全局纠偏能力，同时避免 live PGO 图优化直接扰动控制闭环

#### 推荐方向 B：robot_localization / navsat_transform 作为现成 aligner 骨架（可与 A 结合）

- 如果尽量少造轮子，最像官方范式的现成件不是新的 SLAM 包，而是：
  - `robot_localization`
  - `navsat_transform_node`
- 它们更接近“分层全局定位模块”，而不是“替换整个激光 SLAM”

限制：
- `navsat_transform` 需要世界参考航向；当前项目若没有稳定的绝对航向源，仍要利用固定启动朝向 / datum 约束

#### 不推荐方向 C：直接整包替换成另一套 GPS 紧耦合 SLAM（当前阶段不推荐）

- 官方 LIO-SAM README 说明：
  - 原始实现是 ROS1 / `catkin_make`
  - 主要面向机械雷达
  - 需要 9-axis IMU
  - 对 Livox Horizon 这类固态雷达“尚未充分测试”，且 README 直接提示其他 SLAM 方案可能更好
- 当前项目现实是：
  - ROS2 Humble
  - Livox MID360
  - 现有 Nav2 / bringup 已经围绕 FAST-LIO2 建好

结论：
- 直接整包切到 LIO-SAM 类方案，不是低风险 drop-in replacement
- 短中期性价比低于“保留 FAST-LIO2，拆出独立 global aligner”

### 6. 当前最推荐的架构结论

**GPS 仍然应该参与全局纠偏，但不应该继续以当前这种“运行中接管 corridor 的 PGO 图优化结果”方式进入控制闭环。**

更具体地说：
- 短期稳定版：
  - GPS 用于 route 几何 + fixed-launch bootstrap
  - corridor 运行时不再依赖 live PGO handoff
- 中期增强版：
  - 引入独立 global aligner，持续估计平滑的 `ENU -> map`
  - runner 消费它来更新未来目标点在当前局部地图中的位置
  - 但不在当前 subgoal 中途重算已执行进度

这比“继续把 GPS 强塞进当前 PGO 接管链”更符合当前系统证据。

### 7. “直接换更强的紧耦合 SLAM 包”当前不是更优部署路径

- 当前代码栈与现有 launch 结构说明：
  - FAST-LIO2 / PGO / Nav2 / runner 已经形成完整系统
  - 真正不稳定的接口点是 `ENU -> map` 的运行时接管方式，而不是整套 SLAM 根本不能工作
- 官方 LIO-SAM README 并不支持“当前平台低风险直接替换”的判断：
  - 历史主实现仍是 ROS1/catkin 语境
  - 主要面向机械雷达与 9-axis IMU
  - 对 Livox 固态雷达并非 drop-in 主场景

结论：
- 现阶段直接整包换 SLAM，不如：
  - 保留 FAST-LIO2 作为局部主链
  - 把 GPS 全局纠偏拆为独立 global aligner

### 8. 首轮部署最合理的实现不是引入重依赖，而是先做轻量自定义 aligner

- 当前 `gps_waypoint_dispatcher` 已经具备：
  - route YAML 读取
  - ENU 投影
  - TF 查询
  - alignment topic 抽象
- 因此首轮最小可部署实现是：
  - 在该包内新增 `gps_global_aligner_node.py`
  - corridor launch 改为启动它
  - runner 消费它，而不是消费 `pgo_node` 的 live alignment

结论：
- 首轮不需要整包替换
- 也不需要先引入 `robot_localization`
- 更合适的是先用轻量 global aligner 验证架构方向，再决定是否把 aligner 内核升级到官方现成件

### 9. 2026-03-22 晚间最新实车结论：第一个 waypoint 已达成，第二个 waypoint 在边界处被错误投影

- 最新 session：`/home/jetson/fyp_runtime_data/logs/2026-03-22-21-05-17/`
- `gps_route_runner` 已经进入第二个 waypoint：
  - `WAYPOINT_TARGET|2|2|right-bottom-corner`
  - 说明第一个 waypoint 实际已经完成
- 但第二个 waypoint 一开始发出的就是：
  - `Sending right-bottom-corner subgoal 3/7 ... progress=16.51/49.21`
  - 按路线几何，第二段总长约 `49.21m`
  - 若车刚到第一个 waypoint，第二段起始 progress 应接近 `0m`
  - 现在一进第二段就被投影成已经前进了 `16.51m`
- 结论：
  - 这不是 subgoal 切分逻辑自身乱跳
  - 而是 **waypoint 边界处冻结到的 alignment 已经偏移**，导致当前车位被错误投影到第二段内部，用户看到的“第一个子目标掉进建筑里”与此一致

### 10. “走一下顿一下”的直接原因不是电机，而是 controller/costmap/TF 链在抖

- 最新 `controller_server` 日志显示：
  - `Passing new path to controller`：243 次
  - `RegulatedPurePursuitController detected collision ahead!`：236 次
  - `Controller patience exceeded`：16 次
  - `transformPoseInTargetFrame` future extrapolation：51 次
- 最新 `serial_twistctl` 日志显示：
  - `linear.x=0.000`：678 次
- 结论：
  - stop-go 不是驱动层顿挫
  - 是 Nav2 局部控制反复因为“前方疑似碰撞”或 TF 时间外推失败，把线速度压成 `0`，随后再恢复
  - 因此它表现成“走一下、刹一下、转一点、再走”

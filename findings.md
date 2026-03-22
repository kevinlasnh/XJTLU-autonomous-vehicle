# FYP Autonomous Vehicle - Findings

**最后更新**: 2026-03-22

---

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

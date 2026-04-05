# Nav2 参数调优记录

## 1. 基本概念

- 路径（Path）: 由 planner 生成的空间几何点集合
- 轨迹（Trajectory）: 由 controller 生成的带时间和速度约束的可执行运动序列

## 2. 当前车辆运动参数

- `robot_radius`: `0.38625`
- `max_vel_x`: `0.7`（2026-04-01 从 0.45 提升，commit `2471e73`）
- `min_vel_x`: `0.0`
- `max_vel_theta`: `1.0`
- `min_speed_theta`: `0.0`
- `acc_lim_x`: `3.0`
- `decel_lim_x`: `-3.0`
- `acc_lim_theta`: `3.5`
- `decel_lim_theta`: `-3.5`

## 3. 速度平滑器

- `feedback: OPEN_LOOP`
- `odom_topic: /fastlio2/lio_odom`
- `max_velocity: [0.7, 0.0, 1.0]`（2026-04-01 同步提升）
- 原因: 已确认闭环接入现阶段不稳定，继续使用开环是当前真实配置

## 4. Explore / Corridor 主模式当前控制器（2026-04-01 更新）

Explore 和 Corridor 模式已统一使用 MPPI 控制器（`nav2_explore.yaml`）：

- `plugin: nav2_mppi_controller::MPPIController`
- `time_steps: 48`，`model_dt: 0.05`（前向仿真 2.4s）
- `batch_size: 1000`（每次采样 1000 条轨迹）
- `vx_max: 0.7`，`wz_max: 1.0`
- `temperature: 0.3`，`gamma: 0.015`
- `motion_model: DiffDrive`
- Critics: `ConstraintCritic`, `CostCritic(4.5)`, `GoalCritic(5.0)`, `GoalAngleCritic(3.0)`, `PathAlignCritic(14.0)`, `PathFollowCritic(5.0)`, `PathAngleCritic(2.0)`, `PreferForwardCritic(5.0)`
- `controller_frequency: 20.0`
- `yaw_goal_tolerance: 6.28`（实质上禁用朝向检查）

历史 DWB 配置已不再使用，仅保留在 `nav2_gps.yaml` 和 `nav2_travel.yaml` 中。

## 4a. Corridor 模式 RPP 控制器（2026-03-22，已废弃）

> 以下参数仅供历史参考。Corridor 已于 2026-03-31 切换到 MPPI（commit `9d71823`）。

Corridor v2 使用 Rotation Shim + Regulated Pure Pursuit 替代 DWB：

- `RotationShimController.angular_dist_threshold: 0.785`（45 度）
- `RotationShimController.angular_disengage_threshold: 0.39`
- `RotationShimController.rotate_to_heading_angular_vel: 1.0`
- `RotationShimController.max_angular_accel: 1.6`
- `RotationShimController.simulate_ahead_time: 1.0`
- `RPP.desired_linear_vel: 0.5`
- `RPP.lookahead_dist: 1.0`
- `RPP.min_lookahead_dist: 0.45`
- `RPP.max_lookahead_dist: 1.5`
- `RPP.lookahead_time: 1.5`
- `RPP.max_allowed_time_to_collision_up_to_carrot: 0.30`
- `RPP.use_cost_regulated_linear_velocity_scaling: true`（2026-03-26 启用）
- `RPP.allow_reversing: false`

## 5. 代价地图相关结论（2026-04-01 更新）

### Local Costmap（当前 `nav2_explore.yaml` 实际值）

- 更新频率: `12 Hz`
- 发布频率: `6 Hz`
- `resolution: 0.05`
- `width/height: 30`（cells，实际物理范围 30 * 0.05 = 1.5m）
- STVL `voxel_decay: 0.8`
- `obstacle_range: 15.0`
- `min_obstacle_height: -0.33` / `max_obstacle_height: 0.30`
- `inflation_radius: 0.43`，`cost_scaling_factor: 2.0`
- `denoise_layer.minimal_group_size: 4`

### Global Costmap（当前 `nav2_explore.yaml` 实际值）

- 更新频率: `5 Hz`（2026-04-05 从 3Hz 提升以支持 5Hz 重规划）
- 发布频率: `2.0 Hz`
- `resolution: 0.10`
- `width/height: 50`（cells，实际物理范围 50 * 0.10 = 5.0m，2026-04-05 缩小以降低开销）
- STVL `voxel_decay: 1.5`
- `obstacle_range: 15.0`
- `min_obstacle_height: -0.33` / `max_obstacle_height: 0.30`
- `inflation_radius: 0.63`，`cost_scaling_factor: 1.0`

### 已知待改进

- costmap 画布尺寸（local 1.5m / global 8m）远小于 `obstacle_range` 15m 和 LiDAR 15m 量程
- 超出画布的障碍数据被截断；全局 NavFn 对远距离子目标（30m）实质上没有全局绕路能力
- 当前 MPPI 局部避障能力已通过室内验证，但室外大障碍物绕路能力待评估

## 6. GPS 专用配置（`nav2_gps.yaml`）

GPS 目标导航模式不直接改 `nav2_explore.yaml`，而是新建独立的 `nav2_gps.yaml`。

相对 Explore 配置的最小必要差异：

- `general_goal_checker.xy_goal_tolerance = 3.0`
- `general_goal_checker.yaw_goal_tolerance = 0.5`
- `GridBased.tolerance = 2.5`
- `BaseObstacle.scale = 0.02`
- `GoalAlign.scale = 24.0`
- `RotateToGoal.scale = 32.0`

调参原则：
- 低精度 GNSS 环境下放宽 goal tolerance
- 保持现有 DWB / costmap 主结构不动
- 不在 GPS MVP 分支中顺手引入 MPPI、VoxelLayer 等更大变更

## 7. 当前运行注意事项（2026-04）

1. RViz 的 fixed frame 必须设为 `map`。
2. 如果 `map -> odom` 没建立，即使 Livox 和 FAST-LIO2 在跑，RViz 也可能表现为空白或 costmap 不显示。
3. Explore 和 Corridor 模式已统一使用 MPPI 控制器（commit `9d71823`）。
4. `velocity_smoother.max_velocity[0]` 已同步到 `0.7`。
5. `nav2_gps.yaml` 仍使用 DWB 控制器，独立于 Explore/Corridor。
6. FAST-LIO2 发布点云已在 C++ 端按高度窗口 `[-0.33, 0.30]` 过滤（commit `f619fa6`），下游 STVL 收到的是干净数据。

## 8. 航点系统

- `waypoint_collector` 订阅 RViz 的 `/clicked_point`
- `gps_waypoint_dispatcher` 通过 `FollowWaypoints` 把 GPS 目标交给 Nav2
- `goto_name` 走路网模式
- `goto_latlon` 仅做调试直达模式

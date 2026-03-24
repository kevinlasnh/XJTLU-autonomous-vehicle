# Nav2 参数调优记录

## 1. 基本概念

- 路径（Path）: 由 planner 生成的空间几何点集合
- 轨迹（Trajectory）: 由 controller 生成的带时间和速度约束的可执行运动序列

## 2. 当前车辆运动参数

- `robot_radius`: `0.38625`
- `max_vel_x`: `0.5`
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
- 原因: 已确认闭环接入现阶段不稳定，继续使用开环是当前真实配置

## 4. Explore 主模式当前关键调参结论

DWB 控制器仍为 Explore 模式默认配置：

- `BaseObstacle.scale: 0.02`
- `GoalAlign.scale: 16.0`
- `PathAlign + GoalAlign.forward_point_distance: 0.325`
- `trans_stopped_velocity: 0.05`
- `RotateToGoal.scale: 200.0`
- 已禁用倒车: `min_vel_x = 0.0`

## 4a. Corridor 模式 RPP 控制器（2026-03-22）

Corridor v2 使用 Rotation Shim + Regulated Pure Pursuit 替代 DWB：

- `RotationShimController.angular_dist_threshold: 0.785`（45°）
- `RotationShimController.angular_disengage_threshold: 0.39`
- `RotationShimController.rotate_to_heading_angular_vel: 1.0`
- `RotationShimController.max_angular_accel: 1.6`
- `RotationShimController.simulate_ahead_time: 1.0`
- `RPP.desired_linear_vel: 0.5`
- `RPP.lookahead_dist: 1.0`
- `RPP.min_lookahead_dist: 0.45`
- `RPP.max_lookahead_dist: 1.5`
- `RPP.lookahead_time: 1.5`
- `RPP.max_allowed_time_to_collision_up_to_carrot: 0.6`
  - 注: v1 部署时曾从 0.6 误调到 1.2（方向错误：增大=检测更远=更多停车），修正 v2 已回退到 0.6
- `RPP.regulated_linear_scaling_min_radius: 0.9`
- `RPP.regulated_linear_scaling_min_speed: 0.25`
- `RPP.use_rotate_to_heading: false`
- `RPP.rotate_to_goal_heading: false`
- `RPP.allow_reversing: false`

选择 RPP 的原因: DWB 的 RotateToGoal/GoalAlign critic 在 GPS corridor 场景下导致路径折弯和卷团。RPP 的 pure pursuit 几何追踪适合走廊直线。

## 5. 代价地图相关结论（2026-03-22 更新）

### Local Costmap

- 更新频率: `10 Hz`（从 12 降低，减少 CPU）
- 发布频率: `5 Hz`
- `resolution: 0.02`（corridor 分支当前仍保持 0.02，计划中的 0.05 尚未部署）
- VoxelLayer 已在计划中但当前分支仍用 ObstacleLayer
- `obstacle_min_range: 0.2`（过滤 LiDAR 原点噪声）
- `obstacle_max_range: 5.0`
- `raytrace_max_range: 6.0`
- `min_obstacle_height: -0.3`

### Global Costmap

- 更新频率: `2 Hz`（从 3 降低）
- 发布频率: `1 Hz`
- `resolution: 0.02`（计划中的 0.10 尚未部署）
- `obstacle_max_range: 4.0`（从 10 大幅收紧）
- `obstacle_min_range: 1.0`（从 0.3 提高，减少近场标记）
- `raytrace_max_range: 5.0`（从 12 大幅收紧）
- `raytrace_min_range: 0.5`
- 使用 rolling window, width/height: 50

### 实车发现（2026-03-22~24）

- `cost_scaling_factor: 2.5`, `inflation_radius: 0.4`
- `max obstacle height: 1.5m`
- Global costmap 陈旧障碍仍是主要问题来源: 启动前人站在车前、绕过后的静态障碍未清除
- Local costmap collision ahead 判定在 controller 掉频时更容易误触发
- Controller 已 miss 20Hz，Planner 降至 ~2Hz — 继续提高刷新率会加剧掉频
- 下一步应优先修 obstacle layer 清障策略而非继续调频率
- **2026-03-23 修正 v2**: local `denoise_layer.minimal_group_size` 从 3 提到 4（抑制孤立噪声点），global STVL `transform_tolerance` 从 0.35 对齐到 0.5

## 6. GPS 专用配置（`nav2_gps.yaml`）

GPS 目标导航模式不直接改 `nav2_explore.yaml`，而是新建独立的 `nav2_gps.yaml`。

相对 Explore 配置的最小必要差异：

- `progress_checker.movement_time_allowance = 10.0`
- `general_goal_checker.xy_goal_tolerance = 3.0`
- `general_goal_checker.yaw_goal_tolerance = 0.5`
- `GridBased.tolerance = 2.5`
- `GridBased.use_astar = true`
- `BaseObstacle.scale = 0.02`
- `GoalAlign.scale = 24.0`
- `RotateToGoal.scale = 32.0`

调参原则：
- 低精度 GNSS 环境下放宽 goal tolerance
- 保持现有 DWB / costmap 主结构不动
- 不在 GPS MVP 分支中顺手引入 MPPI、VoxelLayer 等更大变更

## 7. 当前运行注意事项（2026-03）

1. RViz 的 fixed frame 必须设为 `map`。
2. 如果 `map -> odom` 没建立，即使 Livox 和 FAST-LIO2 在跑，RViz 也可能表现为空白或 costmap 不显示。
3. `nav2_default.yaml`、`nav2_explore.yaml`、`nav2_travel.yaml` 已在 2026-03-18 做过注释和格式重写，但没有改参数值。
4. `nav2_gps.yaml` 目前在 `feature/gps-navigation-v4` 上完成软件部署，室外调优还没有结束。
5. Corridor 模式（`gps` 分支）复用 `nav2_explore.yaml`，其中 controller 段已从 DWB 改为 Rotation Shim + RPP，costmap 参数也已按 corridor 需求调整。
6. 当前 Jetson 上 controller 目标从 20Hz 降为 15Hz（修正 v2），planner 降至 ~2Hz。不应继续一味拉高频率。

## 8. 航点系统

- `waypoint_collector` 订阅 RViz 的 `/clicked_point`
- `gps_waypoint_dispatcher` 通过 `FollowWaypoints` 把 GPS 目标交给 Nav2
- `goto_name` 走路网模式
- `goto_latlon` 仅做调试直达模式

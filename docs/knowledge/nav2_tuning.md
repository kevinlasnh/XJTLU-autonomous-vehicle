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
- `RPP.max_allowed_time_to_collision_up_to_carrot: 0.30`
  - 注: 原值 0.6，v1 误调到 1.2（方向错误），修正 v2 回退到 0.6，后续进一步收紧到 0.30 以更早触发减速而非急停
- `RPP.use_cost_regulated_linear_velocity_scaling: true`（2026-03-26 启用）
  - `cost_scaling_dist: 0.55`
  - `cost_scaling_gain: 0.70`
  - 效果：靠近障碍时平滑减速，替代此前的二元急停行为
- `RPP.regulated_linear_scaling_min_radius: 1.2`
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

### 实车发现（2026-03-22~26）

- **2026-03-26 最新参数（收口版本）**:
  - Local costmap: `width/height: 18`, `inflation_radius: 0.65`, `cost_scaling_factor: 2.0`
  - Global costmap: `width/height: 80`, `inflation_radius: 0.95`, `cost_scaling_factor: 1.0`
  - STVL `clear_after_reading: false`（local + global），障碍由 `voxel_decay` 自然管理
  - RPP `max_allowed_time_to_collision_up_to_carrot: 0.30`
  - RPP `use_cost_regulated_linear_velocity_scaling: true`
  - subgoal 间距 30m（global costmap 半径 40m - 10m buffer）
- 绿色 `/plan` 贴边问题已通过 global `cost_scaling_factor: 1.0`（原 2.0）+ `inflation_radius: 0.95`（原 0.75）缓解
- `clear_after_reading: false` 修复了障碍每周期清空的问题，STVL 现在按 `voxel_decay` 正常衰减
- BT override 已修复：`default_nav_to_pose_bt_xml` 从错误的 `bt_navigator_navigate_to_pose_rclcpp_node` 移到 `bt_navigator`
- corridor 运行期调参已触及天花板��当前主瓶颈不是 Nav2 参数，而是 GPS 路线锚定方法
- **2026-03-23 修正 v2**: local `denoise_layer.minimal_group_size` 从 3 提到 4，global STVL `transform_tolerance` 从 0.35 对齐到 0.5

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

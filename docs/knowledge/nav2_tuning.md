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

- `BaseObstacle.scale: 0.02`
- `GoalAlign.scale: 16.0`
- `PathAlign + GoalAlign.forward_point_distance: 0.325`
- `trans_stopped_velocity: 0.05`
- `RotateToGoal.scale: 200.0`
- 已禁用倒车: `min_vel_x = 0.0`

## 5. 代价地图相关结论

- 本地代价地图更新 / 发布频率: `30 Hz`
- `resolution: 0.02`
- `cost_scaling_factor: 2.5`
- `max obstacle height: 1.5m`
- 全局代价地图使用 rolling window

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

## 8. 航点系统

- `waypoint_collector` 订阅 RViz 的 `/clicked_point`
- `gps_waypoint_dispatcher` 通过 `FollowWaypoints` 把 GPS 目标交给 Nav2
- `goto_name` 走路网模式
- `goto_latlon` 仅做调试直达模式

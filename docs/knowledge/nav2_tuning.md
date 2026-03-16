# Nav2 参数调优记录

### 基本概念
- 路径(Path): 空间几何点集合, 由planner生成, 约束条件为静态障碍+连通性
- 轨迹(Trajectory): 空间点+时间/速度信息, 由DWB控制器生成, 约束条件为动力学+动态障碍

### 车辆运动参数
- robot_radius: 0.38625m (正面500mm, 侧边650mm, 勾股定理=336.25mm + 50mm安全余量)
- max_vel_x: 0.5 m/s
- min_vel_x: 0.0 (倒车已禁用, 原为-0.5)
- max_vel_theta: 1.0 rad/s (基于学长论文测试值)
- min_speed_theta: 0.0 (允许完全停止旋转)
- acc_lim_x: 3.0 m/s², decel_lim_x: -3.0 m/s²
- acc_lim_theta: 3.5 rad/s², decel_lim_theta: -3.5 rad/s²

### 速度平滑器 (velocity_smoother)
- max_velocity: [0.5, 0.0, 1.0]
- min_velocity: [0.0, 0.0, 0.0] (倒车禁用)
- max_accel: [3.0, 0.0, 3.5]
- max_decel: [-3.0, 0.0, -3.5]
- feedback: OPEN_LOOP (闭环控制C板里程计导致自转, FASTLIO2导致不循迹)
- odom_topic: /fastlio2/lio_odom

### DWB 控制器 critics
- BaseObstacle.scale: 0.02 (曾误设为0.002导致避障失效)
- GoalAlign.scale: 16.0 (降低, 解决与PathAlign冲突)
- PathAlign + GoalAlign: forward_point_distance = 0.325
- trans_stopped_velocity: 0.05 (防止低速转弯误判为停止)
- PreferForward: 已添加, 惩罚倒退轨迹
- RotateToGoal.scale: 200.0 (已从默认调高)

### 代价地图配置
- 本地代价地图更新/发布频率: 30 Hz
- resolution: 0.02m
- cost_scaling_factor: 2.5 (增强狭窄区域通过性)
- 障碍物最大高度: 1.5m (解决天花板误检)
- 光线追踪范围与窗口大小一致
- 使用增量式更新
- 全局代价地图: 使用滚动窗口(rolling_window=true)

### 代价地图架构讨论 (2025.12.02)
- 全局路径规划不需要全局代价地图, 只需要全局坐标系+起终点位姿
- 航点间默认直线连接, 只在滚动窗口内检测到障碍时改变路径
- 双地图架构(全局+本地)的冲突问题: 局部清除障碍但全局未刷新
- 当前结论: 仍需双地图架构, 通过controller参数配置解决冲突

### 航点系统
- waypoint_collector: 自开发中间节点, 订阅RViz /clicked_point → 累积数组 → 发送给Nav2 waypoint_follower (action通信)
- 已测试成功 (2025.11.25)

### Nav2 目标点格式
```yaml
header:
  stamp: <timestamp>
  frame_id: "map"
pose:
  position: {x: 2.5, y: -1.0, z: 0.0}
  orientation: {x: 0.0, y: 0.0, z: 0.7071, w: 0.7071}
```

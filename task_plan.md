# Corridor v2 — GPS-aligned 多点导航实施计划

**Status**: `CC 复审完成 / Bootstrap 方案 A 锁定 / 交还 Codex 部署`
**当前分支**: `gps`
**最后更新**: 2026-03-22

---

## 总体架构

```
NMEA 驱动 → /fix → PGO（ENU→map 旋转估计 + GPS 因子融合）
                         ↓
                    map frame 对齐 ENU
                         ↓
                    发布 /gps_corridor/enu_to_map 变换
                         ↓
GPS Route Runner → 读 ENU→map 变换 → GPS 路点转 map 坐标 → Nav2 (RPP)
```

**不用 gps_anchor_localizer_node**。PGO 自己估计完整的 ENU→map 变换（旋转+平移），同时做 GPS 因子融合。Runner 节点读这个变换做 GPS→map 坐标转换。简化管道，减少依赖。

---

## 实施优先级

| 阶段 | 内容 | 依赖 | 改动量 |
|------|------|------|--------|
| **Phase 1** | P2/P3/P4: Nav2 参数调优 | 无 | YAML 配置 |
| **Phase 2** | P0: PGO GPS 融合修复 | 需编译 C++ | pgo_node.cpp + simple_pgo.cpp |
| **Phase 3** | P5: 多点 GPS 路线 Runner | P0 完成 | Python 新节点 |

Phase 1 可立即部署验证，不动 C++ 代码。Phase 2 是核心改动。Phase 3 基于 Phase 2 成果。

---

## Phase 1: Nav2 参数调优

### 1.1 控制器: DWB → Rotation Shim + Regulated Pure Pursuit

**解决**: P2（路径折弯/卷团）

**文件**: `src/bringup/config/nav2_explore.yaml` — controller_server 段

```yaml
# === 替换 FollowPath 段 ===
controller_server:
  ros__parameters:
    controller_frequency: 20.0
    min_x_velocity_threshold: 0.001
    min_y_velocity_threshold: 0.5
    min_theta_velocity_threshold: 0.001
    failure_tolerance: 0.3
    progress_checker_plugin: "progress_checker"
    goal_checker_plugins: ["general_goal_checker"]
    controller_plugins: ["FollowPath"]

    progress_checker:
      plugin: "nav2_controller::SimpleProgressChecker"
      required_movement_radius: 0.3       # 0.5→0.3: 降低移动要求
      movement_time_allowance: 10.0       # 3.0→10.0: 容忍短暂停顿

    general_goal_checker:
      stateful: true
      plugin: "nav2_controller::SimpleGoalChecker"
      xy_goal_tolerance: 0.35             # 0.25→0.35: 中间航点放宽
      yaw_goal_tolerance: 6.28            # 0.25→6.28(2π): 不检查朝向

    FollowPath:
      plugin: "nav2_rotation_shim_controller::RotationShimController"
      angular_dist_threshold: 0.785       # 45°: 仅大角度变化时旋转
      angular_disengage_threshold: 0.39  # 审计修复: 脱离旋转阈值 = 阈值的一半，防止抖振
      forward_sampling_distance: 0.5
      rotate_to_heading_angular_vel: 1.0
      max_angular_accel: 1.6
      simulate_ahead_time: 1.0
      rotate_to_goal_heading: false       # 不在目标处旋转

      primary_controller: "nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController"
      desired_linear_vel: 0.5
      lookahead_dist: 1.0
      min_lookahead_dist: 0.4
      max_lookahead_dist: 1.5
      lookahead_time: 1.5
      use_velocity_scaled_lookahead_dist: true
      transform_tolerance: 0.1
      min_approach_linear_velocity: 0.05
      approach_velocity_scaling_dist: 0.6
      use_collision_detection: true
      max_allowed_time_to_collision_up_to_carrot: 1.0
      use_regulated_linear_velocity_scaling: true
      use_cost_regulated_linear_velocity_scaling: false
      regulated_linear_scaling_min_radius: 0.9
      regulated_linear_scaling_min_speed: 0.25
      use_rotate_to_heading: false        # 不在子目标旋转
      allow_reversing: false
      max_robot_pose_search_dist: 10.0
```

**关键变更理由**:
- `RotateToGoal` critic 被完全移除（RPP 没有这个概念）
- `use_rotate_to_heading: false` + `rotate_to_goal_heading: false` 消除所有旋转停顿
- `yaw_goal_tolerance: 6.28` = 2π = 任意朝向都接受
- `lookahead_dist: 1.0` 适合走廊直线

### 1.2 Local Costmap 优化

**解决**: P3（幻影障碍停车）+ P4（过重）

**关键坐标参考**（基于 docs/hardware_spec.md 实测数据）:
- LiDAR 离地: 0.447m
- t_il.z: 0.044m → base_link (IMU) 离地: 0.403m
- body_cloud 中地面 z ≈ -0.40m, 10cm 马路牙 z ≈ -0.30m, 50cm 矮墙 z ≈ +0.10m

```yaml
local_costmap:
  local_costmap:
    ros__parameters:
      update_frequency: 5.0               # 40→5: 降低 CPU 负载
      publish_frequency: 2.0              # 40→2: 降低带宽
      global_frame: odom
      robot_base_frame: base_link
      use_sim_time: false
      rolling_window: true
      width: 5                            # 15→5: 缩小到 5m
      height: 5                           # 15→5
      resolution: 0.05                    # 0.02→0.05: 5cm 分辨率
      robot_radius: 0.38625
      plugins: ["voxel_layer", "inflation_layer"]
      # 注: DenoiseLayer 如需要再加，先验证 VoxelLayer 效果

      voxel_layer:
        plugin: "nav2_costmap_2d::VoxelLayer"
        enabled: true
        footprint_clearing_enabled: true
        origin_z: -0.45                  # 地面(-0.40)以下，确保低矮障碍在网格内
        z_resolution: 0.15              # 15cm/层，马路牙占1层，减少计算量
        z_voxels: 16                    # 16×0.15=2.4m → z=-0.45~+1.95m
        unknown_threshold: 15
        mark_threshold: 0
        publish_voxel_map: false
        observation_sources: pointcloud
        combination_method: 1
        pointcloud:
          topic: /fastlio2/body_cloud
          data_type: "PointCloud2"
          min_obstacle_height: -0.30     # 地面(-0.40)滤掉, 10cm马路牙(-0.30)保留
          max_obstacle_height: 1.5
          obstacle_min_range: 0.3        # 新增: 过滤 LiDAR 原点噪声
          obstacle_max_range: 4.0        # 15→4: 局部只关心近距离
          raytrace_min_range: 0.3
          raytrace_max_range: 5.0
          clearing: true
          marking: true

      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        cost_scaling_factor: 3.0          # 2.5→3.0
        inflation_radius: 0.55            # 0.4→0.55
      always_send_full_costmap: false
```

**幻影障碍防线**（min_obstacle_height 回到 -0.30 后靠以下三层解决）:
1. 分辨率 0.02→0.05: 单个噪声点影响更小
2. obstacle_min_range=0.3: 过滤 Livox MID360 原点自检测噪声
3. VoxelLayer 3D raytrace: 地面点在最底层体素，不会被误投为障碍柱
4. 兜底: 如仍有残留，追加 DenoiseLayer 移除孤立单格障碍

### 1.3 Global Costmap 优化

**解决**: P4（过重）

**审计修复**: global costmap 用 2D ObstacleLayer。当车靠近马路牙（<2.8m）时，LiDAR
光束从马路牙上方飞过，2D raytrace 会错误清掉已标记的马路牙。修复方案：关闭 clearing，
只标不清，靠 inflation 衰减和 costmap rolling 自然淘汰旧障碍。

```yaml
global_costmap:
  global_costmap:
    ros__parameters:
      update_frequency: 1.0               # 5→1
      publish_frequency: 0.5              # 5→0.5
      global_frame: map
      robot_base_frame: base_link
      use_sim_time: false
      robot_radius: 0.38625
      resolution: 0.10                    # 0.02→0.10: 10cm
      track_unknown_space: true
      rolling_window: true
      width: 30                           # 50→30
      height: 30                          # 50→30
      plugins: ["obstacle_layer", "inflation_layer"]

      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        enabled: true
        footprint_clearing_enabled: true
        observation_sources: pointcloud
        pointcloud:
          topic: /fastlio2/body_cloud
          data_type: "PointCloud2"
          min_obstacle_height: -0.30      # 与 local 一致, 保留马路牙
          max_obstacle_height: 1.5
          obstacle_min_range: 0.3
          obstacle_max_range: 10.0
          raytrace_max_range: 12.0
          clearing: false                 # 审计修复: 关闭清障，防止近距离误清马路牙
          marking: true

      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        cost_scaling_factor: 3.0
        inflation_radius: 0.55
      always_send_full_costmap: false
```

### Phase 1 性能改善预估

| 指标 | 修改前 | 修改后 |
|------|--------|--------|
| 局部 costmap cells | 562,500 | 10,000 (**56x↓**) |
| 全局 costmap cells | 6,250,000 | 90,000 (**70x↓**) |
| 路径折弯/卷团 | 严重 | 消除（RPP 无 RotateToGoal）|
| 幻影障碍停车 | 频繁 | 大幅减少（VoxelLayer 3D + 分辨率 0.05 + obstacle_min_range=0.3）|

### 1.4 全量日志记录

**解决**: 每次运行自动产生完整日志，用于复盘、调参和论文数据

**输出目录**: 沿用现有 `scripts/launch_with_logs.sh` session 目录规范

```
~/fyp_runtime_data/logs/<session>/
├── console/                # ROS 2 / launch console 日志（ROS_LOG_DIR）
├── data/                   # 节点自定义日志（FYP_LOG_SESSION_DIR）
├── system/                 # tegrastats + session_info.yaml
└── bag/                    # ros2 bag 录制（本次 corridor 运行数据）
```

`~/fyp_runtime_data/logs/latest` 继续指向最近一次 session，不另起一套平行日志体系。

**录制 topic 列表**:

| Topic | 说明 | 大小估计 |
|-------|------|---------|
| `/fix` | GPS 原始数据 | 极小 |
| `/fastlio2/lio_odom` | SLAM 里程计 | 小 |
| `/tf` | 坐标变换（含 map→odom→base_link） | 小 |
| `/tf_static` | 静态 TF | 极小 |
| `/gps_corridor/status` | runner 状态机 | 极小 |
| `/gps_corridor/goal_map` | 当前目标点 | 极小 |
| `/gps_corridor/path_map` | 规划的 corridor 路径 | 极小 |
| `/cmd_vel` | 发给底盘的速度指令 | 小 |
| `/local_costmap/costmap` | 局部代价地图 | 中 |
| `/plan` | Nav2 全局路径 | 小 |

**不录制**（体积过大，NVMe 空间有限）:
- `/livox/lidar` — 原始点云 ~40MB/s
- `/fastlio2/body_cloud` — 处理后点云 ~10MB/s

**launch 文件修改**: `system_gps_corridor.launch.py` 中新增 bag record，但日志目录不在 launch 内重新造时间戳，而是挂到当前 session：

```python
session_data_dir = os.environ.get('FYP_LOG_SESSION_DIR', '')
session_root = os.path.dirname(session_data_dir) if session_data_dir else \
    os.path.expanduser(f'~/fyp_runtime_data/logs/{datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}')
bag_dir = os.path.join(session_root, 'bag')
os.makedirs(bag_dir, exist_ok=True)

# ros2 bag record
bag_record = ExecuteProcess(
    cmd=[
        'ros2', 'bag', 'record',
        '--output', bag_dir,
        '/fix',
        '/fastlio2/lio_odom',
        '/tf', '/tf_static',
        '/gps_corridor/status',
        '/gps_corridor/goal_map',
        '/gps_corridor/path_map',
        '/cmd_vel',
        '/local_costmap/costmap',
        '/plan',
    ],
    output='log',
)
```

需要在文件头部增加 `from launch.actions import ExecuteProcess`，
并在 `LaunchDescription` 的 actions 列表末尾加入 `bag_record`。
如通过 wrapper 启动，`launch.log` / console log 仍由 `ROS_LOG_DIR` 接管，不额外手写一份 stdout 重定向逻辑。

### Phase 1 构建 & 部署

```bash
# 只需要重建工作区内被改到的启动包:
colcon build --packages-select bringup --symlink-install --parallel-workers 1
source install/setup.bash
```

说明：`nav2_costmap_2d` / `nav2_regulated_pure_pursuit_controller` / `nav2_rotation_shim_controller`
是系统侧 Nav2 运行时依赖，不是本仓库内的 colcon 包，不作为 `--packages-select` 目标。

---

## Phase 2: PGO GPS 融合修复

### 2.1 概述

修改 PGO C++ 代码，解决三个子问题：
1. ENU→map 旋转估计
2. GPS topic 修正
3. 权重平衡（渐进引入）

### 2.2 文件修改清单

| 文件 | 修改内容 |
|------|---------|
| `src/perception/pgo_gps_fusion/src/pgo_node.cpp` | GPS topic 修正 + 旋转估计逻辑 + ENU→map 变换发布 |
| `src/perception/pgo_gps_fusion/src/pgos/simple_pgo.cpp` | 放松首帧先验 + GPS 渐进引入（支持 warmup sigma override） |
| `src/perception/pgo_gps_fusion/src/pgos/simple_pgo.h` | 新增旋转估计状态 / GPS warmup 状态相关成员变量 |
| `src/bringup/config/master_params.yaml` | `gps.topic: /fix` + 新增旋转估计参数 |

### 2.3 旋转估计算法

**在 `pgo_node.cpp` 的 `tryAddGPSFactor()` 中，第 787 行（ENU 转换完成后）插入：**

```
算法: 2D 最小二乘旋转估计

输入: 累积的 (enu_xy, map_xy) 配对列表
输出: 旋转角 θ 和平移 t

步骤:
1. 每次 tryAddGPSFactor 被调用时:
   - enu_xy = Forward(lat, lon) 的 (x, y)
   - map_xy = m_pgo->keyPoses()[current_idx].t_global 的 (x, y)
   - 加入配对列表

2. 检查条件:
   - 配对数 ≥ gps.alignment_min_points (默认 5)
   - 最大空间展幅 ≥ gps.alignment_min_spread_m (默认 5.0m)
   - 如不满足，跳过 GPS factor（不添加）

3. 满足条件时，计算旋转:
   - enu_centroid = mean(enu_xy_i)
   - map_centroid = mean(map_xy_i)
   - e_i' = enu_xy_i - enu_centroid
   - m_i' = map_xy_i - map_centroid
   - H = Σ e_i' * m_i'^T  (2x2 矩阵)
   - θ = atan2(H[1][0] - H[0][1], H[0][0] + H[1][1])
   - R = [[cos θ, -sin θ], [sin θ, cos θ]]
   - t = map_centroid - R * enu_centroid

4. 变换 GPS 坐标:
   - map_gps_xy = R * enu_xy + t
   - 传入 addGPSFactor() 的位置使用 map_gps_xy

5. 持续更新:
   - 每次新配对加入后重新计算 θ
   - 随着数据积累，估计精度提升
   - 审计修复: smoothAndUpdate() 之后，刷新所有配对的 map_xy
     （防止回环校正后旧 map_xy 值过时导致旋转估计偏差）

6. 发布变换:
   - 在 ROS2 topic /gps_corridor/enu_to_map 上发布 θ 和 t
   - Runner 节点订阅此 topic 做 GPS 路点转换
```

**精度估计**（GPS sigma=2.5m, 均值化后约 0.8m）:

| 行驶距离 | 配对数(~) | 角度估计误差 |
|---------|---------|------------|
| 5m | 5 | ~10-15° |
| 10m | 10 | ~5-8° |
| 20m | 20 | ~2-4° |
| 50m | 50 | ~1-2° |

### 2.4 权重平衡策略

**首帧先验放松**:
```cpp
// simple_pgo.cpp addKeyPose(), 第 49 行
// 修改前: gtsam::Vector6::Ones() * 1e-12
// 修改后:
(gtsam::Vector(6) << 1e-6, 1e-6, 1e-6, 1e-2, 1e-2, 1e-4).finished()
// 旋转保持紧 (1e-6), 平移放松到 1e-2 (sigma=0.1m), z 保持较紧 (1e-4)
```

**GPS 渐进引入**:
```
旋转估计完成后的前 5 个 GPS factor:  sigma_xy = 10.0m  (软引入)
之后的 GPS factor:                    sigma_xy = 2.5m   (正常)
```

实现约束补充：
- `simple_pgo.cpp` 需要显式支持 warmup sigma override；当前 `addGPSFactor()` 会优先使用 `NavSatFix.position_covariance`，并把 sigma clamp 到 `<= 5.0m`，不能直接实现 `10.0m` 热身。
- 因此热身期不能只改 `master_params.yaml`，必须同步改 `simple_pgo.h/.cpp` 的 GPS factor 构造逻辑。

### 2.5 配置变更

```yaml
# master_params.yaml
/pgo:
  pgo_node:
    ros__parameters:
      "gps.topic": /fix                       # /gnss → /fix
      "gps.alignment_min_points": 5           # 新增
      "gps.alignment_min_spread_m": 5.0       # 新增
      "gps.alignment_warmup_factors": 5       # 新增: 前 5 个用大噪声
      "gps.alignment_warmup_sigma": 10.0      # 新增: 热身期 sigma
      "gps.factor_interval": 5                # 10 → 5: 关键帧间隔缩小
```

### 2.6 ENU→map 变换发布

PGO 在 `timerCB` 中（已有广播 map→odom TF 的逻辑）增加：
- 发布 `std_msgs/Float64MultiArray` 到 `/gps_corridor/enu_to_map`
- payload 固定为 `[theta, tx, ty, is_valid]`
- 选择该消息的原因：Runner 只需要 2D 旋转/平移和有效位，避免为 topic 传输再套一层 TF 语义

### 2.7 启动 Bootstrap（CC 复审结论）

**问题**: 车静止启动时，PGO 无法积累空间展幅 → enu_to_map 永远不 valid → runner 不起步。

**CC 裁决: 采用方案 A（固定 yaw bootstrap），淘汰 10m 预热方案。**

**技术依据**（基于 FAST-LIO2 源码调研 `imu_processor.cpp:16-49`）:
- `gravity_align: true` 时，FAST-LIO2 用 `FromTwoVectors(-acc_mean, (0,0,-1))` 做最短弧旋转
- 该函数是确定性的：相同物理放置 → 相同 yaw0
- yaw0 启动间变化 < 0.1°（BMI088 加速度计噪声级别）
- 因此 ENU→map 旋转可在上电瞬间计算，无需等待车辆移动

**Bootstrap 算法**:

```
1. 上电 → FAST-LIO 初始化 → 读 map→base_link TF
2. 提取 yaw0 = atan2(R[1,0], R[0,0])
3. 读 route YAML 的 launch_yaw_deg（车的地理朝向，ENU 约定）
4. θ_bootstrap = yaw0 - radians(launch_yaw_deg)
5. 构造初始 ENU→map: R_bootstrap = Rz(θ_bootstrap), t_bootstrap 从 start_ref ENU + map origin 推导
6. 立即开始导航（不等 PGO valid）
```

**launch_yaw_deg 来源**:
- 对于直线 corridor: 直接复用现有 YAML 的 `bearing_deg`（起终点 GPS 方位角）
- 对于多点路线: 起点到第一个路点的方位角，或用手机指南针测量
- 只需测量一次，写入 route YAML

**Bootstrap → PGO 切换**:

```
前 20m: 使用 bootstrap 旋转（精度 ±5°，取决于 launch_yaw_deg 测量精度）
20m+:   PGO 发布 is_valid=true → runner 平滑切换到 PGO 精确旋转
        重算后续未访问路点的 map 坐标
```

切换时如果角度差 > 10°，log WARNING（可能放车朝向不对）。

**淘汰 10m 预热的理由**:
- 浪费 10m 距离 + 20s 时间
- 预热期间无 ENU→map → 无法用 GPS 路点导航，只能 body_vector 盲走
- 预热方向如有障碍物，无法用 GPS 路点规避
- 预热后仍需 bootstrap 到 PGO 的切换逻辑（复杂度不减反增）
- 数学上不需要：yaw0 在上电时已经确定

### Phase 2 构建

```bash
colcon build --packages-select pgo --symlink-install --parallel-workers 1
source install/setup.bash
```

---

## Phase 3: 多点 GPS 路线 Runner

### 3.1 新增/修改文件

| 文件 | 修改内容 |
|------|---------|
| `src/navigation/gps_waypoint_dispatcher/gps_waypoint_dispatcher/gps_route_runner_node.py` | 新的多点路线执行节点 |
| `src/navigation/gps_waypoint_dispatcher/setup.py` | 注册 `gps_route_runner_node` console script |
| `src/bringup/config/master_params.yaml` | 为 route runner 增加独立参数命名空间（ENU 原点等），避免复用旧 `gps_waypoint_dispatcher` 节点名造成参数未注入 |
| `src/bringup/launch/system_gps_corridor.launch.py` | 启动新 runner，参数从 `corridor_file` 切到 `route_file`，并接入 bag record |
| `scripts/launch_with_logs.sh` + `Makefile` | 新增 corridor 模式启动入口，保持 Step 25 继续走统一 session logging 启动点 |

### 3.2 路线 YAML Schema

```yaml
route_name: "campus_loop"
created_at: "2026-03-25"
coordinate_source: /fix
enu_origin:
  lat: 31.274927
  lon: 120.737548
  alt: 0.0
start_ref:
  lat: 31.274xxx
  lon: 120.737xxx
launch_yaw_deg: 123.4
waypoints:
  - name: "wp1"
    lat: 31.274xxx
    lon: 120.737xxx
  - name: "wp2"
    lat: 31.274xxx
    lon: 120.738xxx
  - name: "goal"
    lat: 31.275xxx
    lon: 120.738xxx
startup_fix_sample_count: 10
startup_fix_spread_max_m: 2.0
startup_gps_tolerance_m: 6.0
segment_length_m: 8.0
```

部署约束补充：
- `enu_origin` 必须与运行时 `master_params.yaml` 中 PGO/runner 使用的固定原点一致。
- runner 启动后先校验 route YAML 的 `enu_origin` 与运行时参数；不一致则直接 abort，避免 silently 用错坐标系。
- `launch_yaw_deg` 必须填写。对直线 corridor 可直接复用 `bearing_deg`。
- `collect_gps_route.py` 不能在“起点到第一个路点基线很短”的情况下静默自动生成 `launch_yaw_deg`；应显式提示用户确认，必要时要求手工输入（如手机指南针测量值）。
- runner 启动时从 TF 读 yaw0，与 `launch_yaw_deg` 一起计算 bootstrap ENU→map 旋转。

### 3.3 Runner 控制流

**CC 复审后锁定版本（方案 A: 固定 yaw bootstrap）**

```
1. 读取运行时参数中的固定 ENU 原点（独立 route runner 参数命名空间）
2. 加载路线 YAML，并校验 enu_origin 与运行时固定原点一致
3. 等待 stable /fix（10 次采样，spread < 2m）
4. 校验启动位置（距 start_ref < 6m）
5. 等待 Nav2 + map→base_link TF
6. Bootstrap: 从 TF 读 yaw0，用 launch_yaw_deg 计算初始 ENU→map 旋转
7. 用 bootstrap ENU→map 转换第一个路点 → 立即开始导航
8. 后台监听 PGO /gps_corridor/enu_to_map:
   - is_valid=true 时，切换到 PGO 精确旋转
   - 重算后续未访问路点的 map 坐标
9. 对每个 waypoint:
   a. GPS lat/lon → ENU（pyproj，与 PGO 同 ENU 原点）
   b. ENU → map（乘当前最佳旋转: bootstrap 或 PGO）
   c. 按 segment_length_m 在当前位置和下一个 waypoint 之间插航点
   d. 串行 NavigateToPose
10. 到达最终 goal → SUCCEEDED
```

### 3.4 与 corridor v1 的差异

| | Corridor v1 | GPS Route v2 |
|--|-------------|-------------|
| 路点数 | 2（起终点） | N 个 |
| 目标计算 | body_vector + yaw0 | GPS→ENU→map（PGO 旋转） |
| GPS 依赖 | 仅启动校验 | 启动 + PGO 旋转估计 |
| 路线形状 | 直线 | 任意折线 |
| PGO GPS 融合 | 不需要 | 需要（提供旋转 + 漂移校正）|

### 3.5 采点脚本

新增 `scripts/collect_gps_route.py`:
- 交互式多点采集
- 每点采 10 个 GPS 样本
- 保存为路线 YAML

### Phase 3 构建

```bash
colcon build --packages-select gps_waypoint_dispatcher bringup --symlink-install --parallel-workers 1
source install/setup.bash
```

---

## 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| RPP 控制器行为不符预期 | 低 | 中 | 保留 DWB 配置为 nav2_explore_dwb.yaml 备用 |
| PGO 旋转估计在 GPS 噪声下不收敛 | 中 | 高 | 要求最小展幅 5m + 至少 5 点；渐进引入 GPS |
| PGO C++ 修改引入 segfault | 低 | 高 | 增量修改，每步编译测试；保留旧 pgo_original 包 |
| min_obstacle_height=-0.30 地面噪声残留 | 低 | 中 | VoxelLayer 3D + 分辨率 0.05 + obstacle_min_range=0.3；兜底追加 DenoiseLayer |
| LiDAR 安装高度影响低矮障碍检测 | 中 | 低 | VoxelLayer 保留已见障碍；仅转弯盲区有风险 |

---

## 回退策略

- Phase 1 失败 → 恢复原 nav2_explore.yaml
- Phase 2 失败 → PGO 回退到纯 SLAM（gps.enable: false），corridor v1 仍可用
- Phase 3 失败 → 保持 corridor v1（两点直线仍可工作）

---

## 待用户确认项

1. **Phase 2 改 C++ 的接受度**：PGO 是核心感知节点，改动需要谨慎
2. **是否先跑 Phase 1 验证**：Phase 1 只改 YAML，可立即部署测试
3. **多点路线的实际需求**：Phase 3 的路线形状/长度/拐弯数量
4. **min_obstacle_height=-0.30 的地面噪声容忍度**：如果不平路面仍有幻影障碍，可调至 -0.25（牺牲 5cm 马路牙检测能力）

---

## 已废弃方案

| 方案 | 废弃原因 |
|------|----------|
| P0 路径 A（极简 yaw 校准，不改 PGO） | 用户选择路径 B |
| v7 scene graph + route_server | 对需求过重 |
| v6 整条 route 动态重算 | frame 混用风险 |
| 旧 gnss_global_path_planner A* | 依赖旧路网 |

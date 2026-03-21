# 系统架构

## 1. 运行位置

- Jetson 代码仓: `~/fyp_autonomous_vehicle`
- 运行时数据根目录: `~/fyp_runtime_data`
- GitHub 远端: `kevinlasnh/fyp_autonomous_vehicle`
- AI 协作控制面: 位于独立 PC 仓库，不在本代码仓内

## 2. 硬件平台

- Jetson Orin NX, 16 GB RAM, Ubuntu 22.04, ROS 2 Humble
- Livox MID360 LiDAR
- WIT IMU
- 基础 GNSS 模块，当前按约 2.5 m 级精度使用，不是 RTK 工作流
- 串口连接到 STM32 下位机
- PS2 手柄作为最高优先级人工接管

## 3. 五种运行模式

| 模式 | 命令 | 当前用途 |
|------|------|----------|
| SLAM | `make launch-slam` | 建图与感知链验证 |
| Explore | `make launch-explore` | 当前主运行模式，局部避障导航 |
| Explore GPS | `make launch-explore-gps` | Explore 基础上加入 GNSS 与 PGO GPS 因子 |
| Nav GPS | `make launch-nav-gps` | scene bundle + anchor ready + GPS 路网导航模式 |
| Travel | `make launch-travel` | 静态地图导航框架，当前暂停 |

所有 `make launch-*` 入口都通过 `scripts/launch_with_logs.sh` 启动，因此默认会生成按 session 隔离的日志目录。

## 4. Explore 模式数据流

```text
Livox MID360 -> /livox/lidar ------+
                                   |
Livox IMU   -> /livox/imu -------->+-> FAST-LIO2 -> /fastlio2/body_cloud
                                   |              -> /fastlio2/lio_odom
                                   |
                                   +-> PGO -> TF: map -> odom
                                           -> /pgo/optimized_odom
                                           -> /pgo/loop_markers

PGO / registered cloud -> pointcloud_to_laserscan / pointcloud_to_grid -> Nav2 costmaps
Nav2 -> /cmd_vel -> serial_twistctl -> STM32 -> motors
STM32 -> serial_reader -> chassis feedback / odom_CBoard
```

## 5. GPS 相关链路

### 5.1 Explore GPS 模式

```text
GNSS serial -> nmea_navsat_driver -> /fix
                                   |
                                   v
                          gnss_calibration -> /gnss
                                              |
                                              v
                                   PGO GPS Factor constraints
```

`make launch-explore-gps` 的职责仍然是把校准后的 `/gnss` 注入 PGO，提升 `map -> odom` 的全局位置约束能力。

### 5.2 Nav GPS 模式（scene bundle + route graph）

```text
scene_gps_bundle.yaml -> build_scene_runtime.py
                       -> current_scene/master_params_scene.yaml
                       -> current_scene/scene_points.yaml
                       -> current_scene/scene_route_graph.geojson

GNSS serial -> /fix -> gps_anchor_localizer -> /gnss -----------+
                       |                    |                   |
                       |                    +-> /gps_system/*   +-> PGO GPS Factor
                       |
                       +-> lock startup anchor + session offset

scene_points.yaml + route_graph.geojson ------------------------+
                                                               |
goto_name -> gps_waypoint_dispatcher(goal manager) ------------+
            |  读取 scene_points.yaml
            |  检查 NAV_READY
            |  锁定 startup anchor
            |  Stage A: navigate_to_pose (需要时)
            |  Stage B: ComputeRoute(start_id, goal_id)
            v
     dense graph path -> FollowPath -> Nav2 -> /cmd_vel
```

`nav-gps` 的核心是：
- 当前位姿统一使用 `gps_anchor_localizer` 发布的 `/gnss`
- PGO、localizer、goal manager 读取同一 fixed ENU origin
- `scene_gps_bundle.yaml` 是唯一 source of truth
- 运行时只读取 `~/fyp_runtime_data/gnss/current_scene/` 下的编译产物
- `goto_name` 是主入口；用户只输入英文目标名

## 6. TF 链

```text
map -> odom -> base_link
```

- `map -> odom` 由 PGO 发布，表示全局校正偏移
- `odom -> base_link` 由 FAST-LIO2 发布，表示高频局部里程计
- 两者组合后得到全局位姿

如果 `map -> odom` 不存在，RViz 在 `map` fixed frame 下会表现为点云或 costmap 看起来空白，即使 Livox 和 FAST-LIO2 本身还在运行。

## 7. 配置架构

- `src/bringup/config/master_params.yaml`
  - 仓库模板参数入口
- `src/bringup/config/nav2_default.yaml`
- `src/bringup/config/nav2_explore.yaml`
- `src/bringup/config/nav2_gps.yaml`
- `src/bringup/config/nav2_travel.yaml`
- `~/fyp_runtime_data/gnss/scene_gps_bundle.yaml`
- `~/fyp_runtime_data/gnss/current_scene/master_params_scene.yaml`
- `~/fyp_runtime_data/gnss/current_scene/scene_points.yaml`
- `~/fyp_runtime_data/gnss/current_scene/scene_route_graph.geojson`
- `src/sensor_drivers/gnss/gnss_calibration/config/calibration_points.yaml`
- `src/perception/pgo_gps_fusion/config/pgo.yaml`
- `src/perception/pgo_gps_fusion/config/pgo_no_gps.yaml`

## 8. 日志与运行时数据

`~/fyp_runtime_data/` 与代码仓解耦，当前主要包含：

```text
~/fyp_runtime_data/
├── config/
│   └── log_switch.yaml
├── gnss/
│   ├── scene_gps_bundle.yaml
│   ├── scene_gps_bundle_*.yaml
│   └── current_scene/
│       ├── master_params_scene.yaml
│       ├── scene_points.yaml
│       ├── scene_route_graph.geojson
│       └── scene_gps_bundle.yaml
├── logs/
│   ├── <timestamp>/
│   │   ├── console/
│   │   ├── data/
│   │   └── system/
│   └── latest -> <timestamp>
├── maps/
├── perf/
└── planning/
    └── angle_offset.txt
```

- `console/`: ROS 2 stdout/stderr
- `data/`: 各节点自定义数据日志
- `system/`: `tegrastats.log` 与 `session_info.yaml`

## 9. 源码层级

```text
src/
├── sensor_drivers/
├── perception/
├── planning/
├── navigation/
├── bringup/
└── third_party/
```

说明：
- `sensor_drivers/`: Livox、IMU、GNSS、串口
- `perception/`: FAST-LIO2、PGO GPS 融合、点云转栅格相关
- `planning/`: 历史 GPS 全局规划与坐标转换试验区
- `navigation/`: `waypoint_collector` 与 scene-graph goal manager `gps_waypoint_dispatcher`
- `bringup/`: 系统 launch、参数、地图、RViz 配置
- `third_party/`: 上游依赖，不作为项目自定义开发区

## 10. 包构建类型

- `ament_cmake`
  - `livox_ros_driver2`
  - `serial`
  - `serial_reader`
  - `serial_twistctl`
  - `fastlio2`
  - `pointcloud_to_grid`
  - `pointcloud_to_laserscan`
  - `pgo`
  - `pgo_original`
  - `hba`
  - `localizer`
  - `interface`
- `ament_python`
  - `global2local_tf`
  - `gnss_global_path_planner`
  - `waypoint_collector`
  - `gps_waypoint_dispatcher`
  - `wit_ros2_imu`
  - `gnss_calibration`
  - `gyro_odometry`

## 11. 关键依赖

- PCL
- OpenCV
- Eigen3
- yaml-cpp
- NLopt
- Livox SDK2
- GTSAM
- GeographicLib
- pyproj
- `ros-humble-geographic-msgs`


## 5.3 Fixed-Launch GPS Corridor 模式

```text
two_point_corridor.yaml
  -> start_ref / goal_ref / body_vector_m / thresholds

/fix ----------------------------------------------+
                                                    |
map -> base_link (FAST-LIO2 + PGO) ----------------+-> gps_corridor_runner
                                                    |    1. 等稳定 /fix
                                                    |    2. 检查当前启动点是否靠近 start_ref
                                                    |    3. 读取当前 map 启动位姿
                                                    |    4. 用 body_vector_m 生成 goal_map
                                                    |    5. 沿直线切出多个 subgoals
                                                    |    6. 串行调用 NavigateToPose
                                                    v
                                             Nav2 Explore stack
                                             -> planner/controller/costmaps
                                             -> /cmd_vel
```

该模式与 `nav-gps` 的区别：
- 不使用 scene graph
- 不使用 `route_server`
- 不使用 `gps_waypoint_dispatcher` 的 `goto_name` / menu 交互
- 不使用 runtime `current_scene/` 编译产物

该模式的定位假设：
- 车辆从固定物理 Launch Pose 启动
- 车辆启动朝向物理固定
- corridor 第一版仅覆盖“从固定启动位到固定终点”的单条直线走廊

该模式的数据面：
- `~/fyp_runtime_data/gnss/two_point_corridor.yaml`
- `start_ref` / `goal_ref` 用于记录现场参考 GPS
- `body_vector_m` 才是运行时直接投到 `map` 的几何源数据


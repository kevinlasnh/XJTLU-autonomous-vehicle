# 系统架构

## 1. 运行位置

- Jetson 代码仓: `~/XJTLU-autonomous-vehicle`
- 运行时数据根目录: `~/fyp_runtime_data`
- GitHub 远端: `kevinlasnh/XJTLU-autonomous-vehicle`
- AI 协作控制面: 位于独立 PC 仓库，不在本代码仓内

## 2. 硬件平台

- Jetson Orin NX, 16 GB RAM, Ubuntu 22.04, ROS 2 Humble
- Livox MID360 LiDAR
- WIT IMU
- 基础 GNSS 模块，当前按约 2.5 m 级精度使用，不是 RTK 工作流
- 串口连接到 STM32 下位机
- PS2 手柄作为最高优先级人工接管

## 3. 四种运行模式

| 模式 | 命令 | 当前用途 |
|------|------|----------|
| SLAM | `make launch-slam` | 建图与感知链验证 |
| Explore | `make launch-explore` | 当前主运行模式，局部避障导航 |
| Explore GPS | `make launch-explore-gps` | 在 Explore 基础上加入 GNSS 与 PGO GPS 因子 |
| Travel | `make launch-travel` | 静态地图导航框架，当前暂停 |

四个 `make launch-*` 入口都通过 `scripts/launch_with_logs.sh` 启动，因此默认会生成按 session 隔离的日志目录。

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

## 5. Explore GPS 模式额外链路

```text
GNSS serial -> nmea_navsat_driver -> /fix
                                   |
                                   v
                          gnss_calibration -> /gnss
                                              |
                                              v
                                   PGO GPS Factor constraints
```

当前生产化的 GPS 融合是把 `/gnss` 注入 PGO，提升 `map -> odom` 的全局位置约束能力。长距离 GPS 航点到 Nav2 目标点的完整自动执行链仍在开发中。

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
  当前 FAST-LIO2、PGO、串口、GNSS、pointcloud_to_laserscan 的统一参数入口
- `src/bringup/config/nav2_default.yaml`
- `src/bringup/config/nav2_explore.yaml`
- `src/bringup/config/nav2_travel.yaml`
- `src/perception/pgo_gps_fusion/config/pgo.yaml`
- `src/perception/pgo_gps_fusion/config/pgo_no_gps.yaml`
  作为 legacy 平铺 YAML 兼容入口，便于旧命令和 A/B 测试

## 8. 日志与运行时数据

`~/fyp_runtime_data/` 与代码仓解耦，当前主要包含：

```text
~/fyp_runtime_data/
├── config/
│   └── log_switch.yaml
├── gnss/
│   ├── startid.txt
│   └── gnss_offset.txt / gnss_offset.invalid_*.txt
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
- `planning/`: GPS 全局规划与坐标转换
- `navigation/`: waypoint_collector 等导航辅助节点
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

# 系统架构

### 硬件平台
- Jetson Orin NX, 16GB RAM, 116GB NVMe
- Linux 5.15.148-tegra (aarch64), Ubuntu 22.04, ROS2 Humble

### 传感器
- Livox MID360 LiDAR (3D point cloud, ~10Hz)
- WIT IMU (orientation + angular velocity, ~200Hz)
- GNSS/RTK module (GPS positioning)
- Serial connection to lower C-board (motor control + wheel odometry)
- PS2 wireless controller (manual override, highest priority)

### 三种运行模式
1. **SLAM 模式** (make launch-slam): FASTLIO2 + PGO + SLAM Toolbox → 建图
2. **Explore 模式** (make launch-explore): FASTLIO2 + PGO + Nav2 → 实时避障导航 (当前主要模式)
3. **Travel 模式** (make launch-travel): 静态地图导航 (开发暂停)

### 数据流 (Explore 模式)
```
Livox MID360 → /livox/lidar → FASTLIO2 (LiDAR-Inertial odometry)
WIT IMU → /wit/imu → FASTLIO2
FASTLIO2 → /body_cloud + /lio_odom → PGO (pose graph optimization)
PGO → TF: map→odom, /body_cloud_registered → pointcloud_to_grid → Nav2 costmap
Nav2 → /cmd_vel → serial_twistctl → C-board → 电机
C-board → serial_reader → /odom_CBoard (wheel odometry, currently unused for closed-loop)
GNSS → nmea_navsat_driver → /fix (GPS data)
```

### TF 链
```
map → odom (PGO发布, 包含回环校正偏移量)
odom → base_link (FASTLIO2发布, 包含位置和姿态)
叠加后 = 真实全局位姿
```

### 代码结构
```
src/
├── sensor_drivers/     ← 传感器驱动 (livox, IMU, GNSS, serial)
├── perception/         ← 感知层 (FASTLIO2, PGO, pointcloud处理)
├── planning/           ← 规划层 (GPS全局规划, 坐标转换)
├── navigation/         ← 导航层 (waypoint_collector, waypoint_nav_tool)
├── bringup/            ← 系统集成 (launch, config, maps, rviz)
└── third_party/        ← 第三方依赖 (Nav2, slam_toolbox, via dependencies.repos)
```

### 包构建类型
- ament_cmake (C++): livox_ros_driver2, serial, FASTLIO2, pointcloud_to_grid
- ament_python (Python): global2local_tf, gnss_global_path_planner, waypoint_collector, wit_ros2_imu

### 关键依赖
- PCL, OpenCV, Eigen3, yaml-cpp, NLopt, Livox SDK2, GTSAM (for PGO)

### Explore 模式启动顺序
1. 同时启动: Livox MID360, PGO(含FASTLIO2+RViz), 串口控制节点, 串口读取节点
2. 延时5秒后启动: Nav2导航栈
3. 用户在 RViz 中设定目标点 → 车辆自主避障行驶

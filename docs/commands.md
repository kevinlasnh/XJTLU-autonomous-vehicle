# 操作命令手册

本文档汇总项目所有常用命令，路径已更新为新 monorepo 工作空间 `~/fyp_autonomous_vehicle`。


---


## 1. 构建 & Source

```bash
# 完整构建（受内存限制，必须 --parallel-workers 1）
cd ~/fyp_autonomous_vehicle && colcon build --symlink-install --parallel-workers 1

# Source 环境
source /opt/ros/humble/setup.bash && source ~/fyp_autonomous_vehicle/install/setup.bash

# 通过 Makefile 构建（推荐）
make build                # 全量构建
make build-sensor         # 仅构建传感器层
make build-perception     # 仅构建感知层
make build-planning       # 仅构建规划层
make build-navigation     # 仅构建导航层

# 构建单个包
colcon build --packages-select <pkg_name> --symlink-install

# 首次搭建：拉取第三方依赖 + rosdep 安装
make setup
```


---


## 2. 启动系统

```bash
# 三种运行模式（通过 Makefile）
make launch-slam          # SLAM 建图模式
make launch-explore       # 实时避障模式（当前主要模式）
make launch-travel        # 静态地图导航模式

# 手动启动（等效）
ros2 launch bringup system_slam.launch.py
ros2 launch bringup system_explore.launch.py
ros2 launch bringup system_travel.launch.py

# 手动启动 Nav2
ros2 launch nav2_bringup navigation_launch.py use_sim_time:=false params_file:=<path>
```


---


## 3. 单独启动传感器

```bash
# LiDAR（Livox MID360）
ros2 launch livox_ros_driver2 msg_MID360_launch.py

# IMU（WIT）
ros2 run wit_ros2_imu wit_ros2_imu

# 串口读取（下位机数据）
ros2 run serial_reader serial_reader_node

# 串口控制（发送速度指令）
ros2 run serial_twistctl serial_twistctl_node

# GNSS
ros2 launch nmea_navsat_driver nmea_serial_driver.launch.py

# GPS 路径
ros2 launch wheeltec_gps_path gps_path.launch.py

# GNSS 标定（带超时）
timeout 100 ros2 launch gnss_calibration gnss_calibration_launch.py
```


---


## 4. 感知层单独启动

```bash
# PGO + FASTLIO2 + RViz（完整感知链路）
ros2 launch pgo pgo_launch.py

# 仅 FASTLIO2
ros2 launch fastlio2 lio_launch.py
```


---


## 5. 运行中调试

```bash
# Topic 相关
ros2 topic list
ros2 topic echo <topic>
ros2 topic hz <topic>
ros2 topic hz /scan

# Node 相关
ros2 node list
ros2 node info <node>
ros2 node list | grep waypoint

# 参数查询
ros2 param get /tf_buffer_node buffer_length

# TF 调试
ros2 run tf2_ros tf2_monitor                    # 查看所有 TF
ros2 run tf2_ros tf2_monitor map odom           # 监控 map→odom
ros2 run tf2_ros tf2_monitor odom base_link     # 监控 odom→base_link
ros2 run tf2_tools tf2_echo map base_link       # 输出 map→base_link 变换

# 地图元数据
ros2 topic echo /map_metadata --once
```


---


## 6. 地图保存

```bash
# 保存 3D 点云地图（PCD）
ros2 service call /pgo/save_maps interface/srv/SaveMaps \
  "{file_path: '~/fyp_runtime_data/maps/3d/<dir>', save_patches: true}"

# 保存 2D 栅格地图
ros2 run nav2_map_server map_saver_cli -f ~/fyp_runtime_data/maps/2d/<dir>/map

# 查看 3D 点云地图
pcl_viewer -bc 1,1,1 -ps 3 <map.pcd>
```


---


## 7. 紧急停车

```bash
# 软件层面：杀死所有 ROS2 进程
pkill -f ros2

# 通过 Makefile
make kill
```

**硬件层面：**

| 方式 | 操作 | 说明 |
|------|------|------|
| PS2 手柄 X 键 | 按下 | 失能电机（车轮自由滑行） |
| PS2 手柄 B 键 | **禁止使用** | 紧急刹车会导致车轮严重反转 |
| 车身红色急停按钮 | 按下停车，旋转释放 | 物理级别断电 |


---


## 8. ROS2 Daemon

```bash
# 重启 daemon（topic/node 列表异常时使用）
ros2 daemon stop && sleep 2 && ros2 daemon start && sleep 2

# 查看 daemon 状态
ros2 daemon status
```


---


## 9. Git 操作

```bash
# 推送代码（绕过 Clash 代理）
git -c http.proxy= -c https.proxy= push -u origin main

# 关闭全局代理
git config --global --unset http.proxy
git config --global --unset https.proxy

# 重新启用代理
git config --global http.proxy http://127.0.0.1:7890
```


---


## 10. 系统维护

```bash
# 磁盘使用
df -h /

# 内存使用
free -h

# 系统监控
htop

# JetPack 版本
cat /etc/nv_tegra_release

# 板卡型号
cat /proc/device-tree/model

# SSH 连接（通过 Tailscale）
ssh jetson@100.97.227.24
```

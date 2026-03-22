# 操作命令手册

本文档只记录当前仓库和当前 Jetson 环境下确认可执行的命令。

## 1. 构建与 Source

```bash
cd ~/fyp_autonomous_vehicle

# 首次依赖初始化
make setup

# 全量构建
make build

# 分层构建
make build-sensor
make build-perception
make build-planning
make build-navigation

# 单包构建
colcon build --packages-select <pkg> --symlink-install --parallel-workers 1

# 每次构建后必须重新 source
source /opt/ros/humble/setup.bash
source ~/fyp_autonomous_vehicle/install/setup.bash
```

## 2. 初始化运行时数据

```bash
cd ~/fyp_autonomous_vehicle
bash scripts/init_runtime_data.sh

ls ~/fyp_runtime_data
```

## 3. 启动五种运行模式

```bash
cd ~/fyp_autonomous_vehicle

make launch-slam
make launch-explore
make launch-explore-gps
make launch-nav-gps
make launch-travel
```

等效的 wrapper 直调方式：

```bash
bash scripts/launch_with_logs.sh slam
bash scripts/launch_with_logs.sh explore
bash scripts/launch_with_logs.sh explore-gps
bash scripts/launch_with_logs.sh nav-gps
bash scripts/launch_with_logs.sh travel
```

等效的 `ros2 launch` 方式：

```bash
ros2 launch bringup system_slam.launch.py
ros2 launch bringup system_explore.launch.py
ros2 launch bringup system_explore_gps.launch.py
ros2 launch bringup system_nav_gps.launch.py
ros2 launch bringup system_travel.launch.py
```

## 4. 单独启动核心组件

```bash
# Livox
ros2 launch livox_ros_driver2 msg_MID360_launch.py

# WIT IMU
ros2 run wit_ros2_imu wit_ros2_imu

# GNSS 原始驱动
ros2 launch nmea_navsat_driver nmea_serial_driver.launch.py

# GNSS 标定
ros2 launch gnss_calibration gnss_calibration_launch.py

# GNSS scene-ready localizer（新 GPS 路网架构）
ros2 run gnss_calibration gps_anchor_localizer_node \
  --ros-args --params-file ~/fyp_runtime_data/gnss/current_scene/master_params_scene.yaml

# FAST-LIO2
ros2 launch fastlio2 lio_no_rviz.py params_file:=~/fyp_autonomous_vehicle/src/bringup/config/master_params.yaml

# PGO + FAST-LIO2
ros2 launch pgo pgo_launch.py params_file:=~/fyp_autonomous_vehicle/src/bringup/config/master_params.yaml

# 兼容旧平铺 PGO 配置
ros2 launch pgo pgo_launch.py pgo_config:=pgo_no_gps.yaml

# 串口节点
ros2 run serial_reader serial_reader_node
ros2 run serial_twistctl serial_twistctl_node

# waypoint_collector
ros2 run waypoint_collector waypoint_node

# GPS goal manager CLI
ros2 run gps_waypoint_dispatcher goto_name <destination_name>
ros2 run gps_waypoint_dispatcher list_destinations
ros2 run gps_waypoint_dispatcher stop
```

## 5. 调试与状态检查

```bash
# topic / node / action
ros2 topic list
ros2 node list
ros2 action list
ros2 action info /compute_route
ros2 action info /follow_path
ros2 action info /navigate_to_pose
ros2 node info /pgo/pgo_node

# 频率与消息
ros2 topic hz /livox/lidar
ros2 topic hz /fastlio2/body_cloud
ros2 topic echo /pgo/optimized_odom --once
ros2 topic echo /fix --once
ros2 topic echo /gnss --once
ros2 topic echo /gps_system/status --once
ros2 topic echo /gps_system/nearest_anchor --once
ros2 topic echo /gps_system/nearest_anchor_id --once
ros2 topic echo /gps_goal_manager/status --once
ros2 topic echo /gps_waypoint_dispatcher/goal_map --once
ros2 topic echo /gps_waypoint_dispatcher/path_map --once

# 参数
ros2 param get /fastlio2/lio_node lidar_max_range
ros2 param get /pgo/pgo_node gps.enable
ros2 param get /pgo/pgo_node gps.topic
ros2 param get /pgo/pgo_node gps.origin_mode

# TF
ros2 run tf2_ros tf2_monitor
ros2 run tf2_ros tf2_monitor map odom
ros2 run tf2_ros tf2_monitor odom base_link
ros2 run tf2_tools tf2_echo map base_link
```

常见诊断重点：

- `map -> odom` 是否存在
- `/pgo/optimized_odom` 是否在持续发布
- `/gps_system/status` 是否已经到 `NAV_READY`
- `/gnss` 是否为 `gps_anchor_localizer` 发布的有效 scene-calibrated GNSS 数据
- `/compute_route` / `/follow_path` / `/navigate_to_pose` action 是否在线
- RViz fixed frame 是否为 `map`

## 6. 日志与运行时数据

```bash
# 查看当前 latest 指向
readlink -f ~/fyp_runtime_data/logs/latest

# 查看当前 session 元信息
cat ~/fyp_runtime_data/logs/latest/system/session_info.yaml

# 查看 tegrastats
tail -f ~/fyp_runtime_data/logs/latest/system/tegrastats.log

# 查看 console 日志目录
ls ~/fyp_runtime_data/logs/latest/console

# 查看 data 日志目录
ls ~/fyp_runtime_data/logs/latest/data
```

## 7. 数据采集与评测

```bash
# 录制 rosbag
bash scripts/data_collection/record_bag.sh
bash scripts/data_collection/record_bag.sh ~/fyp_runtime_data/bags/my_run

# 单独录 tegrastats
bash scripts/data_collection/record_perf.sh
bash scripts/data_collection/record_perf.sh ~/fyp_runtime_data/perf/my_run.log

# 导出 TUM 轨迹
python3 scripts/data_collection/bag_to_tum.py   ~/fyp_runtime_data/bags/my_run/rosbag2   /pgo/optimized_odom   ~/fyp_runtime_data/bags/my_run/pgo_optimized.tum
```

## 8. 地图保存

```bash
# 保存 3D 点云地图
ros2 service call /pgo/save_maps interface/srv/SaveMaps   "{file_path: '~/fyp_runtime_data/maps/3d/<dir>', save_patches: true}"

# 保存 2D 栅格地图
ros2 run nav2_map_server map_saver_cli -f ~/fyp_runtime_data/maps/2d/<dir>/map

# 查看 PCD
pcl_viewer -bc 1,1,1 -ps 3 <map.pcd>
```

## 9. 停止系统与紧急停车

```bash
make kill
pkill -f ros2
```

硬件层面的急停优先级：

1. PS2 手柄 `X` 键失能电机
2. 车身红色物理急停按钮

## 10. Git 与 PR

```bash
# 同步 main
git checkout main
git pull --ff-only

# 创建分支
git checkout -b docs/sync-current-state

# 检查状态
git status
git branch -v
git log --oneline -5

# 推送分支
git push -u origin docs/sync-current-state
```

GitHub CLI：

```bash
gh auth status
gh pr create
gh pr merge --merge --delete-branch
```

如果 Jetson 上 `gh auth status` 返回 token 无效，可以在已登录 GitHub CLI 的本地工作站上对同一分支执行 `gh pr create` / `gh pr merge`，然后回 Jetson 执行：

```bash
git checkout main
git pull --ff-only
git fetch --prune
```

## 11. 系统维护

```bash
# 磁盘 / 内存
df -h /
free -h
htop

# JetPack / 机型
cat /etc/nv_tegra_release
cat /proc/device-tree/model

# NetworkManager 与有线网口自启动状态
systemctl is-enabled NetworkManager
systemctl is-active NetworkManager
nmcli -t -f NAME,AUTOCONNECT,AUTOCONNECT-PRIORITY,DEVICE connection show --active

# 检查当前机器是否具备无密码 sudo
sudo -n true && echo sudo_ok

# 切换 Jetson WiFi，并在 Jetson 侧重启 ToDesk（Linux 本机直接执行）
cd ~/fyp_autonomous_vehicle && bash scripts/switch_jetson_wifi.sh --status
cd ~/fyp_autonomous_vehicle && bash scripts/switch_jetson_wifi.sh
cd ~/fyp_autonomous_vehicle && bash scripts/switch_jetson_wifi.sh outdoor
cd ~/fyp_autonomous_vehicle && bash scripts/switch_jetson_wifi.sh indoor
cd ~/fyp_autonomous_vehicle && bash scripts/switch_jetson_wifi.sh Pixel
cd ~/fyp_autonomous_vehicle && bash scripts/switch_jetson_wifi.sh XJTLU

# GPS dispatcher 依赖
apt list --installed | grep ros-humble-geographic-msgs
python3 -c "import pyproj; print(pyproj.__version__)"
```

说明：
- 不带参数时默认在 `XJTLU` 和 `Pixel` 之间 toggle
- 上面这几条就是在 Jetson / Linux 本机直接运行的完整一行命令
- 脚本在 Jetson 本机执行时会自动切到本地模式；如果当前 shell 是 SSH/Tailscale，会话可能在切网过程中断开
- 每次切网都会在 Jetson 侧重启 `todeskd`，日志写入 `/tmp/wifi-switch.log`

## 12. GPS 数据采集

最短两行启动命令：

```bash
cd ~/fyp_autonomous_vehicle && source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch nmea_navsat_driver nmea_serial_driver.launch.py params_file:=/home/jetson/fyp_autonomous_vehicle/src/bringup/config/master_params.yaml
cd ~/fyp_autonomous_vehicle && source /opt/ros/humble/setup.bash && source install/setup.bash && python3 scripts/collect_gps_scene.py
```

```bash
cd ~/fyp_autonomous_vehicle
source /opt/ros/humble/setup.bash
source install/setup.bash
python3 scripts/collect_gps_scene.py
```

脚本说明：
- 坐标源: **仅使用 /fix**
- 采样: 每点 10 个样本取平均
- 质量门槛: 样本散布 < 2m，否则拒绝采集
- 输出文件: `~/fyp_runtime_data/gnss/scene_gps_bundle.yaml`
- 单文件同时维护：
  - fixed origin
  - graph nodes
  - `anchor`
  - `dest`
  - edges

交互命令：
- `Enter`：采图点
- `e`：添加两点之间的边，按双向通行处理
- `o`：从已有点里选择 fixed origin
- `u`：修改已有点的名字 / anchor / destination
- `l`：列出所有点和边，显示 anchor / dest / origin
- `d`：按 ID 删除指定点
- `q`：保存并退出

采集后编译运行时文件：

```bash
cd ~/fyp_autonomous_vehicle
source /opt/ros/humble/setup.bash
source install/setup.bash
python3 scripts/build_scene_runtime.py
```

采集规范：
- 所有转弯、路口、目的地入口必须踩点
- 允许系统上电启动的区域附近必须布 `anchor`
- graph edge 按节点间直线段理解，弯道必须靠增加节点离散化
- 脚本会提示是否与上一个点自动建边

## 13. GPS 导航调试

```bash
# 启动 nav-gps
make launch-nav-gps

# 查看 scene 目标列表
ros2 run gps_waypoint_dispatcher list_destinations

# 室内软件 smoke 可用 mock /fix 驱动 gps_anchor_localizer
ros2 topic pub /fix sensor_msgs/msg/NavSatFix \
  "{header: {frame_id: 'gps'}, status: {status: 0, service: 1}, latitude: 31.274927, longitude: 120.737548, altitude: 0.0, position_covariance: [4.0, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.0, 25.0], position_covariance_type: 2}" \
  --rate 5

# 观察 ready 状态
ros2 topic echo /gps_system/status
ros2 topic echo /gps_goal_manager/status

# 发送英文命名目标
ros2 run gps_waypoint_dispatcher goto_name anchor_a

# 检查 route / local planner action 是否在线
ros2 action list | grep -E 'compute_route|follow_path|navigate_to_pose'

# 停止当前任务
ros2 run gps_waypoint_dispatcher stop

# 一键拉起 nav-gps，等待 NAV_READY，并按编号选择 destination
cd ~/fyp_autonomous_vehicle && source /opt/ros/humble/setup.bash && source install/setup.bash && python3 scripts/nav_gps_menu.py
```

## 14. Fixed-Launch GPS Corridor

两点 corridor 采集：

```bash
cd ~/fyp_autonomous_vehicle && source /opt/ros/humble/setup.bash && source install/setup.bash && python3 scripts/collect_two_point_corridor.py
```

自动 corridor 导航：

```bash
cd ~/fyp_autonomous_vehicle && source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch bringup system_gps_corridor.launch.py
```

调试观察：

```bash
ros2 topic echo /gps_corridor/status
ros2 topic echo /gps_corridor/goal_map
ros2 topic echo /gps_corridor/path_map
```

说明：
- 该模式假定车辆已经摆在固定 Launch Pose，并且车头朝向摆正
- `collect_two_point_corridor.py` 只采两个点：固定启动点与固定终点
- collect_two_point_corridor.py 若未检测到 /fix，会自动后台拉起 nmea_navsat_driver，采完后自动收掉
- 运行时不会再弹出 menu，也不会等待额外命令
- corridor 第一版默认终点位于车辆启动朝向的正前方，`body_vector_m = [distance_m, 0]`
- 启动阶段若当前 `/fix` 与 `start_ref` 偏差超限，`gps_corridor_runner_node` 会直接 abort，不动车


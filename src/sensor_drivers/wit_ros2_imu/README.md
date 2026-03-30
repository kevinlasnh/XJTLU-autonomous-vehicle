# wit_ros2_imu

`wit_ros2_imu` 是 WIT IMU 的 ROS 2 驱动包，当前主要发布 `/imu/data_raw`，供实验性 GNSS 规划链路和独立调试使用。

## 当前行为

- 节点名: `imu_driver_node`
- 发布话题: `/imu/data_raw`
- 消息类型: `sensor_msgs/msg/Imu`
- 默认串口设备: `/dev/imu_usb`
- 默认波特率: `9600`

## 当前实现细节

- 节点会解析 WIT 串口帧中的加速度、角速度、姿态角和磁力计原始值。
- 发布给 ROS 的主输出只有 `Imu` 消息，没有单独发布磁力计话题。
- 日志开关由 `~/XJTLU-autonomous-vehicle/runtime-data/config/log_switch.yaml` 控制。
- 通过 `scripts/launch_with_logs.sh` 启动时，日志会落入当前 session 目录；否则回退到 `~/XJTLU-autonomous-vehicle/runtime-data/logs/wit_imu_log/`。

## 当前限制

- `rviz_and_imu.launch.py` 里虽然声明了 `port` 参数，但主实现 `wit_ros2_imu.py` 仍在 `driver_loop()` 中硬编码打开 `/dev/imu_usb`。也就是说，现阶段修改 launch 参数并不能真正切换串口设备。
- 该包目前不是 FAST-LIO2 的主 IMU 来源；FAST-LIO2 仍主要使用 Livox 链路内的 IMU 数据。

## 构建与运行

从工作区根目录执行:

```bash
colcon build --packages-select wit_ros2_imu --symlink-install --parallel-workers 1
source install/setup.bash
ros2 run wit_ros2_imu wit_ros2_imu
```

或:

```bash
ros2 launch wit_ros2_imu rviz_and_imu.launch.py
```

# global2local_tf

`global2local_tf` 是一个实验性规划辅助包，用来把经纬度路径转换成局部平面坐标。它目前不在主工作流 `make launch-slam` / `make launch-explore` / `make launch-explore-gps` / `make launch-travel` 中自动启动，主要保留给 GNSS 全局路径规划试验。

## 当前功能

- 订阅 `/gnss`，取前 3 个样本的平均值作为局部坐标原点。
- 订阅 `/imu/data_raw`，读取姿态消息后完成初始朝向准备。
- 订阅 `/next_node`，把 `"longitude,latitude"` 字符串转换为 `/target_pos` (`geometry_msgs/PoseStamped`)。
- 订阅 `/path4global`，把全球路径转换为 `/path4local` (`nav_msgs/Path`)。

## 当前实现要点

- 运行时会读取 `~/fyp_runtime_data/planning/angle_offset.txt` 作为航向偏置；文件不存在时回退到 `0.0`。
- 节点初始化完成的条件是:
  - 收到 3 个 `/gnss` 样本，用它们的平均值锁定原点。
  - 收到 3 个 IMU 样本，锁定初始朝向。
- 现版本代码里，初始朝向使用固定基角 `268` 度再叠加 `angle_offset`，并没有直接使用 IMU 实时 yaw 作为最终朝向。这是当前实现的真实状态，不是通用坐标转换范式。
- 坐标换算使用 `geopy.distance.geodesic` 先求经纬度对应的米级偏移，再按初始朝向旋转到本地平面。

## 话题接口

### 输入

- `/gnss` (`sensor_msgs/msg/NavSatFix`)
- `/imu/data_raw` (`sensor_msgs/msg/Imu`)
- `/next_node` (`std_msgs/msg/String`)
- `/path4global` (`nav_msgs/msg/Path`)

### 输出

- `/target_pos` (`geometry_msgs/msg/PoseStamped`)
- `/path4local` (`nav_msgs/msg/Path`)

## 启动与构建

从工作区根目录执行:

```bash
colcon build --packages-select global2local_tf --symlink-install --parallel-workers 1
source install/setup.bash
ros2 launch global2local_tf global2local_tf.launch.py
```

`global2local_tf.launch.py` 会同时拉起本包节点和 `wit_ros2_imu` 的 `rviz_and_imu.launch.py`。

## 当前限制

- 这是实验路径，不是整车生产主入口。
- 包内保留了多个 `copy*.py` 历史草稿文件，当前实际入口是 `global2local_tf/global2local_tf.py`。
- 如果 `angle_offset.txt` 不准确，或者 `/gnss` 初始化样本不稳定，局部坐标会整体偏转。

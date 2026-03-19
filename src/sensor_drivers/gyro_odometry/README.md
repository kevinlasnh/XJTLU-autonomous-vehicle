# gyro_odometry

`gyro_odometry` 是一个实验性的串口速度反馈节点，目标是从底盘串口读取速度数据并发布 `geometry_msgs/msg/TwistWithCovarianceStamped`。

## 当前实现状态

- 可执行文件名: `gyro_odometry`
- 发布话题: `twist_with_covariance`
- 默认串口: `/dev/serial_twistctl`
- 发送周期: `20 ms`

## 当前代码的真实行为

- 源码里全局开关 `serialopen` 目前写死为 `0`。
- 因此默认启动后不会进入串口读取分支，而是持续发布全零的 `twist_with_covariance`。
- 这说明它现在不是主工作流里启用的有效反馈源，更接近保留中的实验包。

## 构建与运行

从工作区根目录执行:

```bash
colcon build --packages-select gyro_odometry --symlink-install --parallel-workers 1
source install/setup.bash
ros2 run gyro_odometry gyro_odometry
```

## 备注

- 该包依赖仓库内的 `serial` 库。
- 如果未来要重新启用真实串口反馈，首先要处理 `serialopen` 的硬编码状态和串口数据格式校验。

# serial_twistctl

`serial_twistctl` 是底盘控制串口桥接节点。它订阅 Nav2 或上层控制器发布的 `/cmd_vel`，把速度指令格式化后发给下位 C 板。这个节点在当前主模式里是生产链路的一部分。

## 当前接口

### 输入

- `/cmd_vel` (`geometry_msgs/msg/Twist`)

### 输出

- 无 ROS 话题输出，数据直接写入串口
- 可选日志:
  - session 模式下写入 `~/fyp_runtime_data/logs/latest/...`
  - 非 session 模式下回退到 `~/fyp_runtime_data/logs/twist_log/`

## 当前串口协议

收到 `/cmd_vel` 后，节点会生成如下格式的命令:

```text
vcx=<linear.x>,wc=<angular.z>
```

实际发送字符串末尾会附带换行。

## 当前参数

- `port`
  - 默认 `/dev/serial_twistctl`
- `baudrate`
  - 默认 `115200`
- `send_attempts`
  - 默认 `1`
- `delay_between_attempts_ms`
  - 默认 `0`

这些参数由 `master_params.yaml` 和各模式 launch 文件统一下发。

## 构建与单独调试

从工作区根目录执行:

```bash
colcon build --packages-select serial_twistctl --symlink-install --parallel-workers 1
source install/setup.bash
ros2 run serial_twistctl serial_twistctl_node
```

## 运维注意事项

- 当前整车默认依赖 udev 命名的 `/dev/serial_twistctl`，不是临时 `chmod 666 /dev/ttyACM0` 工作流。
- 如果串口打不开，优先检查:
  - 设备节点是否存在
  - udev 规则是否生效
  - 下位机是否上电
  - `master_params.yaml` 中端口参数是否被改坏

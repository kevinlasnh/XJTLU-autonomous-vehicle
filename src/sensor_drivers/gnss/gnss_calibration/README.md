# gnss_calibration

`gnss_calibration` 负责把原始 GNSS `/fix` 数据校准后发布为 `/gnss`，供 PGO GPS 因子和后续 GNSS 试验链路使用。当前 `make launch-explore-gps` 会通过 `system_explore_gps.launch.py` 拉起这个包。

## 当前链路

```text
nmea_navsat_driver -> /fix -> gnss_calibration -> /gnss
```

## 当前行为

- 从 `~/fyp_runtime_data/gnss/startid.txt` 读取起始校准点编号，支持 `1-4`。
- 对 `/fix` 进行样本筛选，以下数据会被直接跳过:
  - `status < 0`
  - `latitude/longitude/altitude` 非有限数
  - 经纬度同时为 `0.0`
  - `position_covariance_type == COVARIANCE_TYPE_UNKNOWN`
- 只有在连续 5 个样本落在 1 米稳定范围内时，才会计算并保存偏移量。
- 计算出的偏移量写入 `~/fyp_runtime_data/gnss/gnss_offset.txt`。
- 校准后沿用原始消息头、状态、高度和协方差，只修正经纬度，然后发布到 `/gnss`。

## 运行时文件

- `~/fyp_runtime_data/gnss/startid.txt`
  - 启动前必须存在，内容为 `1-4` 之一。
- `~/fyp_runtime_data/gnss/gnss_offset.txt`
  - 校准成功后生成，两行分别是纬度偏移和经度偏移。
- 日志输出
  - 若由 `scripts/launch_with_logs.sh` 启动，日志写入当前 session 目录。
  - 否则回退到 `~/fyp_runtime_data/logs/gnss_calibration/`。

## 启动与构建

从工作区根目录执行:

```bash
colcon build --packages-select gnss_calibration --symlink-install --parallel-workers 1
source install/setup.bash
ros2 launch gnss_calibration gnss_calibration_launch.py
```

## 现场约束

- 当前基础 GPS 不是 RTK。
- 如果现场没有有效 fix，`gnss_offset.txt` 不会被刷新，这正是当前代码有意保持的保护行为。
- `startid.txt` 需要与当天实际停车起点一致，否则校准结果会整体偏移。

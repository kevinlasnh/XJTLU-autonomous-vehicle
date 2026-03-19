# PGO 位姿图优化说明

## 1. 当前工程实现（2026-03）

当前主用 PGO 实现在：

- 目录: `src/perception/pgo_gps_fusion/`
- colcon 包名: `pgo`
- 启动入口: `ros2 launch pgo pgo_launch.py`

这个实现不是“纯回环 PGO”了，而是：

- FAST-LIO2 局部里程计
- PGO 回环图优化
- 可选 GPS factor 绝对位置约束

## 2. 当前输入与输出

### 输入

- 点云: `/fastlio2/body_cloud`
- 里程计: `/fastlio2/lio_odom`
- GNSS: `/gnss`（当 `gps.enable=true` 时）

### 输出

- TF: `map -> odom`
- 里程计: `/pgo/optimized_odom`
- 可视化: `/pgo/loop_markers`

## 3. 节点职责

PGO 当前承担 5 件事：

1. 从 FAST-LIO2 收集关键帧
2. 做回环搜索与 ICP 确认
3. 用 GTSAM 做位姿图优化
4. 在启用时周期性加入 GPS factor
5. 发布 `map -> odom` 和 `/pgo/optimized_odom`

## 4. 当前主配置参数

这些值来自当前主线 `master_params.yaml`：

- `key_pose_delta_deg: 5.0`
- `key_pose_delta_trans: 0.1`
- `loop_search_radius: 1.0`
- `loop_time_tresh: 60.0`
- `loop_score_tresh: 0.15`
- `loop_submap_half_range: 5`
- `submap_resolution: 0.1`
- `min_loop_detect_duration: 5.0`

这说明当前工程配置比早期设计更激进地保留关键帧，也把回环搜索半径收得更小，更偏向实际车辆场景而不是泛化演示参数。

## 5. GPS Factor 行为

当 `gps.enable=true` 时，PGO 会使用以下 GNSS 相关参数：

- `gps.topic: /gnss`
- `gps.noise_xy: 2.5`
- `gps.noise_z: 5.0`
- `gps.factor_interval: 10`
- `gps.quality_hdop_max: 3.0`
- `gps.quality_sat_min: 6`
- `gps.drift_threshold: 2.0`

当前 GPS 因子职责是给关键帧的位置增加绝对约束，降低长距离运行时的全局漂移；它不是完整的 GPS 全局导航方案。

## 6. TF 关系

```text
map -> odom -> base_link
```

- FAST-LIO2 提供 `odom -> base_link`
- PGO 提供 `map -> odom`
- 组合后得到全局位姿

如果 PGO 没有进入正常关键帧和优化流程，`map -> odom` 就可能消失，RViz 在 `map` fixed frame 下会表现为点云和 costmap 看起来像“空白”。

## 7. 2026-03-18 启动回归修复

### 现象

- `pgo_node` 启动后持续刷 `Received out of order message`
- 没有稳定关键帧
- 没有稳定 `map -> odom`
- `/pgo/optimized_odom` 不稳定或不发布

### 根因

同步状态中的 `last_message_time` 未初始化，第一对同步消息会被错误判定为 out-of-order。

### 修复

将 `last_message_time` 初始化为 `0.0`，保证第一对匹配消息被正常接受。

### 结果

该修复已经合并到 `main`，当前主线的 PGO 启动同步状态是稳定初始化版本。

## 8. 接口速查

| 接口 | 类型 | 说明 |
|------|------|------|
| `/fastlio2/body_cloud` | `sensor_msgs/PointCloud2` | PGO 关键帧点云输入 |
| `/fastlio2/lio_odom` | `nav_msgs/Odometry` | PGO 位姿输入 |
| `/gnss` | `sensor_msgs/NavSatFix` | GPS factor 输入 |
| `/pgo/optimized_odom` | `nav_msgs/Odometry` | 优化后位姿输出 |
| `map -> odom` | TF | 全局校正偏移 |
| `/pgo/loop_markers` | Marker | 回环可视化 |

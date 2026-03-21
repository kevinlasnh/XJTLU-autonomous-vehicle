# ICAC 2026 — Corridor v1 GPS 导航技术方案

**Status**: `implemented / first outdoor baseline validated`
**Jetson 分支**: `feature/gps-corridor-launch`
**最后更新**: 2026-03-21

---

## 当前方案概述

固定 Launch Pose 下的两点直线 corridor 自动导航。

- 预采 1 个起点 GPS + 1 个终点 GPS
- launch 文件一键启动整站
- 自动读取 corridor 数据、采集当前 GPS、校验启动位、生成中间航点、串行导航
- 不依赖 scene graph / route_server / menu 脚本

### 核心假设

1. 车每次从同一个物理位置、同一朝向上电
2. corridor 内本次 GNSS 会话误差可近似为整体平移
3. 目标不依赖绝对 GPS 真值，而是用 body_vector（车体坐标系相对位移）

### 已落地文件

| 文件 | 说明 |
|------|------|
| `src/bringup/launch/system_gps_corridor.launch.py` | 唯一启动入口 |
| `src/navigation/gps_waypoint_dispatcher/gps_waypoint_dispatcher/gps_corridor_runner_node.py` | corridor 自动导航节点 |
| `scripts/collect_two_point_corridor.py` | 两点采集脚本 |
| `src/navigation/gps_waypoint_dispatcher/setup.py` | 包注册 |
| `~/fyp_runtime_data/gnss/two_point_corridor.yaml` | runtime corridor 数据 |

### 启动链架构

基底: `system_explore.launch.py`（Livox + PGO/FAST-LIO2 + Nav2 Explore）
叠加: `nmea_navsat_driver` + `gps_corridor_runner_node`

### Runner 控制流

1. 读取 `two_point_corridor.yaml`
2. 等待: `/fix` 稳定 + Nav2 action server + `map->base_link` TF
3. 采当前启动点 GPS → `start_session_gps`
4. 校验 `start_session_gps` 是否在 `startup_gps_tolerance_m` 内
5. 从 `map->base_link` 读启动位姿 `(x0, y0, yaw0)`
6. 用 `body_vector_m` 生成终点: `goal_map = (x0, y0, yaw0) + body_vector_m`
7. 按 `segment_length_m` 切中间 `PoseStamped`
8. 串行 `NavigateToPose`，一次一个

### Corridor YAML Schema

```yaml
corridor_name: ls_start_to_goal
created_at: 2026-03-21 00:00:00
coordinate_source: /fix
start_ref:
  lat: 0.0
  lon: 0.0
  alt: 0.0
goal_ref:
  lat: 0.0
  lon: 0.0
  alt: 0.0
distance_m: 0.0
bearing_deg: 0.0
body_vector_m:
  x: 0.0
  y: 0.0
segment_length_m: 8.0
startup_fix_sample_count: 10
startup_fix_spread_max_m: 2.0
startup_gps_tolerance_m: 6.0
```

### 用户现场操作

```bash
# 采点（一次性）
cd ~/fyp_autonomous_vehicle
source /opt/ros/humble/setup.bash && source install/setup.bash
python3 scripts/collect_two_point_corridor.py

# 运行导航
ros2 launch bringup system_gps_corridor.launch.py
```

### 构建命令

```bash
colcon build --packages-select gps_waypoint_dispatcher bringup --symlink-install --parallel-workers 1
source install/setup.bash
```

---

## 首次室外验证结果 (2026-03-21)

- 车辆可从固定 Launch Pose 自动出发
- 沿 corridor 朝目标点导航
- 已到达目标附近
- **终点仍有几米级误差**（大概率 GNSS 会话漂移）

---

## 待解决问题

### P0: 终点精度不足

当前到达目标附近但有几米级误差。可能的改进方向：
- 启动位一致性强化
- 目标点会话对齐优化
- ENU→map 旋转校准（当前 body_vector 假设 yaw0 准确，但 IMU 无磁力计，初始 yaw 有不确定性）

### P1: 采点脚本已知行为

- 若未检测到 `/fix`，自动后台拉起 `nmea_navsat_driver`
- 采完两点后自动收掉驱动

### 回退策略

corridor 模式失败时回退到 `system_explore.launch.py`（纯 Explore 避障），corridor 是独立新增模式，不污染现有主模式。

---

## 已废弃方案（仅留索引）

以下方案在 corridor v1 确立后已全部废弃，不再作为开发主线：

| 方案 | 分支 | 废弃原因 |
|------|------|----------|
| v7 scene graph + route_server + Kabsch yaw | `feature/gps-route-ready-v2` | 对单 corridor 需求过重，GPS NO_FIX 阻塞验证后被替代 |
| v6 整条 route 动态重算 | 同上 | 引入 frame 混用、回头/跳点风险 |
| 旧 gnss_global_path_planner A* | 无独立分支 | 依赖旧路网 + 硬编码 angle，不可部署 |

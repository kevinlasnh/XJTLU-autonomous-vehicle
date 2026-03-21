# FYP Autonomous Vehicle - Findings

**最后更新**: 2026-03-21

---

## 2026-03-21 深度调研结论

### 导航定位链路真相

当前 Nav2 全程用 SLAM（FAST-LIO2 via PGO）定位，**GPS 在导航期间完全不参与**：

```
Livox MID360 → FAST-LIO2 → PGO → map→base_link TF → Nav2
GPS: 仅在 corridor runner 启动时采样做距离校验（< 6m），之后再不使用
```

用户担心的"GPS 导航中漂移"问题在当前架构下不存在。

### PGO GPS 融合实现深度分析

**源码位置**：`src/perception/pgo_gps_fusion/src/pgo_node.cpp` + `pgos/simple_pgo.cpp`

**GPS→ENU 转换**：GeographicLib::LocalCartesian（精确 WGS84 椭球），固定原点 (31.274927, 120.737548, 0.0)

**GPS Factor 类型**：gtsam::GPSFactor — 只约束平移 (x,y,z)，**不约束旋转**

**核心问题 — GPS 融合名义存在但功能无效**：

| 问题 | 详情 |
|------|------|
| Topic 错配 | 配置 `/gnss`，NMEA 驱动发 `/fix`，数据收不到 |
| ENU→map 无旋转 | ENU (x=东,y=北) 被直接当 map 坐标注入，但 map 的轴方向由 IMU 上电决定（随机 yaw）。代码中无任何旋转估计逻辑 |
| 权重失衡 | 里程计噪声 1e-4~1e-6 vs GPS 噪声 2.5m，GPS 权重低 4-6 个数量级 |
| 首帧先验锁死 | variance=1e-12，GPS 无法移动起始位置 |
| 死代码 | `gps_quality_sat_min`, `gps_drift_threshold`, `gps_alert_interval`, `gps_emergency_interval` 声明但未使用 |

**结论**：即使修复 topic，由于缺少旋转对齐 + 权重失衡，GPS 对 map frame 无有意义影响。需要代码级修改。

### 已有 GPS Offset 实现

`gps_anchor_localizer_node`（`src/sensor_drivers/gnss/gnss_calibration/`）已实现：
- 订阅 raw `/fix` → pyproj ENU 转换（同 ENU 原点）→ 锚点匹配 → offset 修正 → 发布 `/gnss`
- PGO 订阅 `/gnss`（而非 raw `/fix`），所以这是设计好的管道
- **但 corridor launch 没有启动这个节点**，导致 `/gnss` 无人发布

### 终点精度不足根因确认

**是 yaw0 不确定性，不是 GPS 漂移**。

body_vector 被 yaw0 旋转后投射到 map frame。BMI088 IMU 无磁力计，FAST-LIO 初始 yaw 任意。yaw 偏 5° 在 50m corridor 上 = 4.4m 末端偏差，与观察到的"几米级"一致。

### Nav2 路径质量问题根因

**折弯/卷团**：DWB RotateToGoal scale=300 + GoalAlign scale=300，在每个 subgoal 边界强制旋转对齐。所有 subgoal 朝向相同，但 SLAM 微漂移导致每次都需要小旋转 → 折弯+螺旋。

**幻影障碍停车**：
- costmap 分辨率 0.02m（2cm），SLAM 点云微对齐误差产生单格噪声障碍
- `min_obstacle_height: -0.3`，LiDAR 安装高度约 30cm（t_il.z=0.044m + 底盘高度），地面点被标为障碍
- Livox MID360 已知在原点 (0,0,0) 生成噪声点（GitHub Issue #88）
- progress checker 3s 判定卡住，触发 recovery behavior

**全局 costmap 过重**：50×50m / 0.02m = 625 万格，Jetson 上严重负载

### 控制器选型

| 控制器 | 走廊适合度 | 计算量 | 推荐 |
|--------|-----------|--------|------|
| Regulated Pure Pursuit | 最优 | 最低 | 首选 |
| MPPI | 优 | 较高 | 备选 |
| DWB | 中（critic 权重博弈问题） | 中 | 不推荐 |

---

## Corridor v1 首次室外实车结论（保留）

- 车辆已能从固定 Launch Pose 自动出发，沿 corridor 到达目标附近
- 主要矛盾已从"能不能跑"转为"终点精度够不够"
- 末端几米级偏差，根因是 yaw0 不确定性（非 GPS 漂移）
- corridor v1 适合作为稳定 baseline，后续增量改进

---

## 已归档发现（v7 scene graph）

v7 方案调研结论已随方案废弃，核心结论：

- v7 主链（scene graph + route_server + Kabsch yaw）对单 corridor 需求过重
- v7 部署到 Jetson 后软件可启动，但被 GPS NO_FIX 阻塞实车验证
- GPS 蘑菇头硬件连接正常（ANTENNA OK），定位失败是室内环境/信号问题

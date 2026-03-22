# FYP Autonomous Vehicle - Findings

**最后更新**: 2026-03-22

---

## 2026-03-22 调研最终结论

### 1. 导航定位链路

Nav2 全程用 SLAM（FAST-LIO2 via PGO）定位，GPS 在导航期间不参与：

```
Livox MID360 → FAST-LIO2 → PGO → map→base_link TF → Nav2
GPS: 仅在 corridor runner 启动时做 sanity check（距 start_ref < 6m）
```

### 2. PGO GPS 融合深度分析

**源码**: `src/perception/pgo_gps_fusion/src/pgo_node.cpp` (926行) + `pgos/simple_pgo.cpp`

| 组件 | 实现 |
|------|------|
| GPS→ENU | GeographicLib::LocalCartesian（WGS84 椭球），固定原点 (31.274927, 120.737548) |
| GPS Factor | gtsam::GPSFactor — 只约束平移，不约束旋转 |
| 里程计因子 | BetweenFactor，噪声方差 1e-4~1e-6 |
| 首帧先验 | 方差 1e-12（基本锁死） |

**三个结构性缺陷**:
1. Topic `/gnss` vs 实际 `/fix` — 数据收不到
2. ENU→map 无旋转估计 — GPS ENU (x=东,y=北) 被直接当 map 坐标，但 map yaw 随机
3. 权重失衡 — GPS 权重比里程计低 62,500 倍，融合无效

**关键代码位置**:
- GPS factor 添加: `tryAddGPSFactor()` 第 753-807 行
- 旋转估计最佳插入点: 第 787 行（ENU 转换完成后）、第 790 行（addGPSFactor 前）
- SLAM 位姿: `m_pgo->keyPoses()[idx].t_global`（map 帧）
- offset 更新: `smoothAndUpdate()` 第 185-187 行（用 ISAM2 优化后位姿）
- 首帧先验: `addKeyPose()` 第 49 行

**跳变风险评估**: GPS factor 延迟引入（旋转估计完成后才加入）不会导致地图跳变，因为首帧先验锁死 + GPS 权重极低。但这也意味着 GPS 几乎无效，需要同步放松先验。

### 3. 已有 GPS Offset 实现

`gps_anchor_localizer_node`（`src/sensor_drivers/gnss/gnss_calibration/`）:
- /fix → pyproj ENU → 锚点匹配 → offset → /gnss
- PGO 订阅 /gnss（设计管道完整，但 corridor launch 未启动此节点）
- **新方案不使用此节点** — PGO 自行估计完整 ENU→map 变换，更简洁

### 4. 终点精度根因

**yaw0 不确定性**（非 GPS 漂移）。body_vector 被 yaw0 旋转后偏向。5° yaw 误差在 50m = 4.4m 偏差。

### 5. Nav2 路径质量

- **折弯/卷团**: DWB RotateToGoal/GoalAlign scale=300 → 解决方案: RPP 控制器
- **幻影障碍**: costmap 0.02m + min_obstacle_height=-0.3 → 解决方案: 0.05m + 0.15m + VoxelLayer
- **全局过重**: 625万格 → 解决方案: 0.10m/30×30 = 9万格

### 6. Nav2 插件可用性（Jetson 已编译确认）

- `libnav2_regulated_pure_pursuit_controller.so` ✓
- `libnav2_rotation_shim_controller.so` ✓
- `libvoxel_grid.so` ✓
- `nav2_costmap_2d::DenoiseLayer`（costmap2d 库内）✓

### 7. 旋转估计算法验证

2D 最小二乘旋转估计（cross-covariance → atan2）:
- 架构兼容: PGO 的 `t_global` 可获取 map 帧位姿，与 ENU 配对 ✓
- offset 计算自然受益: 优化后 global 位姿反映 GPS 拉力 ✓
- 跳变安全: 当前权重下延迟引入无跳变风险 ✓

---

## 已归档发现

### v7 scene graph（已废弃）

- v7 主链对单 corridor 需求过重
- v7 部署到 Jetson 后被 GPS NO_FIX 阻塞
- GPS 蘑菇头硬件连接正常，室内无信号

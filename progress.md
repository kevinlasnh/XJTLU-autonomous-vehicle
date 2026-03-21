# FYP Autonomous Vehicle - Progress Log

**最后更新**: 2026-03-21

---

## 当前状态

**Corridor v1 室外验证通过。深度调研完成，已识别 5 个问题并确定修复方向。待出实施计划。**

| 项目 | 状态 |
|------|------|
| 方案 | 固定 Launch Pose 两点 corridor 自动导航 |
| 分支 | `gps`（Jetson 上也是 `gps`） |
| Jetson 部署 | 完成 |
| 首次室外验证 | 通过（到达目标附近，末端几米级误差） |
| 深度调研 | **完成（2026-03-21 下午）** |
| 实施计划 | **待出** |

---

## 最近完成 (2026-03-21 下午 — 调研 session)

- [x] 读取 L2 恢复上下文
- [x] SSH Jetson 检查仓库 + 硬件（IMU CH341 未检测到，其余 13/14 OK）
- [x] 用户提出架构级问题：GPS 漂移是否影响导航、目标点计算逻辑、多点路线扩展性
- [x] 深入读 corridor runner 代码 + launch 文件 + Nav2 配置，精确回答用户问题
- [x] 确认：当前 Nav2 全程用 SLAM 定位，GPS 只在启动时用一次做 sanity check
- [x] 派三路子代理并行调研：
  - PGO GPS 融合源码（pgo_node.cpp + simple_pgo.cpp）
  - Nav2 参数调优（DWB/costmap/controller 选型）
  - GPS→map 坐标转换完整链路
- [x] 汇总调研结果，识别 5 个问题（P0-P4 + P5）
- [x] 用户决策：P0 走路径 B（修复 PGO GPS 融合），控制器切 RPP

---

## 已识别问题汇总

### P0: map frame 与 ENU 不对齐（核心 blocker）

- PGO GPS 融合代码结构完整但功能无效
- 三个子问题：(1) topic `/gnss` vs `/fix` 错配 (2) ENU→map 无旋转估计 (3) 权重失衡（里程计比 GPS 强 1e4-1e6 倍）+ 首帧先验锁死 1e-12
- 用户选择：路径 B — 修复 PGO C++ 代码，加入旋转估计 + 权重平衡
- 影响：解决后 P1（终点精度）和 P5（多点路线）自动通

### P1: 终点精度不足（几米级误差）

- 根因：yaw0 不确定性（BMI088 无磁力计）
- 依赖 P0 解决

### P2: Nav2 路径折弯/卷团

- 根因：DWB RotateToGoal scale=300 + GoalAlign scale=300 + yaw_goal_tolerance=0.25rad
- 方案：切换到 Regulated Pure Pursuit (RPP) + Rotation Shim Controller
- 独立于 P0，可并行

### P3: 幻影障碍停车

- 根因：costmap 分辨率 0.02m + min_obstacle_height=-0.3（打到地面点）+ 无降噪层
- LiDAR 安装高度：t_il.z=0.04m，需确认离地绝对高度来精确设定 min_obstacle_height
- 方案：min_obstacle_height→0.15，分辨率→0.05，加 VoxelLayer + DenoiseLayer
- 独立于 P0，可并行

### P4: costmap 过重

- 全局 625 万格 + 局部 56 万格
- 方案：全局 0.10/30x30=9万格，局部 0.05/5x5=1万格
- 与 P3 一起改

### P5: 多点路线架构

- 当前 body_vector 只支持直线
- 发现 `gps_anchor_localizer_node` 已实现 GPS offset 逻辑（pyproj ENU + 锚点匹配）
- 用户想要的多点 GPS 路线方案：预采→offset→ENU→map→Nav2
- 前提：P0 解决（map 对齐 ENU）

---

## 关键代码发现

- PGO 源码：`src/perception/pgo_gps_fusion/src/pgo_node.cpp` (926行) + `pgos/simple_pgo.cpp`
- GPS→ENU：GeographicLib::LocalCartesian（精确 WGS84 椭球）
- GPS Factor：gtsam::GPSFactor（只约束平移，不约束旋转）
- 旧版 PGO（无 GPS）：`src/perception/pgo/`（package 名 `pgo_original`，未使用）
- 现有 GPS offset 实现：`src/sensor_drivers/gnss/gnss_calibration/gps_anchor_localizer_node.py`
- 它发布修正后的 `/gnss` → 正是 PGO 订阅的 topic

---

## Next Steps

1. 出完整实施计划（优先级排序 + 具体代码修改方案）
2. P0: 修复 PGO GPS 融合（C++ 代码修改 + 编译）
3. P2/P3/P4: Nav2 参数调优（YAML 配置修改）
4. P5: 基于 P0 成果设计多点 GPS 路线导航

---

## 历史摘要

2026-03-21 当天完成了从概念到实车验证的完整迭代：

1. 锁定"两点直线 GPS 导航"概念
2. 否决 v7，收敛为 launch 直启 corridor
3. Codex 部署到 Jetson + 室内 smoke
4. 首次室外验证通过
5. **下午：深度调研所有问题，完成 5 问题诊断 + 解决方案设计**

v7 scene graph 方案（分支 `feature/gps-route-ready-v2`）已废弃，不再作为开发主线。

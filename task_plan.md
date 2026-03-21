# Corridor v2 — GPS-aligned 多点导航升级计划

**Status**: `调研完成 / 待出实施计划`
**当前分支**: `gps`
**最后更新**: 2026-03-21

---

## 目标

将 corridor v1（body_vector 两点直线）升级为支持 GPS offset 多点路线导航，同时修复所有已知 Nav2 问题。

## 用户确定的方向

- P0: 路径 B — 修复 PGO GPS 融合 C++ 代码（加入 ENU→map 旋转估计 + 权重平衡）
- P2: 切换 Nav2 控制器到 Regulated Pure Pursuit (RPP)
- P3/P4: 修改 costmap 参数（分辨率、min_obstacle_height、降噪层）
- P5: 基于 P0 成果，实现多点 GPS 路线导航

## 待出实施计划的内容

下次 session 需要：

1. P0 的具体 C++ 修改方案（pgo_node.cpp + simple_pgo.cpp）:
   - ENU→map 旋转估计算法设计
   - 权重平衡策略
   - 首帧先验放松方案
   - 是否复用 `gps_anchor_localizer_node` 的 offset 逻辑

2. P2 的 RPP 控制器配置（完整 YAML）

3. P3/P4 的 costmap 配置（完整 YAML）:
   - 需要先确认 LiDAR 离地绝对高度（问用户或量测）
   - 据此确定 min_obstacle_height 精确值

4. P5 的多点路线 runner node 设计

5. 实施优先级和依赖关系排序

## 关键代码路径

| 文件 | 修改类型 |
|------|---------|
| `src/perception/pgo_gps_fusion/src/pgo_node.cpp` | P0: GPS 融合修复 |
| `src/perception/pgo_gps_fusion/src/pgos/simple_pgo.cpp` | P0: 权重 + 先验 |
| `src/bringup/config/nav2_explore.yaml` | P2/P3/P4: 控制器 + costmap |
| `src/bringup/config/master_params.yaml` | P0: GPS topic 修正 |
| `src/bringup/launch/system_gps_corridor.launch.py` | P0: 可能需要加入 anchor localizer |
| `src/navigation/gps_waypoint_dispatcher/...runner_node.py` | P5: 多点路线 runner |

## 已废弃方案（仅留索引）

| 方案 | 分支 | 废弃原因 |
|------|------|----------|
| v7 scene graph + route_server + Kabsch yaw | `feature/gps-route-ready-v2` | 对单 corridor 需求过重 |
| v6 整条 route 动态重算 | 同上 | frame 混用风险 |
| 旧 gnss_global_path_planner A* | 无独立分支 | 依赖旧路网 + 硬编码 angle |

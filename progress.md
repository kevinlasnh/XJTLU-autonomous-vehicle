# FYP Autonomous Vehicle - Progress Log

**最后更新**: 2026-03-22

---

## 当前状态

**Corridor v2 实施计划已完成，待用户审批。**

| 项目 | 状态 |
|------|------|
| Corridor v1 | 室外验证通过，作为 baseline 保留 |
| 深度调研 | 完成（5 问题诊断 + PGO 源码分析 + Nav2 调优研究 + GPS 管道验证）|
| 自审迭代 | 完成（算法验证 + 代码插入点确认 + 跳变风险评估）|
| 实施计划 | **完成，见 task_plan.md，待用户审批** |
| 当前分支 | `gps` |

---

## 最近完成 (2026-03-22)

### 调研 session（3月21日下午 — 3月22日早上，跨网络中断）

- [x] 读取 L2 恢复上下文
- [x] SSH Jetson 检查仓库 + 硬件（IMU CH341 未检测到，其余 13/14 OK）
- [x] 用户提出架构级问题讨论：
  - GPS 漂移是否影响导航 → 不影响，Nav2 全程用 SLAM
  - 目标点计算逻辑 → body_vector + yaw0，GPS 不参与目标计算
  - 多点路线扩展性 → body_vector 只支持直线，需新方案
  - 用户提出 GPS offset 方案 → 逻辑通，但缺 ENU→map 旋转
  - 导航中持续 GPS 修正 → 不应该，PGO GPS 融合才是正确做法
- [x] 三路并行子代理调研：
  1. PGO GPS 融合源码深度分析（pgo_node.cpp + simple_pgo.cpp）
  2. Nav2 参数调优（DWB/RPP/costmap/DenoiseLayer）
  3. GPS→map 坐标转换完整管道
- [x] 汇总：发现 PGO GPS 融合结构性缺陷（无旋转估计 + 权重失衡 + 首帧锁死）
- [x] 发现已有 `gps_anchor_localizer_node` 实现 GPS offset（但 corridor launch 未启用）
- [x] 用户决策：P0 走路径 B（修 PGO），控制器切 RPP
- [x] 网络中断恢复后，验证 Jetson 上 RPP/RotationShim/DenoiseLayer/VoxelLayer 全部已编译
- [x] 派代理验证 PGO 旋转估计算法可行性（代码行级确认）
- [x] 自审迭代通过：需求满足 + 架构正确 + 信息准确
- [x] 输出完整三阶段实施计划（task_plan.md）

---

## 实施计划摘要

| 阶段 | 内容 | 改动类型 | 优先级 |
|------|------|---------|--------|
| Phase 1 | P2/P3/P4: RPP控制器 + costmap优化 | YAML | 最高（立即可部署）|
| Phase 2 | P0: PGO GPS 融合修复（旋转估计+权重平衡）| C++ | 高（核心改动）|
| Phase 3 | P5: 多点 GPS 路线 Runner | Python | 中（依赖 Phase 2）|

详见 `task_plan.md`。

---

## 待用户确认

1. LiDAR 离地高度（影响 min_obstacle_height）
2. Phase 2 改 PGO C++ 代码的接受度
3. 是否先跑 Phase 1 验证
4. 多点路线的实际形状/长度需求

---

## 断点位置

**Step 14 完成（输出计划）→ 等待 Step 15（用户确认）**

下次 session：用户审阅 task_plan.md → 确认/修改 → 开始实施

---

## 历史摘要

2026-03-21：
1. 锁定"两点直线 GPS 导航"概念
2. 否决 v7，收敛为 launch 直启 corridor
3. Codex 部署到 Jetson + 室内 smoke
4. 首次室外验证通过

2026-03-21~22（本 session）：
5. 深度调研 5 个问题（P0-P4 + P5）
6. PGO 源码分析 + 算法设计
7. 完成 Corridor v2 三阶段实施计划

v7 scene graph 方案已废弃。

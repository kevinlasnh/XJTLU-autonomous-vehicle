# FYP Autonomous Vehicle - Progress Log

**最后更新**: 2026-03-22

---

## 当前状态

**Corridor v2 实施计划已完成 + 通过审计，待用户审批。**

| 项目 | 状态 |
|------|------|
| Corridor v1 | 室外验证通过，作为 baseline 保留 |
| 深度调研 | 完成 |
| 自审迭代 | 完成（含代码级审计，5 项修复） |
| 实施计划 | **完成 + 审计通过，见 task_plan.md，待用户审批** |
| 当前分支 | `gps` |

---

## 最近完成 (2026-03-22)

### 计划审计 & 修复

- [x] 派子代理对 task_plan.md 进行代码级审计（读 Nav2 源码验证参数名/存在性）
- [x] 发现并修复 5 个问题:
  1. **FAIL**: VoxelLayer origin_z=0.0 + min_obstacle_height=0.15 完全错误（基于 LiDAR 0.447m 安装高度计算，地面在 base_link z=-0.40m）→ 修正为 origin_z=-0.45, min_obstacle_height=-0.30
  2. **FAIL**: Global costmap 2D raytrace 会在近距离误清马路牙 → 修正 clearing: false
  3. **WARNING**: RotationShim 缺少 angular_disengage_threshold → 添加 0.39
  4. **WARNING**: PGO 旋转估计回环后 map_xy 过时 → 添加 pair refresh 说明
  5. **WARNING**: 风险表残留旧值 → 更新

### 之前完成的调研（3月21日下午 — 3月22日早上）

- [x] 用户架构级技术问题讨论（GPS 漂移、目标计算、多点扩展、持续 GPS 修正）
- [x] 三路并行调研（PGO 源码 + Nav2 调优 + GPS 管道）
- [x] PGO GPS 融合结构性缺陷确认（旋转缺失 + 权重失衡 + 首帧锁死）
- [x] 算法设计 + 代码插入点验证
- [x] RPP/RotationShim/DenoiseLayer/VoxelLayer 编译状态确认
- [x] LiDAR 安装高度查证（docs/hardware_spec.md: 0.447m）
- [x] 完整三阶段实施计划

---

## 实施计划摘要

| 阶段 | 内容 | 改动类型 |
|------|------|---------|
| Phase 1 | RPP控制器 + costmap优化（VoxelLayer + 正确高度参数）| YAML |
| Phase 2 | PGO GPS 融合修复（ENU→map 旋转估计 + 权重平衡）| C++ |
| Phase 3 | 多点 GPS 路线 Runner | Python |

详见 `task_plan.md`（已通过审计）。

---

## 断点位置

**Step 14 完成 + 审计通过 → 等待 Step 15（用户确认）**

---

## 历史摘要

2026-03-21: corridor v1 概念→实车验证完整迭代
2026-03-21~22: 深度调研 5 个问题 + PGO 源码分析 + 算法设计
2026-03-22: 实施计划完成 + 代码级审计 + 5 项修复

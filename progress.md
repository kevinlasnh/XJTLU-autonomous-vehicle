# FYP Autonomous Vehicle - Progress Log

**最后更新**: 2026-03-22

---

## 当前状态

**Corridor v2 计划已通过用户审批，交付 Codex 部署。CC 等待 Step 32 回来写文档。**

| 项目 | 状态 |
|------|------|
| Corridor v1 | 室外验证通过，作为 baseline 保留 |
| Corridor v2 计划 | **用户已审批** |
| 下一步 | Codex 从 Step 17 开始部署性审查 |
| CC 断点 | **Step 16 完成 → 等待 Step 32（用户喊回来写文档）** |
| 当前分支 | `gps` |

---

## 最近完成 (2026-03-22)

- [x] 深度调研 5 个问题（PGO 源码 + Nav2 调优 + GPS 管道）
- [x] 三轮自审迭代（算法验证 + 代码级审计 + 5 项 bug 修复）
- [x] costmap 参数基于实测 LiDAR 高度 0.447m 推导
- [x] 全量日志方案（ros2 bag record → ~/fyp_runtime_data/logs/）
- [x] WORKFLOW.md Step 29 日志读取标准流程
- [x] **Step 15: 用户审批通过**
- [x] **Step 16: L2 文件记录完成**

---

## Codex 需要知道的

1. **计划在 `task_plan.md`**，三个 Phase 按顺序实施
2. **Phase 1 可立即部署**（只改 YAML + launch），不动 C++ 代码
3. **Phase 2 改 PGO C++**，风险较高，建议增量修改逐步验证
4. **Phase 3 依赖 Phase 2 完成**
5. **所有 Nav2 插件（RPP/RotationShim/VoxelLayer）已在 Jetson 上编译确认**
6. **docs/hardware_spec.md 有完整硬件参数**（LiDAR 高度 0.447m 等）

---

## 历史摘要

2026-03-21: corridor v1 概念→实车验证完整迭代
2026-03-21~22: 深度调研 + 算法设计 + 计划编写 + 审计
2026-03-22: 用户审批通过，交付 Codex

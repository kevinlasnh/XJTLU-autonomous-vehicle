# FYP Autonomous Vehicle - Progress Log

**最后更新**: 2026-03-22

---

## 当前状态

**CC 复审完成。Bootstrap 方案 A 锁定。计划交还 Codex 部署。**

| 项目 | 状态 |
|------|------|
| Corridor v1 | 室外验证通过，作为 baseline 保留 |
| Corridor v2 计划 | **CC 复审完成，Bootstrap 方案 A 锁定** |
| 启动死锁 blocker | **已解决（固定 yaw bootstrap）** |
| 下一步 | **Codex 从 Step 19 继续部署性审查，确认后进入 Step 20 锁定** |
| 当前分支 | `gps` |

---

## 最近完成 (2026-03-22)

### CC 复审（针对 Codex 部署性审查发现）

- [x] 确认 Codex 发现 1-5（部署性补充）全部合理
- [x] 确认 Codex 发现 6（启动死锁）是真实 blocker
- [x] 调研 FAST-LIO2 yaw 初始化机制（imu_processor.cpp 源码分析）
- [x] 关键发现��yaw0 在相同物理放置下变化 < 0.1°（FromTwoVectors 确定性）
- [x] **裁决：采用方案 A（固定 yaw bootstrap），淘汰 10m 预热方案**
- [x] 更新 task_plan.md：Section 2.7 + 3.3 重写
- [x] 移除 startup_forward_prewarm_m 相关内容

### 之前完成

- [x] 深度调研 5 个问题 + PGO 源码分��� + 算法设计
- [x] 三轮自审迭代 + 代码级审计
- [x] 用户审批通过 → Codex 两轮部署性审查 → 发现启动死锁 → 交回 CC

---

## Codex 需要知道的

1. **启动死锁已解决**: Runner 用 `yaw0_from_TF - radians(launch_yaw_deg)` 在上电瞬间算出初始 ENU→map，无需等 PGO valid
2. **10m 预热方案已淘汰**: 数学上不需要，浪费距离和时间
3. **route YAML 的 launch_yaw_deg 是必填字段**: 对直线 corridor 可复用 bearing_deg
4. **Codex 发现 1-5 全部认可**: 已体现在更新后的 task_plan.md 中
5. **计划可进入 Step 20 锁定**

---

## 断点位置

**CC 复审完成 → Codex 从 Step 19 继续，确认后进入 Step 20 锁定**

---

## 历史摘要

2026-03-21: corridor v1 概念→实车验证
2026-03-21~22: 深度调研 + 算法设计 + 计划编写 + 审计
2026-03-22: 用户审批 → Codex 两轮审查（发现启动死锁）→ CC 复审（锁定方案 A bootstrap）

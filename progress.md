# FYP Autonomous Vehicle - Progress Log

**最后更新**: 2026-03-22

---

## 当前状态

**CC 复审完成。Codex 已完成 Bootstrap 方案 A 的二次部署性审查。Step 19 通过，等待用户进入 Step 20 锁定。**

| 项目 | 状态 |
|------|------|
| Corridor v1 | 室外验证通过，作为 baseline 保留 |
| Corridor v2 计划 | **CC 复审完成，Bootstrap 方案 A 锁定** |
| 启动死锁 blocker | **已解决（固定 yaw bootstrap）** |
| 下一步 | **等待用户确认 Step 20 锁定；确认后进入 Step 21 实施** |
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

### Codex 二次部署性审查（Bootstrap 方案 A）

- [x] 核对 FAST-LIO2: `gravity_align: true` 与 `imu_processor.cpp` 的 `FromTwoVectors` 代码路径存在
- [x] 核对启动 TF 链: FAST-LIO2 发布 `odom -> base_link`，PGO 发布 `map -> odom`，runner 读取 `map -> base_link` 的链路成立
- [x] 核对 Phase 3 包依赖: `gps_waypoint_dispatcher` 已声明 `python3-pyproj`
- [x] 发现并补充一个部署约束: `launch_yaw_deg` 不能在短首段上静默自动生成，采集脚本必须显式确认/必要时手填
- [x] 结论: **新计划可部署，Step 19 通过**

### 之前完成

- [x] 深度调研 5 个问题 + PGO 源码分��� + 算法设计
- [x] 三轮自审迭代 + 代码级审计
- [x] 用户审批通过 → Codex 两轮部署性审查 → 发现启动死锁 → 交回 CC

---

## Codex 需要知道的

1. **启动死锁已解决**: Runner 用 `yaw0_from_TF - radians(launch_yaw_deg)` 在上电瞬间算出初始 ENU→map，无需等 PGO valid
2. **10m 预热方案已淘汰**: 数学上不需要，浪费距离和时间
3. **route YAML 的 launch_yaw_deg 是必填字段**: 对直线 corridor 可复用 bearing_deg，但多点路线采集时必须显式确认
4. **Codex 发现 1-5 全部认可**: 已体现在更新后的 task_plan.md 中
5. **计划已通过 Codex 二次部署性审查，可进入 Step 20 锁定**

---

## 断点位置

**Step 19 已通过 → 等待用户确认进入 Step 20 锁定**

---

## 历史摘要

2026-03-21: corridor v1 概念→实车验证
2026-03-21~22: 深度调研 + 算法设计 + 计划编写 + 审计
2026-03-22: 用户审批 → Codex 两轮审查（发现启动死锁）→ CC 复审（锁定方案 A bootstrap）→ Codex 二次审查通过

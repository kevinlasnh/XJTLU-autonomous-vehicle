# FYP Autonomous Vehicle - Progress Log

**最后更新**: 2026-03-22

---

## 当前状态

**Corridor v2 已完成首轮部署与多次实车测试，并完成本轮文档更新。当前工作流已关闭，等待下一期从 Step 1 重新开始。**

| 项目 | 状态 |
|------|------|
| Corridor v1 | 室外验证通过，作为 baseline 保留 |
| Corridor v2 计划 | **已锁定并完成首轮部署** |
| 启动死锁 blocker | **已解决（固定 yaw bootstrap）** |
| 当前运行状态 | **可起跑，可推进到第一个 waypoint 的后段 subgoal** |
| 文档阶段 | **已完成（Step 33-38）** |
| 下一步 | **新一期工作流 Step 1: 继续攻 PGO 接管门槛 + costmap 微调** |
| 当前分支 | `gps` |

---

## 最近完成 (2026-03-22)

### CC 文档阶段（Step 33-38）

- [x] 读 L2 文件（git diff 看 Codex 更新）
- [x] 读 docs/index.md
- [x] 判断文档类型：无需新增，更新现有文档
- [x] 更新所有相关文档：
  - `devlog/2026-03.md`: 新增 corridor v2 部署与实车测试条目
  - `known_issues.md`: 更新 GPS RF 状态、costmap 残留新发现、新增 PGO handoff 和 controller/planner 掉频问题、更新 corridor v1→v2 状态
  - `knowledge/nav2_tuning.md`: 新增 corridor RPP 控制器参数、更新 costmap 参数与实车发现
  - `knowledge/gps_planning.md`: 更新当前状态、新增 corridor v2 架构与实车验证章节
  - `knowledge/pgo.md`: 更新 GPS topic `/gnss`→`/fix`、新增 corridor v2 ENU→map 对齐机制章节
  - `commands.md`: 新增 corridor quiet 模式说明
  - `index.md`: 更新日期与当前系统摘要
- [x] 调用 planning-with-files 记录进度
- [x] 准备 git commit + push

### Codex 部署与实车闭环

- [x] 完成 corridor v2 首轮代码部署到 `gps`
- [x] 完成 Jetson `pull + colcon build --packages-select gps_waypoint_dispatcher bringup --symlink-install --parallel-workers 1`
- [x] 完成 quiet corridor 前台监控，前台只显示简化状态
- [x] 完成多轮实车测试与日志回读
- [x] 当前已确认：系统能正常进入 `RUNNING_ROUTE`

### 最新 Step 29 分析结论

- [x] 最新实车 session `2026-03-22-15-16-00` 已推进到第一个 waypoint 的倒数第二个 subgoal
- [x] PGO 本轮已 ready，但 route runner 没有实际切换到 `pgo`，当前切换门槛对现场约 `~1Hz` 的更新频率仍然过严
- [x] Nav2 的绿色路径 `/plan` 确认由 planner 基于 global costmap 生成；local controller 再结合 local costmap 跟踪
- [x] 最新问题性质判断：**不是架构 blocker，而是 Step 21 小问题**
- [x] 用户结束本轮实车测试，当前进入会话收尾

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
5. **当前最新断点不是计划审查，而是运行期微调**
6. **不要再默认继续拉高 costmap 刷新率**：最新日志已经显示 controller/planner 掉频
7. **PGO 已能在运行中算出 valid ENU->map**，但 handoff gate 仍未和现场更新频率匹配

---

## 断点位置

**Step 29 已完成 → Step 30 已判断为“小问题” → 下次从 Step 21 继续改**

---

## 历史摘要

2026-03-21: corridor v1 概念→实车验证
2026-03-21~22: 深度调研 + 算法设计 + 计划编写 + 审计
2026-03-22: 用户审批 → Codex 两轮审查（发现启动死锁）→ CC 复审（锁定方案 A bootstrap）→ Codex 二次审查通过
2026-03-22: Codex 完成 corridor v2 首轮部署 → 多轮实车测试 → 问题收敛到 costmap / planner / controller / PGO handoff 微调

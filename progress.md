# FYP Autonomous Vehicle - Progress Log

**最后更新**: 2026-03-22

---

## 当前状态

**Corridor v2 已完成多轮部署与实车测试。架构调研已完成首轮收敛，当前断点为“独立 global aligner 方案已形成，等待锁定后进入新一轮 Step 21 实施”。**

| 项目 | 状态 |
|------|------|
| Corridor v1 | 室外验证通过，作为 baseline 保留 |
| Corridor v2 首轮部署 | **已完成** |
| 微调优化计划 | **已完成（Step 8-16）** |
| 优化方案 | **方案 B（经 Codex 微调后可部署）** |
| 当前工作流位置 | **Step 19 通过，等待 Step 20 锁定新方案** |
| 当前分支 | `gps` |

---

## 最近完成 (2026-03-22)

### CC 微调优化计划（Step 8-16）

- [x] 读取当前分支代码，理解系统现状
- [x] 加载 Superpowers skill
- [x] 审核用户需求：3 个微调问题（PGO 接管门槛、costmap 残留、频率掉频）
- [x] 派第一轮子代理调研（误分析了未启用节点）
- [x] 用户纠正：检查实际启用节点
- [x] 派第二轮子代理调研（分析实际运行节点）
- [x] 自审计划：发现 costmap raytrace 方案有高风险
- [x] 派多个子代理联网验证：
  - FAST-LIO2 参数优化（可行性：中等）
  - Costmap raytrace 优化（可行性：中低，建议用 STVL）
  - Controller 频率优化（可行性：高）
  - Jetson 20Hz 方案验证（可行性：低，推荐最高 5Hz）
- [x] 与用户讨论 Global Costmap 刷新率重要性
- [x] 用户确认方案 B（激进频率提升：Local 12Hz, Global 5Hz）
- [x] 输出完整优化计划（Step 14）
- [x] 用户确认计划（Step 15）
- [x] planning-with-files 记录进度（Step 16）

### Codex 部署性审查（方案 B）

- [x] 读取 CC 新方案及 L2 增量
- [x] 核对当前代码状态：PGO 门槛、Nav2 频率、BT 插件链
- [x] 核对 Jetson 运行环境：STVL 包当前未安装，但 apt 可用
- [x] 核对 Nav2 Humble 默认 BT：planner replan 仍是 `1Hz`
- [x] 发现部署缺口 1：`global_costmap 5Hz` 不能直接实现"绿色 /plan 更快"
- [x] 发现部署缺口 2：STVL 配置块不完整，且缺失安装前置步骤
- [x] 在不改变架构前提下补充部署约束：
  - `global_costmap 5Hz` 改为 staged rollout
  - STVL 补 apt install + 完整 MID360 参数块
- [x] 结论：**方案 B 经微调后可部署，Step 19 通过**

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

### 最新架构调研触发点（2026-03-22 Night）

- [x] 用户再次实测，确认：bootstrap 阶段车辆可较直地推进第一个 waypoint
- [x] 一旦切到 PGO，对齐源开始继续漂移，subgoal 链被重算，车辆出现回头/倒车 recovery
- [x] 已从日志确认：
  - 切换前：`1/1|41.70|-1.84|bootstrap`
  - 切换后：`1/2|46.13|-5.28|pgo`
  - `pgo_node` 在接管后仍持续 `alignment updated`
  - `serial_twistctl_node` 实际发出 `linear.x=-0.050`
- [x] 用户要求 Codex 暂代 CC，深度调研"GPS 是否还应继续融合进 PGO，还是改成独立 global aligner"

### 最新架构调研结论（2026-03-22 Night）

- [x] 已基于最新日志、当前代码和官方资料完成首轮架构调研
- [x] 结论不是"去掉 GPS"，而是：
  - GPS 仍应参与全局纠偏
  - 但不应继续以当前这种 live PGO handoff 方式直接进入 corridor 控制闭环
- [x] 已确认当前更合理方向：
  - 保留 FAST-LIO2 作为局部连续里程计主链
  - 引入独立 `global_aligner`，平滑发布 `ENU -> map`
  - runner 继续消费 `alignment_topic`
  - 不在当前 subgoal 中途因对齐源变化而重算已执行进度
- [x] 已确认"整包替换成另一套 GPS 紧耦合 SLAM"当前并非低风险方案
  - 官方 LIO-SAM 与当前 ROS2 Humble + MID360 栈不构成低成本 drop-in replacement
  - 若要尽量复用现成件，更接近正确方向的是 `robot_localization + navsat_transform` 这类分层全局定位模块
- [x] 已形成首轮可部署方案：
  - 新增 `gps_global_aligner_node`
  - corridor 模式下关闭 `pgo.gps.enable`
  - route runner 改成消费稳定 alignment，不再做 live PGO handoff
  - route runner 保持 ENU 域进度，不在 alignment 更新时回跳 subgoal

### CC 复审（针对 Codex 部署性审查发现）

- [x] 确认 Codex 发现 1-5（部署性补充）全部合理
- [x] 确认 Codex 发现 6（启动死锁）是真实 blocker
- [x] 调研 FAST-LIO2 yaw 初始化机制（imu_processor.cpp 源码分析）
- [x] 关键发现：yaw0 在相同物理放置下变化 < 0.1°（FromTwoVectors 确定性）
- [x] **裁决：采用方案 A（固定 yaw bootstrap），淘汰 10m 预热方案**
- [x] 更新 task_plan.md：Section 2.7 + 3.3 重写
- [x] 移除 startup_forward_prewarm_m 相关内容

### Codex 二次部署性审查（Bootstrap 方案 A）

- [x] 核对 FAST-LIO2: `gravity_align: true` 与 `imu_processor.cpp` 的 `FromTwoVectors` 代码路径存在
- [x] 核对启动 TF 链: FAST-LIO2 发布 `odom -> base_link`，PGO 发布 `map -> odom`，runner 读取 `map -> base_link` 的链路成立
- [x] 核对 Phase 3 包依赖: `gps_waypoint_dispatcher` 已声明 `python3-pyproj`
- [x] 发现并补充一个部署约束: `launch_yaw_deg` 不能在短首段上静默自动生成，采集脚本必须显式确认/必要时手填
- [x] 结论: **新计划可部署，Step 19 通过**

### 独立 Global Aligner 架构部署与实车验证

- [x] commit `e51a46a`: 新增 `gps_global_aligner_node.py`
- [x] commit `7d77f10`: 冻结 waypoint 内 alignment，扩大 costmap 窗口
- [x] commit `3f66c5a`: 收紧 aligner 更新限速，平滑 waypoint 边界切换
- [x] commit `2bb6fbf`: 修复 runtime 清理链，补杀残留进程
- [x] session `2026-03-22-21-05-17`: **waypoint 1 已稳定到达**
- [x] 架构改进生效：从"无法起跑"推进到"waypoint 1 完成"

### 文档更新（2026-03-23）

- [x] 更新 `devlog/2026-03.md`: 补充独立 global aligner 架构部署与实车验证
- [x] 更新 `known_issues.md`: 更新 costmap 问题状态，记录 waypoint 1 到达
- [x] 更新 `knowledge/gps_planning.md`: 更新 corridor v2 架构描述
- [x] 更新 `docs/index.md`: 更新日期到 2026-03-23
- [x] 更新 L2 进度文件

### 之前完成

- [x] 深度调研 5 个问题 + PGO 源码分析 + 算法设计
- [x] 三轮自审迭代 + 代码级审计
- [x] 用户审批通过 → Codex 两轮部署性审查 → 发现启动死锁 → 交回 CC

### CC 微调优化计划（Step 8-16）

- [x] 读取当前分支代码，理解系统现状
- [x] 加载 Superpowers skill
- [x] 审核用户需求：3 个微调问题（PGO 接管门槛、costmap 残留、频率掉频）
- [x] 派第一轮子代理调研（误分析了未启用节点）
- [x] 用户纠正：检查实际启用节点
- [x] 派第二轮子代理调研（分析实际运行节点）
- [x] 自审计划：发现 costmap raytrace 方案有高风险
- [x] 派多个子代理联网验证：
  - FAST-LIO2 参数优化（可行性：中等）
  - Costmap raytrace 优化（可行性：中低，建议用 STVL）
  - Controller 频率优化（可行性：高）
  - Jetson 20Hz 方案验证（可行性：低，推荐最高 5Hz）
- [x] 与用户讨论 Global Costmap 刷新率重要性
- [x] 用户确认方案 B（激进频率提升：Local 12Hz, Global 5Hz）
- [x] 输出完整优化计划（Step 14）
- [x] 用户确认计划（Step 15）
- [x] planning-with-files 记录进度（Step 16）

### Codex 部署性审查（方案 B）

- [x] 读取 CC 新方案及 L2 增量
- [x] 核对当前代码状态：PGO 门槛、Nav2 频率、BT 插件链
- [x] 核对 Jetson 运行环境：STVL 包当前未安装，但 apt 可用
- [x] 核对 Nav2 Humble 默认 BT：planner replan 仍是 `1Hz`
- [x] 发现部署缺口 1：`global_costmap 5Hz` 不能直接实现“绿色 /plan 更快”
- [x] 发现部署缺口 2：STVL 配置块不完整，且缺失安装前置步骤
- [x] 在不改变架构前提下补充部署约束：
  - `global_costmap 5Hz` 改为 staged rollout
  - STVL 补 apt install + 完整 MID360 参数块
- [x] 结论：**方案 B 经微调后可部署，Step 19 通过**

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

### 最新架构调研触发点（2026-03-22 Night）

- [x] 用户再次实测，确认：bootstrap 阶段车辆可较直地推进第一个 waypoint
- [x] 一旦切到 PGO，对齐源开始继续漂移，subgoal 链被重算，车辆出现回头/倒车 recovery
- [x] 已从日志确认：
  - 切换前：`1/1|41.70|-1.84|bootstrap`
  - 切换后：`1/2|46.13|-5.28|pgo`
  - `pgo_node` 在接管后仍持续 `alignment updated`
  - `serial_twistctl_node` 实际发出 `linear.x=-0.050`
- [x] 用户要求 Codex 暂代 CC，深度调研“GPS 是否还应继续融合进 PGO，还是改成独立 global aligner”

### 最新架构调研结论（2026-03-22 Night）

- [x] 已基于最新日志、当前代码和官方资料完成首轮架构调研
- [x] 结论不是“去掉 GPS”，而是：
  - GPS 仍应参与全局纠偏
  - 但不应继续以当前这种 live PGO handoff 方式直接进入 corridor 控制闭环
- [x] 已确认当前更合理方向：
  - 保留 FAST-LIO2 作为局部连续里程计主链
  - 引入独立 `global_aligner`，平滑发布 `ENU -> map`
  - runner 继续消费 `alignment_topic`
  - 不在当前 subgoal 中途因对齐源变化而重算已执行进度
- [x] 已确认“整包替换成另一套 GPS 紧耦合 SLAM”当前并非低风险方案
  - 官方 LIO-SAM 与当前 ROS2 Humble + MID360 栈不构成低成本 drop-in replacement
  - 若要尽量复用现成件，更接近正确方向的是 `robot_localization + navsat_transform` 这类分层全局定位模块
- [x] 已形成首轮可部署方案：
  - 新增 `gps_global_aligner_node`
  - corridor 模式下关闭 `pgo.gps.enable`
  - route runner 改成消费稳定 alignment，不再做 live PGO handoff
  - route runner 保持 ENU 域进度，不在 alignment 更新时回跳 subgoal

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
8. **最新问题已不再只是调参**：PGO 接管后 runner 会重算剩余 subgoal，且 `map->odom` 在接管后仍继续漂移
9. **当前新断点是架构调研**：评估 `GPS-in-PGO` 与“独立 global aligner + runner 消费 `ENU->map`”两条路径
10. **架构调研已有首轮结论**：推荐方向是“保留 FAST-LIO2，拆出独立 global aligner”，而不是继续强化当前 live PGO handoff
11. **若用户要求尽量用现成包**：优先考虑 `robot_localization/navsat_transform` 作为全局对齐模块骨架，而不是直接整包换 SLAM
12. **新方案的最大实现风险不在定位数学，而在 runner 进度语义**：必须避免 alignment 更新时重切当前剩余 subgoal 链

---

## 断点位置

**Step 19 已通过 → 等待用户 Step 20 锁定“独立 global aligner”方案 → 锁定后从 Step 21 开始新一轮实现**

---

## 优化方案 B 摘要

### Phase 1（锁定后首轮部署）
1. PGO 接管门槛：`pgo_switch_min_stable_updates: 3`（从 4 降到 3）
2. Costmap 频率：Local 12Hz（从 10），Global 3Hz（首轮），5Hz 作为二轮实验值
3. STVL 障碍清除：需先安装 `ros-humble-spatio-temporal-voxel-layer`，并补完整 MID360 参数
4. Controller：保持 20Hz

### Phase 2（可选）
5. FAST-LIO2：`det_range: 55.0`（从 60）
6. PGO 回环：`loop_search_radius: 1.5`（从 1.0）

### 风险与回退
- Phase 1.2 有中高风险（Jetson 可能掉频）
- 回退方案：Local 10Hz / Global 3Hz

---

## 历史摘要

2026-03-21: corridor v1 概念→实车验证
2026-03-21~22: 深度调研 + 算法设计 + 计划编写 + 审计
2026-03-22: 用户审批 → Codex 两轮审查（发现启动死锁）→ CC 复审（锁定方案 A bootstrap）→ Codex 二次审查通过
2026-03-22: Codex 完成 corridor v2 首轮部署 → 多轮实车测试 → 问题收敛到 costmap / planner / controller / PGO handoff 微调
2026-03-22 晚: 独立 global aligner 架构已部署；最新实车已首次完整到达 waypoint 1，并开始执行 waypoint 2；当前问题后移到 waypoint 2 边界 alignment 漂移 + Nav2 stop-go

---

## 最新运行断点（2026-03-22 21:05 session）

- session: `/home/jetson/fyp_runtime_data/logs/2026-03-22-21-05-17/`
- 已确认：
  - waypoint 1 已到达
  - runner 进入 `WAYPOINT_TARGET|2|2|right-bottom-corner`
  - 第二个 waypoint 开始即发送 `subgoal 3/7`，且 `progress=16.51/49.21`
- 当前判断：
  - 第二段一开始就“已经走了 16.5m”不合理，说明 waypoint 边界冻结到的 alignment 已偏
  - stop-go 主因是 controller `collision ahead` + TF future extrapolation，不是电机硬件
- 下一轮优先级：
  1. 收紧/限幅 global aligner 在 waypoint 边界的漂移，避免第二段起始投影跳入建筑或跳过前两个 subgoal
  2. 只通过 Nav2 参数微调提升平顺性：降低误触发 collision ahead，减少 future extrapolation 对 controller 的扰动

---

## 工作流收口断点（2026-03-22 夜）

- 已完成：
  - `3f66c5a`：收紧 global aligner + waypoint 边界 guard + Nav2 平顺性微调
  - `2bb6fbf`：修复 runtime 清理链，补杀 `gps_global_aligner`，并在每次 corridor 启动前预清理残留节点
- 已确认根因：
  - “一启动直接 SUCCEEDED” 主要由旧 `gps_global_aligner` 残留进程污染新一轮 runner 引起
  - RViz 偶发空白更像该残留 bug 的连带现象，不是 RViz 自身启动失败
- 当前阻塞：
  - Jetson SSH 暂时超时，尚未完成 `2bb6fbf` 的现场 pull、残留进程清理和复验
- 下次恢复工作流时的首步：
  1. Jetson `git pull --ff-only origin gps`
  2. `make kill-runtime`
  3. 重新实车测试 corridor
  4. 重点复核“第一段持续右偏”和“第二段仍朝建筑偏”是否在干净运行环境下依然存在

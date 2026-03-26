# GPS 全局导航与场景路网

## 1. 当前状态（2026-03-22）

当前 GPS 导航有两条并行链路：

1. **Scene-graph 路网导航**（`feature/gps-route-ready-v2` 分支）
   - 使用 `scene_gps_bundle.yaml` + `gps_anchor_localizer` + `route_server`
   - 当前被 PGO 段错误阻塞（known_issues #1）
   - 软件链已通，实车未通过

2. **Fixed-launch GPS corridor**（`gps` 分支，当前主开发线）
   - 使用 `collect_gps_route.py` 采集多点路线
   - **独立 global aligner 架构**（commit `e51a46a`~`2bb6fbf`）
   - `gps_global_aligner_node` 平滑发布 `ENU->map` 变换
   - `gps_route_runner_node` 消费稳定 alignment，冻结 waypoint 内进度
   - **waypoint 1 已稳定到达**（session `2026-03-22-21-05-17`）
   - 当前问题：waypoint 边界 alignment 漂移 + Nav2 平顺性微调

## 2. Source Of Truth 与运行时产物

### 2.1 唯一 source of truth

- `~/fyp_runtime_data/gnss/scene_gps_bundle.yaml`

该文件同时保存：
- `scene_name`
- `fixed_origin_node_id`
- `nodes`
- `edges`
- `anchor`
- `dest`

### 2.2 运行时编译产物

采图完成后运行：

```bash
python3 scripts/build_scene_runtime.py
```

生成：
- `~/fyp_runtime_data/gnss/current_scene/master_params_scene.yaml`
- `~/fyp_runtime_data/gnss/current_scene/scene_points.yaml`
- `~/fyp_runtime_data/gnss/current_scene/scene_route_graph.geojson`

这些文件分别服务于：
- PGO fixed origin
- `gps_anchor_localizer`
- `gps_waypoint_dispatcher`
- `route_server`

## 3. 启动定位链

### 3.1 `gps_anchor_localizer`

输入：
- `/fix`
- `scene_points.yaml`

输出：
- `/gnss`
- `/gps_system/status`
- `/gps_system/nearest_anchor`
- `/gps_system/nearest_anchor_id`

状态机：
- `NO_FIX`
- `UNSTABLE_FIX`
- `NO_ANCHOR`
- `AMBIGUOUS_ANCHOR`
- `GNSS_READY`
- `NAV_READY`

锁定逻辑：
1. 启动阶段收集 10 个稳定 `/fix` 样本
2. 仅在 spread `<= 2.0m` 且水平 sigma `<= 6.0m` 时继续
3. 在 `scene_points.yaml` 里匹配最近 `anchor`
4. 仅当最近 anchor 距离 `<= 8.0m` 且与第二近 anchor 的差值 `> 3.0m` 时，锁定该 anchor
5. 用该 anchor 计算 session ENU offset
6. 持续发布校正后的 `/gnss`
7. 当 `/gnss -> map` 与 `base_link` 的残差 `<= 4.0m`，并连续满足 3 个样本后，升为 `NAV_READY`

关键语义：
- 系统不再依赖 `startid.txt`
- 也不再依赖旧 `gnss_offset.txt`
- 只有在附近存在已知 `anchor` 时，系统才 ready

## 4. 目标管理与图导航

### 4.1 `gps_waypoint_dispatcher` 的新职责

当前 `gps_waypoint_dispatcher` 已不再自己做 Dijkstra，也不再发 `FollowWaypoints`。

它现在是 goal manager，负责：
- 读取英文目标名
- 列出可选 destination
- 检查 `NAV_READY`
- 读取 startup anchor
- 两阶段动作编排
- `stop`

### 4.2 两阶段动作

Stage A:
- 若当前 `map` 位姿距离 startup anchor 大于 `2.5m`
- 先调用 `navigate_to_pose` 回到该 anchor

Stage B:
- 调用 `ComputeRoute(start_id=anchor_id, goal_id=dest_id)`
- 接收 `route_server` 返回的 dense path
- 再调用 `/follow_path`

输入接口：
- `ros2 run gps_waypoint_dispatcher list_destinations`
- `ros2 run gps_waypoint_dispatcher goto_name <english_name>`
- `ros2 run gps_waypoint_dispatcher stop`

## 5. Route Graph 语义

### 5.1 图文件

- `scene_route_graph.geojson`

由 `build_scene_runtime.py` 从 scene bundle 自动生成。

### 5.2 图边语义

- 每条 edge 按节点间直线段解释
- 转弯和弯道必须靠增加节点离散化
- 不依赖“edge 自带弯曲几何”

### 5.3 局部避障语义

全局路径必须尽可能沿 graph edge 执行，但中间局部行为仍由 Nav2 + LiDAR 完成：

- 无障碍时：尽量贴着 path 直线段走
- 有静态或动态障碍时：允许安全绕开
- 绕开后：尽量回到原 path

这正是当前 `nav2_gps.yaml` 中 DWB critic 权重的预期行为。

## 6. 采图脚本

### 6.1 `collect_gps_scene.py`

现场用户只需要运行：

```bash
python3 scripts/collect_gps_scene.py
```

特性：
- 只使用 `/fix`
- 10 样本平均
- 2m spread 检查
- 自动保存 scene bundle
- 支持：
  - 新增点
  - 改英文名
  - 标记 `anchor`
  - 标记 `dest`
  - 设 fixed origin
  - 添加 / 删除边
  - 删除节点
  - 列表查看

### 6.2 布点规则

- 所有转弯、路口、岔路都必须踩点
- 所有目标入口必须踩点
- 需要允许系统启动的区域附近必须有 `anchor`
- `anchor` 建议间距不小于 15m

## 7. 已完成的软件验证

### 7.1 构建验证

已完成：
- `gnss_calibration`
- `gps_waypoint_dispatcher`
- `bringup`

构建命令统一为：

```bash
colcon build --packages-select <pkg> --symlink-install --parallel-workers 1
source install/setup.bash
```

### 7.2 室内 smoke

已确认：
- `build_scene_runtime.py` 能从 sample bundle 生成 3 个运行时文件
- `list_destinations` 能读取编译产物
- `gps_anchor_localizer` 能从 mock `/fix` 进入 `GNSS_READY -> NAV_READY`
- 在引入 session offset 后，localizer 能锁定 startup anchor 并发布校正 `/gnss`
- `compute_route` / `follow_path` / `navigate_to_pose` action 均在线
- goal manager 室内链路已到达：
  - `COMPUTING_ROUTE`
  - `FOLLOWING_ROUTE`
  - `SUCCEEDED`

## 8. 2026-03-20 首轮真实场景验证结论

用户已经采集真实 `ls-building` scene，并完成 `build_scene_runtime.py` 编译；`nav_gps_menu.py` 也已在车上进入真实使用。

现场确认：
- `nav_gps_menu.py` 可以自动拉起 `nav-gps`
- `gps_system` 可以正常到达 `NAV_READY`
- 菜单可以列出 destination 并按编号发送目标
- 选择真实目标 `2 -> ls-right-bottom-corner` 后，goal manager 会到达：
  - `GOAL_REQUESTED`
  - `COMPUTING_ROUTE`
  - `FOLLOWING_ROUTE`

但当前实车执行仍然失败：
- 最终状态：
  - `FAILED; follow_path_status=6`
- 直接根因：
  - `pgo_node` 在执行期间 `exit code -11`
  - `map -> odom` TF 消失
  - Nav2 controller 随后报 `Controller patience exceeded`

因此当前链路已经证明：
- 启动定位链是通的
- 目标输入链是通的
- graph routing 链是通的
- 当前 blocker 是 PGO 稳定性，不是 GPS 路网菜单或 route server 本身

## 9. 当前边界

1. 这套链路已经可部署，但真实 scene bundle 仍需要现场采图
2. “任意位置上电”在工程上等价于：
   - 位于已覆盖场景内
   - 且附近存在已知 `anchor`
3. 如果当前点附近没有合法 `anchor`，系统必须保持 `NO_ANCHOR` 或 `AMBIGUOUS_ANCHOR`
4. 这不是 RTK 方案，GPS 绝对精度仍受环境影响；scene anchor 解决的是启动收口，不是全域厘米级定位

## 10. 下一步实车流程

1. 继续定位并修复 `pgo_node` 段错误
2. 优先恢复稳定的 `map -> odom` 与 `/pgo/optimized_odom`
3. 复测 `nav_gps_menu.py`
4. 再次在真实 scene 上验证：
   - `NAV_READY`
   - `FOLLOWING_ROUTE`
   - 到点成功


## 11. Fixed-Launch Two-Point Corridor

### 11.1 适用场景

这条链路只解决最小问题：
- 固定 Launch Pose
- 固定启动朝向
- 一个固定终点
- 中间自动切段
- 一次只给 Nav2 一个小目标

### 11.2 为什么不用旧 scene graph 主链

因为当前任务不是“任意位置上电 + GPS 图路网导航”，而是“先验证固定 corridor 能不能稳定跑通”。

因此：
- scene graph / route_server 过重
- menu / destination 输入不是必须
- 最合理的做法是直接在当前 `map` 下生成一条 corridor

### 11.3 运行逻辑

1. 预采两点：
   - `start_ref`
   - `goal_ref`
2. 采集脚本自动写出：
   - `distance_m`
   - `bearing_deg`
   - `body_vector_m`
3. corridor runner 启动后：
   - 等待稳定 `/fix`
   - 检查当前启动点是否在 `startup_gps_tolerance_m` 内
   - 读取当前 `map -> base_link`
   - 用 `body_vector_m` 生成 `goal_map`
   - 将 corridor 按 `segment_length_m`（默认 30m，基于 global costmap 半径 35m - 5m buffer）切成多个 subgoals
   - 串行执行 `NavigateToPose`

### 11.4 当前 v1 约束

- v1 不计算全局 scene 对齐
- v1 不计算 route graph
- v1 不推导任意目标名
- v1 默认 corridor 在车辆启动朝向正前方

也就是：
- `body_vector_m.x = distance_m`
- `body_vector_m.y = 0`

### 11.5 当前 smoke 结论

截至 2026-03-21：
- corridor runner 已能在 launch 中自动拉起
- 能正确读取 corridor YAML
- 能进入 `WAITING_FOR_STABLE_FIX`
- 在无有效 GNSS fix 时会超时 abort，不动车

这说明当前 corridor 链的关键控制流已经打通，剩余验证转为现场真实 `/fix` 与实车走廊测试。


## 12. Corridor v2 独立 Global Aligner 架构（2026-03-22~24）

### 12.1 设计目标

Corridor v2 解决 v1 的核心问题：
- v1 用 body_vector 直线导航，受 yaw0 不确定性影响终点偏差 ~4m
- v2 初版尝试 PGO ENU→map 对齐，但实车发现 PGO live handoff 在运行中继续漂移，导致 subgoal 重算和 recovery
- **v2 最终版引入独立 `gps_global_aligner_node`，与 PGO 解耦，平滑发布 `ENU→map` 变换**

### 12.2 核心机制

**Bootstrap 启动对齐**:
- 车辆上电后从 TF 读取 `map->base_link` 的 yaw0
- 用 route YAML 的 `launch_yaw_deg`（车的地理朝向）计算初始 ENU→map 旋转
- 公式: `θ_bootstrap = yaw0 - radians(launch_yaw_deg)`
- 立即开始导航，不等 GPS stable fix 之外的任何额外条件

**独立 Global Aligner**:
- `gps_global_aligner_node` 持续采集 GPS→ENU 与 map→base_link 配对
- 在线估计平滑 `ENU→map` 刚体变换（旋转+平移）
- 输出到 `/gps_corridor/enu_to_map`
- 对估算结果做**限速与平滑**，防止跳变
- 不依赖 PGO 的 live 图优化结果

**Waypoint 内冻结 alignment**:
- Runner 在进入一个 waypoint 后，冻结当前 alignment
- 不在 subgoal 执行中途因 alignment 更新而重算已执行进度
- 仅在 waypoint 边界才吸收新 alignment

### 12.3 运行期微调（2026-03-23~26）

v2 部署后经多轮实车微调收敛：

| 参数 | 初始值 | 最���收口值 | 理由 |
|------|--------|-----------|------|
| `max_allowed_time_to_collision` | 0.6 | **0.30** | 更早触发平滑减速（配合 cost-regulated scaling） |
| `use_cost_regulated_linear_velocity_scaling` | false | **true** | 靠近障碍平滑减速，替代二元急停 |
| local `denoise_layer.minimal_group_size` | 3 | **4** | 抑制孤立噪声点 |
| `waypoint_start_progress_guard_m` | 10.0 | **5.0** | GPS 2-sigma ~5m |
| global STVL `transform_tolerance` | 0.35 | **0.5** | 与 local 一致 |
| STVL `clear_after_reading` | true | **false** | 障碍由 voxel_decay 管理，不再每周期清空 |
| global `cost_scaling_factor` | 2.0 | **1.0** | 推开绿色路径离障碍边缘 |
| global `inflation_radius` | 0.75 | **0.95** | 安全余量增大 |
| `max_bootstrap_translation_delta_m` | 15.0 | **8.0** | 拒绝偏差过大的 raw GPS alignment |
| `waypoint_alignment_translation_guard_m` | (新增) | **3.0** | waypoint 边界处 alignment 跳变守卫 |
| `waypoint_alignment_theta_guard_deg` | (新增) | **2.0** | waypoint 边界处 alignment 旋转守卫 |

### 12.4 实车验证结论（2026-03-26 收口）

**已验证成立**:
- 独立 global aligner 架构从”无法起跑”推进到 waypoint 1 完成
- waypoint 边界 alignment 守卫已生效：第二段不再换坏 alignment（session `2026-03-26-15-27-19`）
- BT override 已修复：corridor BT 现在正确加载（commit `d075c6b`）
- STVL `clear_after_reading: false` 解决了障碍每周期清空的问题

**当前主瓶颈 — GPS 路线锚定方法**:
- startup GPS 锚定带 ~2.5m 系统误差（`distance_to_start_ref=2.48m`）
- 第二段目标线在 map 中本身就带右偏分量（dx=+1.81m），不是运行时跳点
- 继续调 Nav2 YAML 或小修 runner 无法���决”稳定到预定物理位置”的目标
- 候选重设计方向：
  1. 多点刚体配准替代单点 `start_ref`
  2. 路线改为 `map` 物理点位，GPS 只负责启动定位
  3. 连续轨迹采集 + 中心线/拐角拟合

### 12.5 与 v1 对比

| | Corridor v1 | Corridor v2 |
|--|-------------|-------------|
| 路点坐标系 | body_vector（车体前方） | GPS→ENU→map（独立 aligner） |
| 启动对齐 | 无 | 固定 yaw bootstrap |
| 运行对齐 | 无 | 独立 global aligner（平滑） |
| 对齐更新方式 | N/A | waypoint 内冻结，边界吸收 |
| 终点精度 | ~4m（受 yaw0 影响） | 理论更高（取决于 aligner 质量） |
| PGO 角色 | 提供 map→odom | 仅 loop closure，不参与 corridor 对齐 |
| 实车状态 | baseline 保留 | 已部署，Nav2 调参已收口，主瓶颈转移到 GPS 锚定方法 |

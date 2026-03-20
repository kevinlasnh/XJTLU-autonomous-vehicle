# GPS 全局导航与场景路网

## 1. 当前状态（2026-03-20）

当前 GPS 导航已经从旧的 `v4` 路网 dispatcher 升级为新的 scene-graph 架构：

1. `make launch-explore-gps`
   - 继续负责 `GNSS -> /gnss -> PGO GPS Factor`
   - 主要用途是 Explore 模式下的全局约束
2. `make launch-nav-gps`
   - 使用 `scene_gps_bundle.yaml`
   - 上电后由 `gps_anchor_localizer` 检查附近已知 `anchor`
   - 进入 `NAV_READY` 后只接受英文目标名
   - 通过 `route_server + FollowPath` 沿 GPS 图边线导航

这条链当前已经在 `feature/gps-route-ready-v2` 上完成软件部署和室内 smoke，真实场景还需要用户用新采图脚本采集一份 scene bundle。

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

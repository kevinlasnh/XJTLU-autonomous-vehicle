# GPS 全局导航与路网规划

## 1. 当前状态（2026-03-20）

当前 GPS 导航实现分成两层：

1. `make launch-explore-gps`
   - GNSS 校准后的 `/gnss` 注入 PGO GPS 因子
   - 负责提升 `map -> odom` 的全局一致性
2. `make launch-nav-gps`
   - 目前在 `feature/gps-navigation-v4` 上完成软件部署
   - 负责把 GPS 目标转换成 Nav2 `FollowWaypoints` 执行链
   - 已完成室内软件 smoke，室外实车验证待做

这意味着当前仓库已经不只是 `GNSS -> PGO GPS 因子` 这条链；GPS 目标导航的主软件链也已经搭起来，但还没有通过最终室外验证。

## 2. 锁定的数据契约

### 2.1 当前位姿源

- `gnss_calibration` 内部输入: `/fix`
- 系统可用的当前 GNSS 位姿: `/gnss`
- `gps_waypoint_dispatcher` 只订阅 `/gnss`
- 路网采集脚本也只使用 `/gnss`

`/fix` 不再参与路网起点吸附，也不作为最终路网坐标源。

### 2.2 固定 ENU 原点

PGO 与 dispatcher 从 `master_params.yaml` 读取同一固定 ENU 原点：

- `gps.origin_mode = fixed`
- `gps.origin_lat = 31.274927`
- `gps.origin_lon = 120.737548`
- `gps.origin_alt = 0.0`

这样做的目的：
- 不依赖系统启动时的第一条 GPS
- 每次启动的 map 坐标系一致
- 路网点、PGO、dispatcher 三者共享同一坐标参考

### 2.3 路网 source of truth

- 唯一 source of truth: `src/navigation/gps_waypoint_dispatcher/config/campus_road_network.yaml`
- `goto_name` 从这个文件的 `dest: true` 节点列表里选目的地
- `goto_latlon` / `/gps_goal` 只保留为调试直达模式
- `allow_direct_fallback` 默认关闭，不让“没图时直线冲过去”成为默认行为

## 3. 已实现的软件组件

### 3.1 `gnss_calibration`

- 校准点从 `config/calibration_points.yaml` 外置读取
- 运行前置明确依赖：
  - `~/fyp_runtime_data/gnss/startid.txt`
  - 有效的 `gnss_offset.txt`
- offset 不存在或无效时，不再假装 `/gnss` 可用

### 3.2 `nav2_gps.yaml`

GPS 专用 Nav2 配置基于 `nav2_explore.yaml` 派生，只改最小必要参数：

- `movement_time_allowance = 10.0`
- `xy_goal_tolerance = 3.0`
- `yaw_goal_tolerance = 0.5`
- `GridBased.tolerance = 2.5`
- `GridBased.use_astar = true`
- `BaseObstacle.scale = 0.02`
- `GoalAlign.scale = 24.0`
- `RotateToGoal.scale = 32.0`

Explore 主模式参数没有被这个分支顺手改掉。

### 3.3 `gps_waypoint_dispatcher`

新包路径: `src/navigation/gps_waypoint_dispatcher/`

能力：
- 订阅 `/gnss` 作为当前位姿
- 订阅 `/gps_goal` 处理调试直达模式
- 通过 `goto_name` 走路网模式
- 支持 `stop` 取消当前 `FollowWaypoints` 任务
- 发布调试用 `/gps_waypoint_dispatcher/goal_map` 与 `/gps_waypoint_dispatcher/path_map`

路网模式的关键行为：
- 读取 `campus_road_network.yaml`
- 用 nearest-edge projection + 虚拟起点处理当前位姿吸附
- 在路网上做 Dijkstra
- 把结果转成 map 帧 waypoint 后调用 `FollowWaypoints`

### 3.4 GPS 点位采集脚本 v2

`scripts/collect_gps_points.py` 当前行为：
- `/gnss` only
- 10 样本平均
- 2m 散布检查
- 输出 ID-keyed YAML

输出文件: `~/fyp_runtime_data/gnss/collected_points.yaml`

采集后复制到：
`src/navigation/gps_waypoint_dispatcher/config/campus_road_network.yaml`

## 4. 已完成的软件验证

### 4.1 构建验证

已完成以下包构建：
- `gnss_calibration`
- `bringup`
- `pgo`
- `gps_waypoint_dispatcher`

构建命令均使用：

```bash
colcon build --packages-select <pkg> --symlink-install --parallel-workers 1
source install/setup.bash
```

### 4.2 室内 nav-gps smoke

已通过 wrapper 启动：

```bash
bash scripts/launch_with_logs.sh nav-gps
```

关键结果：
- `nav-gps` session 正常生成
- Nav2 lifecycle manager 全部节点成功激活
- dispatcher 成功读取 fixed origin 与路网文件
- `goto_name 前门口` 已成功触发 `FollowWaypoints`
- `FollowWaypoints` goal 已被接受并完成

这说明 `/gnss` 当前位姿 -> 路网规划 / 直达目标 -> Nav2 action 这条主软件链已经打通。

## 5. 当前仍未完成的部分

1. 室外有效 fix / `gnss_offset.txt` 仍需现场验证
2. `campus_road_network.yaml` 还只是 bootstrap 图，需要按真实校园继续采点扩展
3. `nav-gps` 还没有完成最终室外车辆验证与调优
4. `global2local_tf` / `gnss_global_path_planner` 仍保留在仓库中作为历史试验代码，没有接入主 bringup

## 6. 推荐的下一步实车序列

1. 室外启动 `make launch-explore-gps`，确认 `/fix` 与 `/gnss` 都有效
2. 生成有效 `gnss_offset.txt`
3. 用 `collect_gps_points.py` 继续采集和扩充路网
4. 启动 `make launch-nav-gps`
5. 先用 `goto_name` 验证近距离命名目标
6. 再用 `goto_latlon` 做调试直达模式验证
7. 记录 rosbag / tegrastats / session logs，完成论文采样

# GPS 采集脚本改进 + Corridor v2 运行期微调

**Status**: `collect_gps_route.py 已部署到 GitHub / Jetson，等待现场交互验证`
**当前分支**: `gps`
**最后更新**: 2026-03-25

---

## 当前活跃任务：collect_gps_route.py 改进

**工作流位置**: Step 25 已完成静态部署验证，等待用户现场运行脚本
**修改文件**: `scripts/collect_gps_route.py`（唯一目标）
**最新提交**: `41f88d9` `Improve GPS route collection review and preview for safer capture`
**Jetson 状态**: 已 `git pull` 到 `41f88d9`，`python3 -m py_compile scripts/collect_gps_route.py` 通过，无需 `colcon build`

### 2026-03-25 Codex 部署结果

- 已实现 5 个锁定改动，且只修改 `scripts/collect_gps_route.py`
- 本地验证通过：
  - `python -m py_compile scripts/collect_gps_route.py`
  - 脱 ROS stub import smoke test
- Jetson 已从 `a7dc2fd` 快进到 `41f88d9`
- 该改动是独立脚本级变更，不触发 ROS 包重编译
- 当前剩余验证：
  1. 用户在 Jetson 现场运行 `python3 scripts/collect_gps_route.py`
  2. 确认 `wp1/wp2` 默认命名、`Accept/Retry`、ENU 预览、路线摘要都按预期工作

### 可复用的现有代码

- `scene_runtime.py:FixedENUProjector` — lat/lon -> ENU x,y 投影
- 脚本内已有 `haversine_m`、`bearing_deg`、`load_fixed_origin`

### 改动 1：修复 waypoint 默认命名

**位置**: `main()` 第 312 行

当前第一个 waypoint 默认叫 `goal`，多点路线时语义反了。

改为：采集中统一默认 `wp1, wp2, ...`，保存前询问用户是否把最后一个重命名为 `goal`。

### 改动 2：单点重采选项

**位置**: `main()` 第 316 行之后

- 每个 waypoint 采完后显示 spread
- spread > 1.0m 时提示建议重采
- 无论 spread 多少，询问 `Accept / Retry? [A/r]:`
- 选 r 重新 `collect_fix_samples()`

### 改动 3：高度异常告警

**位置**: 紧接改动 2

- 当前点与上一个点高度差 > 10m 时打印警告
- `WARNING: altitude jumped {delta:.1f}m from previous point (GPS altitude unreliable, 2D nav not affected)`
- 仅告警不阻塞

### 改动 4：ENU 坐标预览

**位置**: 每个点采完后立即显示

- 在 `main()` 开头用 `load_fixed_origin()` + `FixedENUProjector` 创建投影器
- 新增 `from gps_waypoint_dispatcher.scene_runtime import FixedENUProjector`
  - 依赖 `pyproj`，Jetson 已安装
  - import 失败则 fallback 跳过预览
- 每采完一个点打印 `ENU: x={x:.1f}m, y={y:.1f}m (relative to origin)`

### 改动 5：保存前路线摘要

**位置**: `yaml.safe_dump()` 之前

```
=== Route Summary ===
Route: {route_name}
ENU Origin: {lat}, {lon}

  #  Name               Lat          Lon        ENU_X    ENU_Y   Leg(m)  Bearing
  S  start_ref      31.2781712  120.7327402     12.3     -5.6      -        -
  1  wp1            31.2777963  120.7327782      8.1    -47.2    42.1    172.4
  2  goal           31.2777800  120.7322618    -40.5    -49.0    48.6    268.3

Total distance: 90.7m
launch_yaw_deg: 172.4

Save? [Y/n]:
```

### 不改的部分

- 采样逻辑（10 samples, spread < 2m）
- GNSS driver 自动启停
- launch_yaw_deg 确认流程
- 输出文件格式（不破坏 runner/aligner 兼容性）

### 构建与部署

```bash
# 脚本不是 ROS 包，不需要 colcon build，git pull 即可
ssh jetson@100.97.227.24
cd ~/fyp_autonomous_vehicle && git pull --ff-only origin gps
```

### 验证

1. Jetson 运行 `python3 scripts/collect_gps_route.py`
2. 第一个 waypoint 默认名是 `wp1` 不是 `goal`
3. 采完后显示 ENU 坐标和 Accept/Retry 选项
4. 保存前显示路线摘要表格
5. 生成的 `current_route.yaml` 格式不变

---

## Corridor v2 运行期微调（已部署，等待 GPS fix 后实车验证）

### 当前状态

**已完成**:
- 独立 global aligner 架构已部署（commit `e51a46a`~`2bb6fbf`）
- Waypoint 1 已稳定到达（session `2026-03-22-21-05-17`）
- 运行期微调 v1 已部署（commit `1898655`），Jetson build 通过
- 修正 v2 已部署到 Jetson（commit `a7dc2fd`，`git pull` + `colcon build` 通过）

**v1 中确认正确并继续保留的项**：
1. `controller_frequency: 15.0`
2. `controller_server.transform_tolerance: 0.5`
3. `FollowPath.transform_tolerance: 0.5`
4. local STVL `transform_tolerance: 0.5`
5. `planner_server.transform_tolerance: 0.8`
6. local STVL `voxel_decay: 0.8`

**Codex 收敛结论**：
- 当前执行口径已收敛为单一版本，可以进入 Step 20 锁定
- 仅以下“修正方案 v2（Codex 收敛锁定版）”可执行
- 本文件后半历史方案仅保留审计记录，不再作为当前部署依据
- 2026-03-24 已按本锁定版完成 Jetson 部署；最新启动级 smoke test 说明当前 blocker 仍是 GPS `NO_FIX`，不是部署链断裂

---

## 修正方案 v2（Codex 收敛锁定版）

### Phase 1：回收 v1 中方向错误或无实证支撑的 stop-go 调整

#### 1.1 回退 RPP collision time 到已实车跑过的基线

**文件**: `src/bringup/config/nav2_explore.yaml`

```yaml
# 第 308 行
max_allowed_time_to_collision_up_to_carrot: 0.6   # 从 1.2 回退到 0.6
```

**理由**:
- `1.2` 已确认方向错误：增大时间窗口会检测更远碰撞，导致更多停车
- 当前唯一有实车 route 证据的基线是 `0.6`，不是 `0.8`
- 若不同时完成经验证的高度过滤修正，直接改到 `0.8` 仍比 `0.6` 更敏感，缺乏现场证据支撑
- 先回到已跑过的基线，再叠加低风险降噪项，符合部署最小惊扰原则

#### 1.2 增强 local Denoise Layer

**文件**: `src/bringup/config/nav2_explore.yaml`

```yaml
# 第 361 行（local costmap -> denoise_layer）
minimal_group_size: 4         # 从 3 改为 4
```

**理由**:
- 该修改只影响 local costmap 的孤立小连通域抑制
- 不会像抬高高度门限那样直接削弱低矮真实障碍的感知
- 与 `0.05m` 分辨率配合时，真实障碍通常不止 4 个连通栅格

#### 1.3 将高度门限改动从锁定批次中移除

**本轮不改**:
- local `pointcloud_mark.min_obstacle_height` 保持 `0.05`
- local `pointcloud_clear.min_z` 保持 `0.05`
- global `pointcloud_mark.min_obstacle_height` 保持 `0.05`
- global `pointcloud_clear.min_z` 保持 `0.05`

**理由**:
- 仓库内现有高度参考写明：`body_cloud` 中 `50cm` 矮墙约为 `z ≈ +0.10`
- 因此把 `min_obstacle_height` 直接抬到 `0.15`，会有过滤真实低矮障碍的风险
- STVL 官方 README 将 `min_z` 作为 clearing source 的 z 过滤参数示例；当前项目没有足够证据证明把它从 `0.05` 抬到 `0.10/0.15` 会更安全
- 这组参数后续如要继续动，必须基于现场点云切片或 bag 回放，而不是在当前计划里直接锁定

### Phase 2：修正 Waypoint 保护阈值

#### 2.1 收紧 progress guard

**文件**:
- `src/bringup/config/master_params.yaml`
- `src/navigation/gps_waypoint_dispatcher/gps_waypoint_dispatcher/gps_route_runner_node.py`

```yaml
# master_params.yaml
waypoint_start_progress_guard_m: 5.0      # 从 10.0 改为 5.0
# waypoint_start_cross_track_guard_m 保持 5.0 不变
```

```python
# gps_route_runner_node.py 第 84 行
self.declare_parameter("waypoint_start_progress_guard_m", 5.0)  # 从 10.0 改为 5.0
```

**理由**:
- GPS 2.5m 精度的 2-sigma 范围约为 `5m`
- `10.0` 过宽，只会拦极端跳变
- 现有逻辑已经有 `candidate_suspicious + previous_is_better` 双条件门控，`5.0` 可以更早拦住中等偏移

### Phase 3：补齐 global STVL TF 容忍度

#### 3.1 Global Costmap STVL Transform Tolerance

**文件**: `src/bringup/config/nav2_explore.yaml`

```yaml
# 第 492 行（global costmap -> stvl_layer）
transform_tolerance: 0.5     # 从 0.35 改为 0.5
```

**理由**:
- 与 controller/local STVL 当前已部署的 `0.5` 保持一致
- 属于明确遗漏项，不涉及新的感知安全折衷

---

## 修正 v2 汇总（唯一执行口径）

| 参数 | 当前值 | 锁定值 | 文件 |
|------|--------|--------|------|
| `max_allowed_time_to_collision` | 1.2 | **0.6** | nav2_explore.yaml |
| local `denoise_layer.minimal_group_size` | 3 | **4** | nav2_explore.yaml |
| `waypoint_start_progress_guard_m` | 10.0 | **5.0** | master_params.yaml + runner |
| global STVL `transform_tolerance` | 0.35 | **0.5** | nav2_explore.yaml |
| local/global `pointcloud_mark.min_obstacle_height` | 0.05 | **保持 0.05** | nav2_explore.yaml |
| local/global `pointcloud_clear.min_z` | 0.05 | **保持 0.05** | nav2_explore.yaml |

## 构建与部署

```bash
colcon build --packages-select gps_waypoint_dispatcher bringup --symlink-install --parallel-workers 1
source install/setup.bash
```

**2026-03-24 部署结果**:
- Jetson 已从 `1898655` 快进到 `a7dc2fd`
- `gps_waypoint_dispatcher` 与 `bringup` build 通过
- 零运动 corridor smoke test session: `/home/jetson/fyp_runtime_data/logs/2026-03-24-12-34-31/`
- 启动链正常，但 `gps_global_aligner` / `gps_route_runner` 都仍停在 `WAITING_FOR_STABLE_FIX`
- 当前真正阻塞仍是现场 GPS `fix=0 / satellites=0`

## 预期效果

- Waypoint 2 起始 progress：`16.51m` → 明显收敛，目标 `<5m`
- TF extrapolation：global STVL 与 local 口径一致后应继续减少
- Stop-go：相对 v1 当前部署状态应改善，但这轮目标是“先不再放大 collision ahead”，不是一次性把近地噪声问题彻底做完
- Controller 频率：继续保持 `15Hz`

## 风险评估

| 修改项 | 风险等级 | 说明 |
|--------|---------|------|
| collision time 回退到 0.6 | 低 | 回到唯一有实车 route 证据的基线 |
| denoise group_size 4 | 低 | 对小散点更严格，但不直接过滤低矮真实障碍 |
| guard_m 5.0 | 低 | GPS 2-sigma 范围 + 双条件门控 |
| global STVL tolerance 0.5 | 低 | 与 local/controller 口径一致 |
| 高度门限保持不动 | 低 | 避免在证据不足时引入低矮障碍漏检 |

## 回退策略

所有锁定改动都是参数级微调。如果效果不佳：
- `minimal_group_size` 可改回 `3`
- `waypoint_start_progress_guard_m` 可改回 `10.0`
- global STVL `transform_tolerance` 可改回 `0.35`
- `max_allowed_time_to_collision` 保持 `0.6` 作为当前安全基线，不建议再次无证据上调

## 历史存档（不可执行）

以下内容为 2026-03-23 早前方案记录，仅用于审计和追溯，不作为当前部署口径。

#### 1.1 Collision Ahead 触发阈值放宽

**文件**: `src/bringup/config/nav2_explore.yaml`

**修改**:
```yaml
# 第 308 行
max_allowed_time_to_collision_up_to_carrot: 1.2  # 从 0.6 提高到 1.2
```

**理由**:
- 当前 0.6s 仅前瞻 0.27m，小于安全边界 0.84m
- 1.2s 前瞻 0.54m，覆盖安全边界
- 符合 Nav2 最佳实践（默认 1.0s）

**预期**: collision ahead 触发次数降低 60-70%

#### 1.2 STVL Voxel 衰减加速

**文件**: `src/bringup/config/nav2_explore.yaml`

**修改**:
```yaml
# 第 385 行
voxel_decay: 0.8  # 从 1.2 降到 0.8
```

**理由**:
- 点云噪声更快消失，减少误报源头
- 配合 1.1 使用效果更佳

**风险**: 低（动态障碍物可能过早消失，但 corridor 场景影响小）

#### 1.3 Transform Tolerance 放宽

**文件**: `src/bringup/config/nav2_explore.yaml`

**修改**:
```yaml
# 第 229 行
controller_server:
  ros__parameters:
    transform_tolerance: 0.5  # 从 0.35 提高到 0.5

# 第 304 行
FollowPath:
  transform_tolerance: 0.5  # 从 0.35 提高到 0.5

# 第 370 行（local_costmap STVL）
transform_tolerance: 0.5  # 从 0.35 提高到 0.5

# 第 145 行（planner）
planner_server:
  ros__parameters:
    transform_tolerance: 0.8  # 从 0.5 提高到 0.8
```

**理由**:
- 当前 0.35s 对 Jetson 偏严
- 0.5s 是嵌入式平台常见值
- 容忍 CPU 波动，减少 future extrapolation

**预期**: TF extrapolation 次数降低 50-70%

#### 1.4 Controller 频率降低

**文件**: `src/bringup/config/nav2_explore.yaml`

**修改**:
```yaml
# 第 227 行
controller_server:
  ros__parameters:
    controller_frequency: 15.0  # 从 20.0 降到 15.0
```

**理由**:
- 当前已经 miss 20Hz 目标
- 15Hz 仍能保证控制响应
- 减少 TF 查询压力和 CPU 负载

**风险**: 低（控制响应略慢，但 corridor 直线场景影响小）

```
NMEA 驱动 → /fix → PGO（ENU→map 旋转估计 + GPS 因子融合）
                         ↓
                    map frame 对齐 ENU
                         ↓
                    发布 /gps_corridor/enu_to_map 变换
                         ↓
GPS Route Runner → 读 ENU→map 变换 → GPS 路点转 map 坐标 → Nav2 (RPP)
```

**不用 gps_anchor_localizer_node**。PGO 自己估计完整的 ENU→map 变换（旋转+平移），同时做 GPS 因子融合。Runner 节点读这个变换做 GPS→map 坐标转换。简化管道，减少依赖。

### Phase 2：Runner Waypoint 边界保护（必须部署）

#### 2.1 Waypoint 边界 Alignment 切换限幅

**文件**:
- `src/navigation/gps_waypoint_dispatcher/gps_waypoint_dispatcher/gps_route_runner_node.py`
- `src/bringup/config/master_params.yaml`

**修改位置**: `_choose_waypoint_alignment()` 方法（第 520-563 行）

**修改内容**:

1. 提高保护阈值参数：
```python
# 第 84-85 行
self.declare_parameter("waypoint_start_progress_guard_m", 10.0)  # 从 4.0 提高到 10.0
self.declare_parameter("waypoint_start_cross_track_guard_m", 5.0)  # 从 3.0 提高到 5.0
```

```yaml
/gps_route_runner:
  ros__parameters:
    waypoint_start_progress_guard_m: 10.0      # 从 4.0 提高到 10.0
    waypoint_start_cross_track_guard_m: 5.0    # 从 3.0 提高到 5.0
```

2. 修改保护逻辑（第 545-548 行）：
```python
# 原代码：
previous_is_better = (
    previous_progress_m + 0.5 < candidate_progress_m
    or previous_cross_track_m + 0.5 < candidate_cross_track_m
)

# 改为：
previous_is_better = (
    abs(previous_progress_m) + 1.0 < abs(candidate_progress_m)
    or abs(previous_cross_track_m) + 0.5 < abs(candidate_cross_track_m)
)
```

**理由**:
- 当前 4.0m 阈值不够，16.51m 跳变未被拦截
- corridor launch 当前会通过 `master_params.yaml` 给 `gps_route_runner` 注入参数；若只改 Python 默认值，运行时仍会被 YAML 中的 `4.0 / 3.0` 覆盖
- 新逻辑：只要 previous 更接近 0 就用 previous
- 避免 waypoint 边界处的投影跳变

**预期**: 第二段起始 progress 接近 0m

---

## 构建与部署

### 构建步骤

```bash
# 只需重建修改的包
colcon build --packages-select gps_waypoint_dispatcher bringup --symlink-install --parallel-workers 1
source install/setup.bash
```

### 验证步骤

1. 实车测试 corridor
2. 观察日志：
   - Collision ahead 次数应显著降低
   - Waypoint 2 起始 progress 应接近 0m
   - TF extrapolation 次数应降低
   - Controller 应稳定达到 15Hz

---

## 风险评估

| 修改项 | 风险等级 | 回退方案 |
|--------|---------|---------|
| Collision ahead 阈值 1.2s | 低 | 改回 0.6s |
| Voxel decay 0.8s | 低 | 改回 1.2s |
| Transform tolerance 0.5s | 低 | 改回 0.35s |
| Controller 15Hz | 低 | 改回 20Hz |
| Waypoint 保护逻辑 | 低 | 改回原逻辑 |

所有修改都是参数级或简单逻辑调整，不涉及架构变更。

---

## 2026-03-23 Codex 部署性审查补充

### 发现 1：Phase 2 只改 Python 默认值不能直接生效

- `system_gps_corridor.launch.py` 当前以 `parameters=[master_params_file, {...}]` 启动 `gps_route_runner`
- `master_params.yaml` 里 `/gps_route_runner` 仍显式写着：
  - `waypoint_start_progress_guard_m: 4.0`
  - `waypoint_start_cross_track_guard_m: 3.0`
- 因此若只改 `gps_route_runner_node.py` 的 `declare_parameter()` 默认值，运行时仍会被 YAML 覆盖，现场行为不会变化

**部署修正**:
- Phase 2 必须同步修改 `src/bringup/config/master_params.yaml`
- Python 默认值可一并改，作为代码默认值与运行参数保持一致；但真正决定 corridor 运行时行为的是 `master_params.yaml`

### 发现 2：Planner `transform_tolerance` 的目标项是成立的

- 当前实际生效的 `planner_server.ros__parameters.transform_tolerance` 仍是 `0.5`
- 因此计划中的 `0.5 -> 0.8` 方向正确
- 搜索结果中 `1.0` 那项来自 `amcl`，不是 planner，不构成部署冲突

### 部署性结论

- **按原文直接执行：存在一个运行时参数覆盖缺口，不可直接部署**
- **按上述补丁微调后：可部署**
- Step 19 可通过，等待用户确认进入 Step 20

---

## 预期效果

- Collision ahead 触发次数：236 → ~70-90 次
- TF extrapolation 次数：51 → ~10-20 次
- Waypoint 2 起始 progress：16.51m → ~0-2m
- Stop-go 顿挫：明显改善
- Controller 频率：稳定达到 15Hz

---

最新多轮实车后，出现了一个超出普通调参范围的新问题：

- fixed-launch bootstrap 阶段，车辆能较直地向第一个 waypoint 推进
- 一旦切到 PGO，对齐源仍继续漂移
- runner 会在切换后重算当前 waypoint 的剩余 subgoal 链
- controller 随后进入 `collision ahead` / backup recovery，车辆出现回头与转圈

因此当前需要补做一轮架构级调研，核心问题不是“要不要 GPS”，而是：

1. GPS 是否应继续直接耦合进当前 PGO，并在 corridor 运行中接管
2. 还是应拆分成独立的 global aligner，只负责平滑发布 `ENU -> map`
3. runner 是否应只消费稳定的 `ENU -> map`，而不让 PGO 图优化结果直接改变 Nav2 正在使用的参考系

### 本轮调研目标

- 基于现有日志与代码，判断 `GPS-in-PGO` 在当前 fixed-launch corridor 场景中是否仍是正确方向
- 若不是，给出最小改造面版本的替代架构
- 明确：
  - 哪些组件保留
  - 哪些组件拆分
  - `map/odom/base_link` 的语义如何维持一致
  - route runner 应消费哪一个全局对齐源

### 约束

- 先做调研，不立即改架构代码
- 结论必须同时解释：
  - 为什么 bootstrap 前半段更稳
  - 为什么 PGO 接管后会退化
  - 如何在不丢掉 GPS 全局纠偏能力的前提下，避免运行中参考系抖动

### 本轮调研结论（Codex 代行架构评估）

#### 结论 1：GPS 仍然应该保留，但不应继续以当前 live PGO handoff 方式进入 corridor 控制闭环

当前日志与代码共同说明：
- bootstrap 阶段车辆可较稳定推进第一个 waypoint
- 一旦切到 PGO：
  - `ENU -> map` 仍继续漂移
  - runner 会重算当前 waypoint 的剩余 subgoals
  - controller 随后进入 collision / backup recovery

因此当前主问题不是“要不要 GPS”，而是：
- GPS 是否必须继续直接耦合进当前 PGO 并在运行中接管 corridor

评估结论：
- **不推荐继续强化当前这条 live handoff 链**

#### 结论 2：当前最合理的方向是“保留 FAST-LIO2，拆出独立 global aligner”

推荐目标架构：

```text
FAST-LIO2 -> 提供局部连续位姿 / odom
GPS global aligner -> 估计平滑 ENU -> map
GPS Route Runner -> 消费平滑 ENU -> map，把固定 route waypoint 投到当前 map
Nav2 -> 只追当前 map 中的目标点
PGO -> 降级为离线/可选全局优化模块，不再作为 corridor 运行时接管源
```

关键原则：
- GPS 仍参与全局纠偏
- 但 corridor 运行时，不再让 live PGO 图优化直接改变 Nav2 正在追的对齐源
- runner 不应在当前 subgoal 中途因 alignment 源变化而重算已执行进度

#### 结论 3：若尽量复用现成包，优先是分层全局定位模块，不是整包替换 SLAM

优先级判断：

1. **首选**：`robot_localization + navsat_transform`
   - 作用：作为独立 global aligner 的骨架
   - 原因：最符合 ROS 官方“局部连续 + 全局纠偏”分层范式

2. **不推荐当前阶段直接采用**：LIO-SAM 类整包替换
   - 原因：
     - 官方实现历史上以 ROS1/catkin 为主
     - 对 Livox 固态雷达并非低风险 drop-in
     - 现有 Humble + MID360 + Nav2 栈替换成本过高

#### 结论 4：后续若进入架构实施，最小改造面应如下

1. 新增 `global_aligner` 节点，专门输出平滑 `ENU -> map`
2. route runner 保留，但改为：
   - 不在当前 subgoal 中途因 alignment 更新而重建剩余子目标链
   - 只在 waypoint 边界或安全边界吸收新的 alignment
3. corridor 运行链中停止使用“PGO ready 后自动接管当前 route”
4. PGO 保留为：
   - 离线分析 / 日志验证
   - 后续独立评估是否还能作为全局辅助，而不是当前控制主链的一部分

## 2026-03-22 Night 独立 Global Aligner 部署方案（锁定候选）

**工作流位置**: Step 17-19 重新开始（新架构方向）

### 目标

在**不更换主 SLAM 包**的前提下，把 corridor v2 收敛为一条更稳的运行链：

```text
/fix + map->base_link + fixed route datum
    -> gps_global_aligner
    -> /gps_corridor/enu_to_map
    -> gps_route_runner
    -> Nav2

FAST-LIO2 + PGO(loop closure only)
    -> 持续提供局部定位 / map->odom
```

### Phase 1（必须部署，最小改造面）

#### 1.1 新增独立 `gps_global_aligner_node`

**建议放置位置**: `src/navigation/gps_waypoint_dispatcher/gps_waypoint_dispatcher/gps_global_aligner_node.py`

**原因**:
- 现有 `gps_waypoint_dispatcher` 已具备：
  - `pyproj`
  - route YAML 读取
  - ENU 投影工具
  - TF 查询能力
- 直接复用当前 `alignment_topic` 抽象，改造面最小

**输入**
- `/fix`
- `map -> base_link` TF
- `route_file`
- 固定 ENU 原点

**输出**
- `/gps_corridor/enu_to_map`
  - 继续复用当前 `Float64MultiArray [theta, tx, ty, valid]`
- 新增调试状态：
  - `/gps_corridor/alignment_status`
  - `/gps_corridor/alignment_debug`（可选）

**内部逻辑**
1. 启动阶段先基于：
   - `start_ref`
   - `launch_yaw_deg`
   - 当前 `map -> base_link`
   构造 bootstrap `ENU -> map`
2. bootstrap 一旦建立，立即开始对外发布有效 alignment
3. 运行阶段持续采集：
   - 当前稳定 GPS → ENU
   - 当前 `map -> base_link` 位置
   形成在线 `ENU/map` 配对
4. 基于最近窗口解算刚体变换
5. 对解算结果做**平滑与限速**
   - 限制角速度更新
   - 限制平移更新
   - 严格拒绝离群点

**关键原则**
- 运行中 alignment 可以更新
- 但必须是**平滑收敛**
- 不能像当前 PGO handoff 那样瞬间切换参考系

#### 1.2 corridor 模式下 route runner 改为“消费稳定 aligner”，不再做 live PGO handoff

**文件**: `src/navigation/gps_waypoint_dispatcher/gps_waypoint_dispatcher/gps_route_runner_node.py`

**改动要点**
- 去掉 corridor 运行时 `bootstrap -> pgo` 接管状态机
- runner 不再自己判断 `pgo_switch_*`
- runner 只消费 `/gps_corridor/enu_to_map`

**新的进度语义**
- 不允许在 alignment 更新时重建已经执行到一半的子目标链
- 当前 segment / subgoal 的进度必须保留

**推荐实现**
- 将 waypoint 几何保留在 ENU 域
- 每次用最新 alignment 只做：
  - 当前 robot map pose -> 反解 ENU 位置
  - 在当前 ENU 段上求 progress
  - 生成“前方一个 lookahead/subgoal”
- 不再用“从当前 map pose 直接重新切完整剩余段”的方式生成 subgoal

#### 1.3 corridor 模式下关闭 PGO 的 GPS 因子

**原因**
- 当前目标是把 GPS 从 PGO 运行时接管链中移出
- 若 corridor 模式仍让 PGO 同时融合 GPS，则会形成双重全局修正，增加耦合和调试难度

**实施方式**
- corridor launch 下给 `/pgo/pgo_node` 单独覆盖：
  - `"gps.enable": false`

**保留内容**
- PGO 仍保留：
  - 图优化 / 回环
  - `map -> odom`
  - `optimized_odom`

#### 1.4 启动链调整

**文件**
- `src/bringup/launch/system_gps_corridor.launch.py`
- `src/navigation/gps_waypoint_dispatcher/setup.py`

**改动**
1. 新增 `gps_global_aligner_node` console script
2. corridor launch 中：
   - 先启动 explore 栈
   - 再启动 NMEA
   - 再启动 `gps_global_aligner`
   - 最后启动 `gps_route_runner`
3. runner 仅等待：
   - Nav2 ready
   - valid alignment topic
   - 启动位 sanity check

#### 1.5 日志与 bag 补充

**新增录制**
- `/gps_corridor/enu_to_map`
- `/gps_corridor/alignment_status`
- `/gps_corridor/alignment_debug`（若实现）

**原因**
- 下一轮现场若再出现“前半段好、后半段偏”，需要直接区分：
  - GPS 本身问题
  - aligner 输出漂移
  - runner progress 语义问题

### Phase 2（可选增强，不作为首轮 mandatory）

#### 2.1 用 `robot_localization + navsat_transform` 替代 aligner 内核

**定位**
- 不是替换 FAST-LIO2 / Nav2
- 而是替换 `gps_global_aligner` 的内部实现骨架

**适用时机**
- 当 Phase 1 自研 aligner 证明方向正确后
- 若后续希望更接近 ROS 官方分层范式，再引入

**当前不作为首轮 mandatory 的原因**
- 需要额外梳理：
  - datum / 世界航向约束
  - 与现有 FAST-LIO2 / PGO TF 语义的衔接
- 首轮部署会比自研轻量 aligner 更重

#### 2.2 若 PGO loop closure 仍导致 map 明显跳变，再评估 corridor 纯 FAST-LIO2 模式

这是 fallback，不是首选方案。

### 部署性审查结论

#### 可部署项

1. **新增 Python global aligner**：可直接落在现有 `gps_waypoint_dispatcher` 包，无需新重依赖
2. **runner 改消费稳定 alignment**：现有代码已通过 `alignment_topic` 解耦，改造面明确
3. **corridor 模式关闭 PGO GPS**：当前 PGO 已有 `gps.enable` 参数，配置面明确

#### 风险点

1. **runner 进度语义重构** 是本轮最大代码风险
   - 如果只简单“继续每轮重算 map subgoal”，问题会复现
2. **PGO loop closure 仍可能对 `map -> odom` 造成跳变**
   - 但这和“GPS-in-PGO 接管”是两个问题
   - 本轮先把 GPS 这一层耦合去掉，再单独看 loop closure 是否仍是 blocker

#### 审查结论

- 这条新方案**可部署**
- 且比“直接整包替换成另一套 GPS 紧耦合 SLAM”风险更低
- Step 19 可通过，等待用户进入 Step 20 锁定

## 2026-03-22 微调优化方案（方案 B）

**工作流位置**: Step 8-16 完成，等待 Codex 执行 Step 17-25

### 优化目标

1. **PGO 接管门槛**：从数学不可能 → 可切换
2. **Costmap 障碍清除**：从 ~2 秒残留 → ~0.5 秒清除
3. **系统响应速度**：提高 Global Costmap 刷新率，减少绿色路径滞后

### Phase 1（必须部署）

#### 1.1 PGO 接管门槛修正
**文件**: `src/bringup/config/master_params.yaml`
```yaml
gps_route_runner:
  pgo_switch_min_stable_updates: 3      # 从 4 降到 3
  pgo_switch_stable_window_s: 3.0       # 保持
  bootstrap_switch_distance_m: 6.0      # 保持
```
**风险**: 低

#### 1.2 Costmap 频率提升（激进）
**文件**: `src/bringup/config/nav2_explore.yaml`
```yaml
local_costmap:
  update_frequency: 12.0                # 从 10.0 提高到 12.0
global_costmap:
  update_frequency: 5.0                 # 从 2.0 提高到 5.0
  publish_frequency: 2.0                # 从 1.0 提高到 2.0
```
**风险**: 中高（可能导致 Jetson 掉频）
**回退方案**: Local 10Hz / Global 3Hz

#### 1.3 STVL 障碍清除
**文件**: `src/bringup/config/nav2_explore.yaml`
```yaml
local_costmap:
  voxel_layer:
    plugin: "spatio_temporal_voxel_layer/SpatioTemporalVoxelLayer"
    voxel_decay: 2.0                    # 2 秒后自动清除
    decay_model: 1                      # 指数衰减
    decay_acceleration: 0.5
    raytrace_min_range: 0.2             # 保持，不扩大死区
```
**前置条件**: `sudo apt install ros-humble-spatio-temporal-voxel-layer`
**风险**: 低

### Phase 2（可选）

#### 2.1 FAST-LIO2 感知范围
```yaml
fastlio2:
  det_range: 55.0                       # 从 60.0 降到 55.0
```

#### 2.2 PGO 回环参数
```yaml
pgo:
  loop_search_radius: 1.5               # 从 1.0 提高到 1.5
  gps:
    alignment_min_spread_m: 4.0         # 从 5.0 降到 4.0
```

### 验证方法

1. **PGO 接管**: `ros2 topic echo /gps_corridor/status`
2. **Costmap 清除**: RViz 观察障碍移动后更新速度
3. **频率稳定**: `ros2 topic hz /cmd_vel /local_costmap/costmap /global_costmap/costmap`
4. **系统负载**: `htop` 确保 CPU < 80%

---

## 2026-03-22 Codex 对方案 B 的部署性审查

**审查结论**: 原方案 B 有 2 个部署缺口；在不改变总体架构的前提下补齐后，计划可部署。

### 1. PGO 接管门槛修正可直接部署

- 当前代码的真实 hold reason 已明确是 `have 3/4 recent PGO updates`
- 因此把 `pgo_switch_min_stable_updates: 4 -> 3` 属于低风险、直接对症的修正
- `pgo_switch_stable_window_s: 3.0` 与这一改动可先保持一致，先验证是否足以触发切换

### 2. Global Costmap `5Hz` 不能直接作为“绿色 `/plan` 更快”的依据

- 当前仓库没有自定义 NavigateToPose BT XML 覆盖默认行为树
- Jetson 本机 Nav2 Humble 默认 BT 仍使用 `RateController hz="1.0"` 对 planner 重规划节流
- 因此即使把 Global Costmap 提到 `5Hz`，`/plan` 也不会自动变成 `5Hz`
- 与此同时，最新现场日志已经出现：
  - controller miss `20Hz`
  - planner loop 实际掉到约 `2Hz`

**部署修正**:
- Phase 1.2 改成 staged rollout：
  - 首轮部署目标：`global_costmap update_frequency: 3.0`, `publish_frequency: 1.5`
  - `5.0 / 2.0` 只作为二轮实验值，不作为首轮 mandatory
- 如果后续确实要让绿色 `/plan` 比 `1Hz` 更快，必须新增 **BT XML override**，而不是只改 costmap Hz

### 3. STVL 不是“换插件名 + 加 voxel_decay”就能直接落地

- Jetson 当前 **未安装** `ros-humble-spatio-temporal-voxel-layer`
- 但 apt 源中已有可安装候选包，因此这不是架构 blocker，而是部署前置条件
- STVL 的配置结构也与当前 `VoxelLayer` 不同，不能直接复用现有参数块

**部署修正**:
- 在 Step 21 前，先补明确前置步骤：
  - `sudo apt install ros-humble-spatio-temporal-voxel-layer`
- 在 YAML 中使用完整的 STVL 参数块，而不是只替换 plugin 字符串
- STVL 配置必须至少补齐：
  - layer-level: `voxel_size`, `obstacle_range`, `observation_sources`, `transform_tolerance`
  - marking source
  - clearing source
  - `model_type: 1`（3D lidar）
  - `horizontal_fov_angle`
  - `vertical_fov_angle`
  - `vertical_fov_offset`
  - `clear_after_reading`
- 对 Livox MID360，需显式写 `vertical_fov_offset`；官方 README 示例已点名 MID360 需要该参数

### 4. 锁定后的可执行版本

#### Phase 1（首轮 mandatory）

1. `pgo_switch_min_stable_updates: 3`
2. `local_costmap update_frequency: 12.0`
3. `global_costmap update_frequency: 3.0`
4. `global_costmap publish_frequency: 1.5`
5. `controller_frequency: 20.0`

#### Phase 1.3（条件 mandatory）

- 若安装 STVL 包成功，则切换到完整 STVL 配置
- 若 Jetson 安装或 smoke test 失败，则本轮先保留现有 `VoxelLayer`，不在同一轮里硬切插件

#### Phase 2（可选）

- FAST-LIO2 `det_range: 55.0`
- PGO `loop_search_radius: 1.5`
- 若首轮已稳定，再评估 `global_costmap 5.0 / 2.0` 与 BT XML override

### 5. 部署性结论

- **按 CC 原文直接执行：不可直接部署**
- **按上述 Codex 微调后：可部署**
- Step 19 可通过，等待用户进入 Step 20 锁定

---

## 2026-03-22 Afternoon Runtime Loop Status

**当前执行位置**: `Step 29 完成，问题归类为 Step 21 小问题迭代`

### 已验证成立

- corridor v2 已经从“无法起跑”推进到“可稳定启动并进入 `RUNNING_ROUTE`”
- 最新实车 session `2026-03-22-15-16-00` 中，route runner 已连续推进到第一个 waypoint `right-top-corner` 的倒数第二个 subgoal
- 最新部署版 `b7a6b2f` 没有再出现“启动即 abort / Nav2 不起 / corridor 命令无前台状态”这类启动级 blocker

### 当前收敛出的真实问题

1. **PGO 接管门槛仍未闭合**
   - PGO 在运行中已经发布有效 `ENU->map`
   - 但 route runner 仍持续保持 bootstrap
   - 最新日志显示 hold reason 反复是 `have 3/4 recent PGO updates` / `have 2/4 recent PGO updates`
   - 说明当前 `pgo_switch_min_stable_updates` 与 `pgo_switch_stable_window_s` 的组合，对现场约 `~1Hz` 的 PGO 更新频率来说过严，导致“PGO ready 但永远切不过去”

2. **绿色 `/plan` 的确由代价地图驱动**
   - Nav2 planner 每约 `1Hz` 重算 `/plan`
   - `/plan` 是基于当前 goal + global costmap 生成的全局路径
   - local controller 再基于 local costmap 跟踪 `/plan`
   - 因此若 global/local costmap 残留障碍没有及时清掉，绿色路径就会绕障、弯折、甚至向后绕

3. **当前不应继续盲目拉高刷新率**
   - 最新日志里 controller 已经反复 `Control loop missed its desired rate of 20Hz`
   - planner 也出现过 `Current loop rate is 2.0759 Hz`
   - 这说明当前 Jetson 上的瓶颈不是“频率设得还不够高”，而是“地图/TF/控制链已经在掉频”
   - 下一轮应优先修 obstacle layer 语义、清障策略和接管门槛，而不是继续一味提高 Hz

### 下一轮 Step 21 微调范围

- 收紧 PGO 接管判据，使其与现场实际 PGO 发布频率匹配
- 区分 global/local costmap 的职责:
  - global costmap 避免保留“启动前人站在车前”这类陈旧障碍
  - local costmap 负责实时动态避障
- 继续排查 controller `collision ahead` 与 TF extrapolation / loop miss 的关系
- 必要时再调整 local costmap 窗口或清障语义，但不再先验要求更高刷新率

---

## 实施优先级

| 阶段 | 内容 | 依赖 | 改动量 |
|------|------|------|--------|
| **Phase 1** | P2/P3/P4: Nav2 参数调优 | 无 | YAML 配置 |
| **Phase 2** | P0: PGO GPS 融合修复 | 需编译 C++ | pgo_node.cpp + simple_pgo.cpp |
| **Phase 3** | P5: 多点 GPS 路线 Runner | P0 完成 | Python 新节点 |

Phase 1 可立即部署验证，不动 C++ 代码。Phase 2 是核心改动。Phase 3 基于 Phase 2 成果。

---

## Phase 1: Nav2 参数调优

### 1.1 控制器: DWB → Rotation Shim + Regulated Pure Pursuit

**解决**: P2（路径折弯/卷团）

**文件**: `src/bringup/config/nav2_explore.yaml` — controller_server 段

```yaml
# === 替换 FollowPath 段 ===
controller_server:
  ros__parameters:
    controller_frequency: 20.0
    min_x_velocity_threshold: 0.001
    min_y_velocity_threshold: 0.5
    min_theta_velocity_threshold: 0.001
    failure_tolerance: 0.3
    progress_checker_plugin: "progress_checker"
    goal_checker_plugins: ["general_goal_checker"]
    controller_plugins: ["FollowPath"]

    progress_checker:
      plugin: "nav2_controller::SimpleProgressChecker"
      required_movement_radius: 0.3       # 0.5→0.3: 降低移动要求
      movement_time_allowance: 10.0       # 3.0→10.0: 容忍短暂停顿

    general_goal_checker:
      stateful: true
      plugin: "nav2_controller::SimpleGoalChecker"
      xy_goal_tolerance: 0.35             # 0.25→0.35: 中间航点放宽
      yaw_goal_tolerance: 6.28            # 0.25→6.28(2π): 不检查朝向

    FollowPath:
      plugin: "nav2_rotation_shim_controller::RotationShimController"
      angular_dist_threshold: 0.785       # 45°: 仅大角度变化时旋转
      angular_disengage_threshold: 0.39  # 审计修复: 脱离旋转阈值 = 阈值的一半，防止抖振
      forward_sampling_distance: 0.5
      rotate_to_heading_angular_vel: 1.0
      max_angular_accel: 1.6
      simulate_ahead_time: 1.0
      rotate_to_goal_heading: false       # 不在目标处旋转

      primary_controller: "nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController"
      desired_linear_vel: 0.5
      lookahead_dist: 1.0
      min_lookahead_dist: 0.4
      max_lookahead_dist: 1.5
      lookahead_time: 1.5
      use_velocity_scaled_lookahead_dist: true
      transform_tolerance: 0.1
      min_approach_linear_velocity: 0.05
      approach_velocity_scaling_dist: 0.6
      use_collision_detection: true
      max_allowed_time_to_collision_up_to_carrot: 1.0
      use_regulated_linear_velocity_scaling: true
      use_cost_regulated_linear_velocity_scaling: false
      regulated_linear_scaling_min_radius: 0.9
      regulated_linear_scaling_min_speed: 0.25
      use_rotate_to_heading: false        # 不在子目标旋转
      allow_reversing: false
      max_robot_pose_search_dist: 10.0
```

**关键变更理由**:
- `RotateToGoal` critic 被完全移除（RPP 没有这个概念）
- `use_rotate_to_heading: false` + `rotate_to_goal_heading: false` 消除所有旋转停顿
- `yaw_goal_tolerance: 6.28` = 2π = 任意朝向都接受
- `lookahead_dist: 1.0` 适合走廊直线

### 1.2 Local Costmap 优化

**解决**: P3（幻影障碍停车）+ P4（过重）

**关键坐标参考**（基于 docs/hardware_spec.md 实测数据）:
- LiDAR 离地: 0.447m
- t_il.z: 0.044m → base_link (IMU) 离地: 0.403m
- body_cloud 中地面 z ≈ -0.40m, 10cm 马路牙 z ≈ -0.30m, 50cm 矮墙 z ≈ +0.10m

```yaml
local_costmap:
  local_costmap:
    ros__parameters:
      update_frequency: 5.0               # 40→5: 降低 CPU 负载
      publish_frequency: 2.0              # 40→2: 降低带宽
      global_frame: odom
      robot_base_frame: base_link
      use_sim_time: false
      rolling_window: true
      width: 5                            # 15→5: 缩小到 5m
      height: 5                           # 15→5
      resolution: 0.05                    # 0.02→0.05: 5cm 分辨率
      robot_radius: 0.38625
      plugins: ["voxel_layer", "inflation_layer"]
      # 注: DenoiseLayer 如需要再加，先验证 VoxelLayer 效果

      voxel_layer:
        plugin: "nav2_costmap_2d::VoxelLayer"
        enabled: true
        footprint_clearing_enabled: true
        origin_z: -0.45                  # 地面(-0.40)以下，确保低矮障碍在网格内
        z_resolution: 0.15              # 15cm/层，马路牙占1层，减少计算量
        z_voxels: 16                    # 16×0.15=2.4m → z=-0.45~+1.95m
        unknown_threshold: 15
        mark_threshold: 0
        publish_voxel_map: false
        observation_sources: pointcloud
        combination_method: 1
        pointcloud:
          topic: /fastlio2/body_cloud
          data_type: "PointCloud2"
          min_obstacle_height: -0.30     # 地面(-0.40)滤掉, 10cm马路牙(-0.30)保留
          max_obstacle_height: 1.5
          obstacle_min_range: 0.3        # 新增: 过滤 LiDAR 原点噪声
          obstacle_max_range: 4.0        # 15→4: 局部只关心近距离
          raytrace_min_range: 0.3
          raytrace_max_range: 5.0
          clearing: true
          marking: true

      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        cost_scaling_factor: 3.0          # 2.5→3.0
        inflation_radius: 0.55            # 0.4→0.55
      always_send_full_costmap: false
```

**幻影障碍防线**（min_obstacle_height 回到 -0.30 后靠以下三层解决）:
1. 分辨率 0.02→0.05: 单个噪声点影响更小
2. obstacle_min_range=0.3: 过滤 Livox MID360 原点自检测噪声
3. VoxelLayer 3D raytrace: 地面点在最底层体素，不会被误投为障碍柱
4. 兜底: 如仍有残留，追加 DenoiseLayer 移除孤立单格障碍

### 1.3 Global Costmap 优化

**解决**: P4（过重）

**审计修复**: global costmap 用 2D ObstacleLayer。当车靠近马路牙（<2.8m）时，LiDAR
光束从马路牙上方飞过，2D raytrace 会错误清掉已标记的马路牙。修复方案：关闭 clearing，
只标不清，靠 inflation 衰减和 costmap rolling 自然淘汰旧障碍。

```yaml
global_costmap:
  global_costmap:
    ros__parameters:
      update_frequency: 1.0               # 5→1
      publish_frequency: 0.5              # 5→0.5
      global_frame: map
      robot_base_frame: base_link
      use_sim_time: false
      robot_radius: 0.38625
      resolution: 0.10                    # 0.02→0.10: 10cm
      track_unknown_space: true
      rolling_window: true
      width: 30                           # 50→30
      height: 30                          # 50→30
      plugins: ["obstacle_layer", "inflation_layer"]

      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        enabled: true
        footprint_clearing_enabled: true
        observation_sources: pointcloud
        pointcloud:
          topic: /fastlio2/body_cloud
          data_type: "PointCloud2"
          min_obstacle_height: -0.30      # 与 local 一致, 保留马路牙
          max_obstacle_height: 1.5
          obstacle_min_range: 0.3
          obstacle_max_range: 10.0
          raytrace_max_range: 12.0
          clearing: false                 # 审计修复: 关闭清障，防止近距离误清马路牙
          marking: true

      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        cost_scaling_factor: 3.0
        inflation_radius: 0.55
      always_send_full_costmap: false
```

### Phase 1 性能改善预估

| 指标 | 修改前 | 修改后 |
|------|--------|--------|
| 局部 costmap cells | 562,500 | 10,000 (**56x↓**) |
| 全局 costmap cells | 6,250,000 | 90,000 (**70x↓**) |
| 路径折弯/卷团 | 严重 | 消除（RPP 无 RotateToGoal）|
| 幻影障碍停车 | 频繁 | 大幅减少（VoxelLayer 3D + 分辨率 0.05 + obstacle_min_range=0.3）|

### 1.4 全量日志记录

**解决**: 每次运行自动产生完整日志，用于复盘、调参和论文数据

**输出目录**: 沿用现有 `scripts/launch_with_logs.sh` session 目录规范

```
~/fyp_runtime_data/logs/<session>/
├── console/                # ROS 2 / launch console 日志（ROS_LOG_DIR）
├── data/                   # 节点自定义日志（FYP_LOG_SESSION_DIR）
├── system/                 # tegrastats + session_info.yaml
└── bag/                    # ros2 bag 录制（本次 corridor 运行数据）
```

`~/fyp_runtime_data/logs/latest` 继续指向最近一次 session，不另起一套平行日志体系。

**录制 topic 列表**:

| Topic | 说明 | 大小估计 |
|-------|------|---------|
| `/fix` | GPS 原始数据 | 极小 |
| `/fastlio2/lio_odom` | SLAM 里程计 | 小 |
| `/tf` | 坐标变换（含 map→odom→base_link） | 小 |
| `/tf_static` | 静态 TF | 极小 |
| `/gps_corridor/status` | runner 状态机 | 极小 |
| `/gps_corridor/goal_map` | 当前目标点 | 极小 |
| `/gps_corridor/path_map` | 规划的 corridor 路径 | 极小 |
| `/cmd_vel` | 发给底盘的速度指令 | 小 |
| `/local_costmap/costmap` | 局部代价地图 | 中 |
| `/plan` | Nav2 全局路径 | 小 |

**不录制**（体积过大，NVMe 空间有限）:
- `/livox/lidar` — 原始点云 ~40MB/s
- `/fastlio2/body_cloud` — 处理后点云 ~10MB/s

**launch 文件修改**: `system_gps_corridor.launch.py` 中新增 bag record，但日志目录不在 launch 内重新造时间戳，而是挂到当前 session：

```python
session_data_dir = os.environ.get('FYP_LOG_SESSION_DIR', '')
session_root = os.path.dirname(session_data_dir) if session_data_dir else \
    os.path.expanduser(f'~/fyp_runtime_data/logs/{datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}')
bag_dir = os.path.join(session_root, 'bag')
os.makedirs(bag_dir, exist_ok=True)

# ros2 bag record
bag_record = ExecuteProcess(
    cmd=[
        'ros2', 'bag', 'record',
        '--output', bag_dir,
        '/fix',
        '/fastlio2/lio_odom',
        '/tf', '/tf_static',
        '/gps_corridor/status',
        '/gps_corridor/goal_map',
        '/gps_corridor/path_map',
        '/cmd_vel',
        '/local_costmap/costmap',
        '/plan',
    ],
    output='log',
)
```

需要在文件头部增加 `from launch.actions import ExecuteProcess`，
并在 `LaunchDescription` 的 actions 列表末尾加入 `bag_record`。
如通过 wrapper 启动，`launch.log` / console log 仍由 `ROS_LOG_DIR` 接管，不额外手写一份 stdout 重定向逻辑。

### Phase 1 构建 & 部署

```bash
# 只需要重建工作区内被改到的启动包:
colcon build --packages-select bringup --symlink-install --parallel-workers 1
source install/setup.bash
```

说明：`nav2_costmap_2d` / `nav2_regulated_pure_pursuit_controller` / `nav2_rotation_shim_controller`
是系统侧 Nav2 运行时依赖，不是本仓库内的 colcon 包，不作为 `--packages-select` 目标。

---

## Phase 2: PGO GPS 融合修复

### 2.1 概述

修改 PGO C++ 代码，解决三个子问题：
1. ENU→map 旋转估计
2. GPS topic 修正
3. 权重平衡（渐进引入）

### 2.2 文件修改清单

| 文件 | 修改内容 |
|------|---------|
| `src/perception/pgo_gps_fusion/src/pgo_node.cpp` | GPS topic 修正 + 旋转估计逻辑 + ENU→map 变换发布 |
| `src/perception/pgo_gps_fusion/src/pgos/simple_pgo.cpp` | 放松首帧先验 + GPS 渐进引入（支持 warmup sigma override） |
| `src/perception/pgo_gps_fusion/src/pgos/simple_pgo.h` | 新增旋转估计状态 / GPS warmup 状态相关成员变量 |
| `src/bringup/config/master_params.yaml` | `gps.topic: /fix` + 新增旋转估计参数 |

### 2.3 旋转估计算法

**在 `pgo_node.cpp` 的 `tryAddGPSFactor()` 中，第 787 行（ENU 转换完成后）插入：**

```
算法: 2D 最小二乘旋转估计

输入: 累积的 (enu_xy, map_xy) 配对列表
输出: 旋转角 θ 和平移 t

步骤:
1. 每次 tryAddGPSFactor 被调用时:
   - enu_xy = Forward(lat, lon) 的 (x, y)
   - map_xy = m_pgo->keyPoses()[current_idx].t_global 的 (x, y)
   - 加入配对列表

2. 检查条件:
   - 配对数 ≥ gps.alignment_min_points (默认 5)
   - 最大空间展幅 ≥ gps.alignment_min_spread_m (默认 5.0m)
   - 如不满足，跳过 GPS factor（不添加）

3. 满足条件时，计算旋转:
   - enu_centroid = mean(enu_xy_i)
   - map_centroid = mean(map_xy_i)
   - e_i' = enu_xy_i - enu_centroid
   - m_i' = map_xy_i - map_centroid
   - H = Σ e_i' * m_i'^T  (2x2 矩阵)
   - θ = atan2(H[1][0] - H[0][1], H[0][0] + H[1][1])
   - R = [[cos θ, -sin θ], [sin θ, cos θ]]
   - t = map_centroid - R * enu_centroid

4. 变换 GPS 坐标:
   - map_gps_xy = R * enu_xy + t
   - 传入 addGPSFactor() 的位置使用 map_gps_xy

5. 持续更新:
   - 每次新配对加入后重新计算 θ
   - 随着数据积累，估计精度提升
   - 审计修复: smoothAndUpdate() 之后，刷新所有配对的 map_xy
     （防止回环校正后旧 map_xy 值过时导致旋转估计偏差）

6. 发布变换:
   - 在 ROS2 topic /gps_corridor/enu_to_map 上发布 θ 和 t
   - Runner 节点订阅此 topic 做 GPS 路点转换
```

**精度估计**（GPS sigma=2.5m, 均值化后约 0.8m）:

| 行驶距离 | 配对数(~) | 角度估计误差 |
|---------|---------|------------|
| 5m | 5 | ~10-15° |
| 10m | 10 | ~5-8° |
| 20m | 20 | ~2-4° |
| 50m | 50 | ~1-2° |

### 2.4 权重平衡策略

**首帧先验放松**:
```cpp
// simple_pgo.cpp addKeyPose(), 第 49 行
// 修改前: gtsam::Vector6::Ones() * 1e-12
// 修改后:
(gtsam::Vector(6) << 1e-6, 1e-6, 1e-6, 1e-2, 1e-2, 1e-4).finished()
// 旋转保持紧 (1e-6), 平移放松到 1e-2 (sigma=0.1m), z 保持较紧 (1e-4)
```

**GPS 渐进引入**:
```
旋转估计完成后的前 5 个 GPS factor:  sigma_xy = 10.0m  (软引入)
之后的 GPS factor:                    sigma_xy = 2.5m   (正常)
```

实现约束补充：
- `simple_pgo.cpp` 需要显式支持 warmup sigma override；当前 `addGPSFactor()` 会优先使用 `NavSatFix.position_covariance`，并把 sigma clamp 到 `<= 5.0m`，不能直接实现 `10.0m` 热身。
- 因此热身期不能只改 `master_params.yaml`，必须同步改 `simple_pgo.h/.cpp` 的 GPS factor 构造逻辑。

### 2.5 配置变更

```yaml
# master_params.yaml
/pgo:
  pgo_node:
    ros__parameters:
      "gps.topic": /fix                       # /gnss → /fix
      "gps.alignment_min_points": 5           # 新增
      "gps.alignment_min_spread_m": 5.0       # 新增
      "gps.alignment_warmup_factors": 5       # 新增: 前 5 个用大噪声
      "gps.alignment_warmup_sigma": 10.0      # 新增: 热身期 sigma
      "gps.factor_interval": 5                # 10 → 5: 关键帧间隔缩小
```

### 2.6 ENU→map 变换发布

PGO 在 `timerCB` 中（已有广播 map→odom TF 的逻辑）增加：
- 发布 `std_msgs/Float64MultiArray` 到 `/gps_corridor/enu_to_map`
- payload 固定为 `[theta, tx, ty, is_valid]`
- 选择该消息的原因：Runner 只需要 2D 旋转/平移和有效位，避免为 topic 传输再套一层 TF 语义

### 2.7 启动 Bootstrap（CC 复审结论）

**问题**: 车静止启动时，PGO 无法积累空间展幅 → enu_to_map 永远不 valid → runner 不起步。

**CC 裁决: 采用方案 A（固定 yaw bootstrap），淘汰 10m 预热方案。**

**技术依据**（基于 FAST-LIO2 源码调研 `imu_processor.cpp:16-49`）:
- `gravity_align: true` 时，FAST-LIO2 用 `FromTwoVectors(-acc_mean, (0,0,-1))` 做最短弧旋转
- 该函数是确定性的：相同物理放置 → 相同 yaw0
- yaw0 启动间变化 < 0.1°（BMI088 加速度计噪声级别）
- 因此 ENU→map 旋转可在上电瞬间计算，无需等待车辆移动

**Bootstrap 算法**:

```
1. 上电 → FAST-LIO 初始化 → 读 map→base_link TF
2. 提取 yaw0 = atan2(R[1,0], R[0,0])
3. 读 route YAML 的 launch_yaw_deg（车的地理朝向，ENU 约定）
4. θ_bootstrap = yaw0 - radians(launch_yaw_deg)
5. 构造初始 ENU→map: R_bootstrap = Rz(θ_bootstrap), t_bootstrap 从 start_ref ENU + map origin 推导
6. 立即开始导航（不等 PGO valid）
```

**launch_yaw_deg 来源**:
- 对于直线 corridor: 直接复用现有 YAML 的 `bearing_deg`（起终点 GPS 方位角）
- 对于多点路线: 起点到第一个路点的方位角，或用手机指南针测量
- 只需测量一次，写入 route YAML

**Bootstrap → PGO 切换**:

```
前 20m: 使用 bootstrap 旋转（精度 ±5°，取决于 launch_yaw_deg 测量精度）
20m+:   PGO 发布 is_valid=true → runner 平滑切换到 PGO 精确旋转
        重算后续未访问路点的 map 坐标
```

切换时如果角度差 > 10°，log WARNING（可能放车朝向不对）。

**淘汰 10m 预热的理由**:
- 浪费 10m 距离 + 20s 时间
- 预热期间无 ENU→map → 无法用 GPS 路点导航，只能 body_vector 盲走
- 预热方向如有障碍物，无法用 GPS 路点规避
- 预热后仍需 bootstrap 到 PGO 的切换逻辑（复杂度不减反增）
- 数学上不需要：yaw0 在上电时已经确定

### Phase 2 构建

```bash
colcon build --packages-select pgo --symlink-install --parallel-workers 1
source install/setup.bash
```

---

## Phase 3: 多点 GPS 路线 Runner

### 3.1 新增/修改文件

| 文件 | 修改内容 |
|------|---------|
| `src/navigation/gps_waypoint_dispatcher/gps_waypoint_dispatcher/gps_route_runner_node.py` | 新的多点路线执行节点 |
| `src/navigation/gps_waypoint_dispatcher/setup.py` | 注册 `gps_route_runner_node` console script |
| `src/bringup/config/master_params.yaml` | 为 route runner 增加独立参数命名空间（ENU 原点等），避免复用旧 `gps_waypoint_dispatcher` 节点名造成参数未注入 |
| `src/bringup/launch/system_gps_corridor.launch.py` | 启动新 runner，参数从 `corridor_file` 切到 `route_file`，并接入 bag record |
| `scripts/launch_with_logs.sh` + `Makefile` | 新增 corridor 模式启动入口，保持 Step 25 继续走统一 session logging 启动点 |

### 3.2 路线 YAML Schema

```yaml
route_name: "campus_loop"
created_at: "2026-03-25"
coordinate_source: /fix
enu_origin:
  lat: 31.274927
  lon: 120.737548
  alt: 0.0
start_ref:
  lat: 31.274xxx
  lon: 120.737xxx
launch_yaw_deg: 123.4
waypoints:
  - name: "wp1"
    lat: 31.274xxx
    lon: 120.737xxx
  - name: "wp2"
    lat: 31.274xxx
    lon: 120.738xxx
  - name: "goal"
    lat: 31.275xxx
    lon: 120.738xxx
startup_fix_sample_count: 10
startup_fix_spread_max_m: 2.0
startup_gps_tolerance_m: 6.0
segment_length_m: 8.0
```

部署约束补充：
- `enu_origin` 必须与运行时 `master_params.yaml` 中 PGO/runner 使用的固定原点一致。
- runner 启动后先校验 route YAML 的 `enu_origin` 与运行时参数；不一致则直接 abort，避免 silently 用错坐标系。
- `launch_yaw_deg` 必须填写。对直线 corridor 可直接复用 `bearing_deg`。
- `collect_gps_route.py` 不能在“起点到第一个路点基线很短”的情况下静默自动生成 `launch_yaw_deg`；应显式提示用户确认，必要时要求手工输入（如手机指南针测量值）。
- runner 启动时从 TF 读 yaw0，与 `launch_yaw_deg` 一起计算 bootstrap ENU→map 旋转。

### 3.3 Runner 控制流

**CC 复审后锁定版本（方案 A: 固定 yaw bootstrap）**

```
1. 读取运行时参数中的固定 ENU 原点（独立 route runner 参数命名空间）
2. 加载路线 YAML，并校验 enu_origin 与运行时固定原点一致
3. 等待 stable /fix（10 次采样，spread < 2m）
4. 校验启动位置（距 start_ref < 6m）
5. 等待 Nav2 + map→base_link TF
6. Bootstrap: 从 TF 读 yaw0，用 launch_yaw_deg 计算初始 ENU→map 旋转
7. 用 bootstrap ENU→map 转换第一个路点 → 立即开始导航
8. 后台监听 PGO /gps_corridor/enu_to_map:
   - is_valid=true 时，切换到 PGO 精确旋转
   - 重算后续未访问路点的 map 坐标
9. 对每个 waypoint:
   a. GPS lat/lon → ENU（pyproj，与 PGO 同 ENU 原点）
   b. ENU → map（乘当前最佳旋转: bootstrap 或 PGO）
   c. 按 segment_length_m 在当前位置和下一个 waypoint 之间插航点
   d. 串行 NavigateToPose
10. 到达最终 goal → SUCCEEDED
```

### 3.4 与 corridor v1 的差异

| | Corridor v1 | GPS Route v2 |
|--|-------------|-------------|
| 路点数 | 2（起终点） | N 个 |
| 目标计算 | body_vector + yaw0 | GPS→ENU→map（PGO 旋转） |
| GPS 依赖 | 仅启动校验 | 启动 + PGO 旋转估计 |
| 路线形状 | 直线 | 任意折线 |
| PGO GPS 融合 | 不需要 | 需要（提供旋转 + 漂移校正）|

### 3.5 采点脚本

新增 `scripts/collect_gps_route.py`:
- 交互式多点采集
- 每点采 10 个 GPS 样本
- 保存为路线 YAML

### Phase 3 构建

```bash
colcon build --packages-select gps_waypoint_dispatcher bringup --symlink-install --parallel-workers 1
source install/setup.bash
```

---

## 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| RPP 控制器行为不符预期 | 低 | 中 | 保留 DWB 配置为 nav2_explore_dwb.yaml 备用 |
| PGO 旋转估计在 GPS 噪声下不收敛 | 中 | 高 | 要求最小展幅 5m + 至少 5 点；渐进引入 GPS |
| PGO C++ 修改引入 segfault | 低 | 高 | 增量修改，每步编译测试；保留旧 pgo_original 包 |
| min_obstacle_height=-0.30 地面噪声残留 | 低 | 中 | VoxelLayer 3D + 分辨率 0.05 + obstacle_min_range=0.3；兜底追加 DenoiseLayer |
| LiDAR 安装高度影响低矮障碍检测 | 中 | 低 | VoxelLayer 保留已见障碍；仅转弯盲区有风险 |

---

## 回退策略

- Phase 1 失败 → 恢复原 nav2_explore.yaml
- Phase 2 失败 → PGO 回退到纯 SLAM（gps.enable: false），corridor v1 仍可用
- Phase 3 失败 → 保持 corridor v1（两点直线仍可工作）

---

## 待用户确认项

1. **Phase 2 改 C++ 的接受度**：PGO 是核心感知节点，改动需要谨慎
2. **是否先跑 Phase 1 验证**：Phase 1 只改 YAML，可立即部署测试
3. **多点路线的实际需求**：Phase 3 的路线形状/长度/拐弯数量
4. **min_obstacle_height=-0.30 的地面噪声容忍度**：如果不平路面仍有幻影障碍，可调至 -0.25（牺牲 5cm 马路牙检测能力）

---

## 已废弃方案

| 方案 | 废弃原因 |
|------|----------|
| P0 路径 A（极简 yaw 校准，不改 PGO） | 用户选择路径 B |
| v7 scene graph + route_server | 对需求过重 |
| v6 整条 route 动态重算 | frame 混用风险 |
| 旧 gnss_global_path_planner A* | 依赖旧路网 |

---

## 当前运行期微调焦点（2026-03-22 最新）

独立 `global_aligner` 架构已经证明方向正确：
- waypoint 1 已可稳定到达
- 运行失败点已后移到 waypoint 2

当前不再优先怀疑 route GPS 采图，而是聚焦两项运行期微调：

1. **Waypoint 边界 alignment 漂移控制**
   - runner 已在 waypoint 内冻结 alignment
   - 但切到 waypoint 2 时，冻结到的 alignment 已把当前车位错误投影到第二段约 `16.5m` 处
   - 需要进一步限制 aligner 在 waypoint 边界可接受的跳变幅度

2. **Nav2 平顺性优化（不改系统运行逻辑）**
   - 目标不是换架构，而是减少 stop-go
   - 已知主因是 `collision ahead` 高频误触发与 `transformPoseInTargetFrame` future extrapolation
   - 下一轮优先通过 Nav2 / TF 容差 / 局部代价地图灵敏度微调来提升平顺性

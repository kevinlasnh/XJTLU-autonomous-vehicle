# 已知问题追踪

## 当前阻塞

1. **[致命] `feature/gps-route-ready-v2` 首轮实车 `nav-gps` 导航会在执行中失效**
   - 描述: 用户已采真实 `ls-building` scene，并完成 `current_scene/` 编译；`nav_gps_menu.py` 可正常进入 `GOAL_REQUESTED -> COMPUTING_ROUTE -> FOLLOWING_ROUTE`，但车辆只短暂动作后即停止。
   - 直接证据:
     - `goal_manager`: `FAILED; follow_path_status=6`
     - `controller_server`: `Controller patience exceeded`
     - launch 日志: `pgo_node ... process has died ... exit code -11`
   - 已确认影响链:
     - `pgo_node` 段错误退出
     - `map -> odom` TF 消失，只剩 `odom -> base_link`
     - `/gps_system/status` 从 `NAV_READY` 退回 `GNSS_READY`
     - Nav2 `follow_path` 被 abort
   - 状态: 2026-03-20 已复现并锁定为当前最高优先级 blocker
   - 影响: 新 GPS 路网导航模式当前不能通过实车验收

2. **[已验证] 室外 GNSS RF / fix 质量**
   - 描述: GPS 天线馈线已更换，设备枚举正常。
   - 状态: 2026-03-22 多轮 corridor v2 室外实车中 GPS fix 稳定工作，启动定位和 PGO 对齐均正常使用 `/fix`
   - 影响: 不再是 blocker

3. **[重要] `nav-gps` 已软件落地，但室外实车验证未完成**
   - 描述: `feature/gps-navigation-v4` 已完成 `gps_waypoint_dispatcher`、`nav2_gps.yaml`、固定 ENU 原点和 `system_nav_gps.launch.py`，室内 smoke 已通过；但真正的室外运行、路网扩充和调优还没完成。
   - 状态: 软件已完成，等待室外验证
   - 影响: 不能把 GPS 目标导航能力宣称为最终实车稳定功能

4. **[致命] 速度平滑器闭环控制失败**
   - 描述: C 板里程计闭环会导致车辆异常自转；FAST-LIO2 里程计接入闭环后也未得到稳定循迹效果。
   - 状态: 仍使用 `OPEN_LOOP`
   - 来源: 2025-11 系列实车测试

## 重要问题

5. **[重要] 长时间运行后车辆停止**
   - 描述: Nav2 路径和 costmap 仍在更新，但底盘不再运动，疑似串口输出或控制器链路问题。
   - 状态: 未排查完成

6. **[重要] SLAM Toolbox 长走廊内存压力高**
   - 描述: 长时间建图时存在明显内存增长风险。
   - 状态: 未根治

7. **[重要] LiDAR 贴墙退化**
   - 描述: MID360 贴墙时点云退化，对狭窄过道避障不友好。
   - 状态: 仅有经验性规避，暂无彻底方案

8. **[重要] FAST-LIO2 + PGO 内存增长**
   - 描述: 长时间运行时 FAST-LIO2、PGO 关键帧和相关缓存会推高内存占用。
   - 状态: 系统层面已做服务裁剪，但算法层未处理

9. **[已缓解] 代价地图障碍残留 / 消散慢**
   - 描述: 移除障碍后，代价地图上的代价值清除不够快。
   - 状态: 2026-03-26 STVL `clear_after_reading` 已从 `true` 改为 `false`（local + global），障碍由 `voxel_decay` 自然管理，不再每周期清空
   - 同期 global inflation 从 `0.75 → 0.95`，`cost_scaling_factor` 从 `2.0 → 1.0`，绿色路径不再紧贴障碍边缘
   - 影响: 已不再是 corridor 主要 stop-go 来源

## 中等问题

10. **[中等] Travel 模式开发暂停**
   - 描述: `system_travel.launch.py` 与 `nav2_travel.yaml` 已在仓库内，但该模式当前不作为主开发方向。
   - 状态: 暂停

11. **[中等] GPS 路网仍需继续采集和精修**
   - 描述: 固定 ENU 原点与 dispatcher 路网规划已经软件实现，但 `campus_road_network.yaml` 仍只是 bootstrap 图，需要继续用车载 `/gnss` 采点扩图。
   - 状态: 待继续采集

12. **[中等] GPS 漂移仍会影响全局位姿与终点收敛**
   - 描述: 长距离单向运行时，单靠回环不足以约束全局漂移，因此仍依赖 GPS 因子质量、有效 offset 和户外数据质量。
   - 状态: GPS 因子已上线，现场数据不足

13. **[中等] 无 URDF**
   - 描述: 当前缺少完整 URDF / 仿真链，因此参数验证主要依赖实车。
   - 状态: 未开始

14. **[中等] 原地旋转轨迹不圆**
   - 描述: 机械侧左右轮输出不一致，狭窄区域旋转时风险较高。
   - 状态: 硬件限制

## 低优先级 / 工具链问题

15. **[低] Jetson 上 `gh` token 失效风险**
   - 描述: 已知 Jetson 侧 `gh` 曾出现登录失效；如果复发，可在已登录的 Windows 工作站执行 `gh pr create` / `gh pr merge` 规避。
   - 状态: 目前可用，但需留意

16. **[低] PGO 全局点云 RViz 可视化仍不完整**
   - 描述: 当前主链强调 `map -> odom` 与 `/pgo/optimized_odom`，但全局点云展示体验仍不是主维护目标。
   - 状态: 低优先级

17. **[低] FAST-LIO2 `world_cloud` 实用性有限**
   - 描述: 该输出在当前主链中不是核心依赖，可在后续资源优化时再评估。
   - 状态: 低优先级

18. **[低] 下位机 PID 急停倒转**
   - 描述: 急停逻辑会引起车轮明显反转。
   - 状态: 硬件 / 下位机问题

19. **[低] USB 2.0 接口限制**
   - 描述: 对部分高带宽外设扩展不友好。
   - 状态: 硬件限制

## 最近已修复

27. **[已修复] syncPackage 空点云段错误 (Issue #4)**
   - 现象: 雷达被遮挡或所有点超出范围时，`livox2PCL()` 返回空 cloud，`syncPackage()` 对空 `points` 调用 `.back()` 触发段错误
   - 影响链: FAST-LIO2 崩溃 → `odom → base_link` TF 丢失 → 系统定位失效
   - 修复: commit `9a193af` — `syncPackage()` 中增加空点云守卫，空帧直接丢弃
   - 状态: 已修复，已部署，GitHub Issue #4 已关闭（2026-03-31）

28. **[已修复] Startup GPS spread 门槛过严导致 corridor 无法启动**
   - 现象: 首轮实车测试中 `gps_global_aligner` / `gps_route_runner` 停在 `WAITING_FOR_STABLE_FIX`，系统其余部分正常
   - 根因: route 默认 `startup_fix_spread_max_m: 3.0`，但当前 GPS 设备 60 点窗口 spread 典型值 ~4.8m，无法满足
   - 修复: commit `d9b63dc` — 路线采集脚本默认从 `2.0` 放宽到 `5.0`，当前运行 route 从 `3.0` 改为 `5.0`
   - 状态: 已修正，待下次晴天复测验证（2026-03-31）

1. **[已修复] PGO 启动后 `map -> odom` 不建立**
   - 现象: 启动后持续刷 `Received out of order message`，没有关键帧，没有稳定 `map -> odom`，RViz 在 `map` fixed frame 下看起来像空白。
   - 根因: `pgo_node.cpp` 中同步状态 `last_message_time` 未初始化，第一对同步消息会被错误判定为 out-of-order。
   - 修复: 将 `last_message_time` 初始化为 `0.0`，确保第一对匹配消息被接受。
   - 状态: 已于 2026-03-18 合并到 `main`

2. **[已修复] GPS 导航主软件链缺失**
   - 现象: 历史版本只有 `GNSS -> PGO GPS factor`，没有把 GPS 目标交给 Nav2 的正式执行链。
   - 修复: 在 `feature/gps-navigation-v4` 上新增 `gps_waypoint_dispatcher`、`nav2_gps.yaml`、固定 ENU 原点、`system_nav_gps.launch.py` 与 `nav-gps` 模式。
   - 状态: 室内软件 smoke 已通过，等待室外最终验证

20. **[已升级] Corridor v1 终点几米级残差 → v2 独立 aligner 已部署**
   - 描述: v1 使用 body_vector 直线导航，受 yaw0 不确定性影响终点偏差 ~4m。
   - 状态: 已升级到 corridor v2（独立 global aligner 架构），v1 作为 baseline 保留
   - v2 当前状态（2026-03-26 收口）:
     - waypoint 1 已稳定到达
     - waypoint 边界 alignment 守卫已生效，不再换坏 alignment
     - **主问题已收敛为 GPS 路线采集/锚定方法**: startup GPS 带 ~2.5m 误差，单点锚定无法保证稳定到预定物理位置
     - 继续只调 Nav2 YAML 或小修 runner 已触及天花板，需重新设计锚定方案

21. **[已解决] Corridor v2 PGO handoff 门槛与现场频率不匹配**
   - 描述: v2 初版使用 PGO live handoff，但 PGO ~1Hz 更新频率达不到切换门槛。
   - 状态: **已通过架构变更解决** — 独立 global aligner 替代了 PGO handoff，不再需要切换门槛
   - 影响: 不再适用

22. **[中等] Controller / Planner 循环频率不达标**
   - 描述: Controller 反复报 `Control loop missed its desired rate`，Planner 降至 `~2Hz`。
   - 状态: 修正 v2 已将 controller 目标频率从 20Hz 降至 15Hz，减轻 CPU 压力
   - 根因: 当前 Jetson 上 costmap 更新 + TF 查询 + 点云处理的总计算量已接近瓶颈
   - 影响: TF extrapolation warnings、collision ahead 误报概率增加（但已通过降频缓解）

23. **[已修复] Corridor BT 文件已移除 Spin 但 runtime 仍执行 spin**
   - 描述: 本地和 Jetson 的 corridor BT XML 都不含 `Spin`，但 `behavior_server` 日志仍打印 `Running spin`
   - 根因: `default_nav_to_pose_bt_xml` 参数写在 `bt_navigator_navigate_to_pose_rclcpp_node` 下，不是 `bt_navigator` 下，导致 launch 注入无效
   - 修复: commit `d075c6b` 将参数移到正确的 `bt_navigator` 节点下
   - 状态: 已修复（2026-03-26）

24. **[根因已修复] 后段 `lio_odom` / `odom→base_link` 发散**
   - 描述: 多轮实车中第二段后半程 `odom→base_link` 开始连续大跳，导致位姿发散、导航失败
   - **根因已确认（2026-03-30）**: `lidar_processor.cpp:245` 点到平面 Jacobian 中 `hat()` 参数错误使用 `state.t_wi`（世界位置，~50m）而非 `state.t_il`（外参偏移，~0.04m）
     - 来源：fork 将原始 FAST-LIO2 的 `SKEW_SYM_MATRX` 宏改为 `Sophus::SO3d::hat()` 时变量名写错
     - 影响：旋转 Jacobian 随距离从原点增长被放大数百倍 → IESKF 旋转修正错误 → 地图旋转 → odom 发散
   - 修复: commit `e4945f4` — 一行修复 `state.t_wi` → `state.t_il`
   - 缓解措施保留（commit `308fe77`）: odom watchdog + ESKF 退化保护仍作为通用安全机制
   - 2026-03-31 更新: Jetson smoke test 通过；首轮现场测试系统正常启动（未触发 odom 发散），但因 startup GPS gate 过严未进入导航阶段，发散修复效果尚未在长距离行驶中验证
   - 状态: 根因已修复，待长距离实车验证

25. **[重要] GPS 路线采集/锚定方法不足以保证物理精度**
   - 描述: 当前 corridor GPS 路线依赖单个 `start_ref` + `launch_yaw_deg` 锚定。startup GPS 本身带 ~2.5m 误差，加上路线几何只在 ENU 域定义，导致 map 中生成的目标线系统性偏离用户期望的物理路径
   - 最新证据（session `2026-03-27-13-43-46`）:
     - `distance_to_start_ref=4.75m`（tolerance 15.0m 允许了过大偏差起跑）
     - frozen alignment 下第二段 map 投影 dx=+3.28m 侧偏
     - translation-only aligner 持续拒绝修正（delta 8.88~9.50m > 8.0m 阈值）
   - Calibration handshake 尝试（commit `308fe77`）:
     - 部署航点渐进标定机制：runner 到达 waypoint 后请求 aligner 用静止 GPS 样本重新标定
     - session `2026-03-27-18-22-31` 结果：wp1 标定失败，GPS 均值与记录航点差 30.35m，执行 `CALIBRATION_FALLBACK`
     - 结论：当前路线中 wp1 不具备可靠标定锚点价值
   - 状态: 2026-03-27 再次确认为当前主瓶颈，需回 Step 8 重新复审锚定方案
   - 候选方向: 多点刚体配准 / map 物理点位路线 / 连续轨迹采集

26. **[已知] Translation-only aligner 未能纠回启动锚定误差**
   - 描述: commit `94862d7` �� global aligner 改为固定 bootstrap 旋转、只估计平移的模式，意图在运行中逐步修正启动锚定偏差
   - 实车结果（session `2026-03-27-13-43-46`）:
     - 运行期持续打印 `Rejecting raw GPS alignment: bootstrap translation delta 8.88m > 8.00m`
     - 没有成功发布新的可信 runtime 平移修正
   - 根因: 启动锚定本身偏差已超过 aligner 的 `max_bootstrap_translation_delta_m: 8.0` 阈值
   - 状���: 已记录，不单独修 — 属于 #25 GPS 锚定主问题的下游表现

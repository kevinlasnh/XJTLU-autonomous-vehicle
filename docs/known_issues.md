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

2. **[重要] 室外 GNSS RF / fix 质量仍待验证**
   - 描述: GPS 天线馈线已更换，设备枚举正常，但有效 fix 质量和长时间室外稳定性还没有重新验证。
   - 状态: 等待晴天实测
   - 影响: `gnss_offset.txt` 生成、GPS 因子评测、`nav-gps` 实车验证

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

9. **[重要] 代价地图障碍残留 / 消散慢**
   - 描述: 移除障碍后，代价地图上的代价值清除不够快。
   - 状态: 通过最大障碍物高度 `1.5m` 有部分缓解

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

1. **[已修复] PGO 启动后 `map -> odom` 不建立**
   - 现象: 启动后持续刷 `Received out of order message`，没有关键帧，没有稳定 `map -> odom`，RViz 在 `map` fixed frame 下看起来像空白。
   - 根因: `pgo_node.cpp` 中同步状态 `last_message_time` 未初始化，第一对同步消息会被错误判定为 out-of-order。
   - 修复: 将 `last_message_time` 初始化为 `0.0`，确保第一对匹配消息被接受。
   - 状态: 已于 2026-03-18 合并到 `main`

2. **[已修复] GPS 导航主软件链缺失**
   - 现象: 历史版本只有 `GNSS -> PGO GPS factor`，没有把 GPS 目标交给 Nav2 的正式执行链。
   - 修复: 在 `feature/gps-navigation-v4` 上新增 `gps_waypoint_dispatcher`、`nav2_gps.yaml`、固定 ENU 原点、`system_nav_gps.launch.py` 与 `nav-gps` 模式。
   - 状态: 室内软件 smoke 已通过，等待室外最终验证

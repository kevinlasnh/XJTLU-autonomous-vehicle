# FYP Autonomous Vehicle - Progress Log

**最后更新**: 2026-03-21

---

## 当前状态

**Corridor v1 已完成首次室外验证，可作为 baseline 继续增量开发。**

| 项目 | 状态 |
|------|------|
| 方案 | 固定 Launch Pose 两点 corridor 自动导航 |
| 分支 | `feature/gps-corridor-launch` |
| Jetson 部署 | 完成 |
| 室内 smoke | 通过 |
| 首次室外验证 | 通过（到达目标附近，末端几米级误差） |
| 主要 blocker | 终点精度不足 |

---

## 最近完成 (2026-03-21)

- [x] 用户需求收敛：固定启动点/朝向 → 两点采集 → launch 直启 → 自动导航
- [x] 否决 v7 scene graph 主链，确立 corridor v1 为新基线
- [x] Jetson 代码落地：
  - `system_gps_corridor.launch.py`
  - `gps_corridor_runner_node.py`
  - `collect_two_point_corridor.py`
- [x] 构建通过：`gps_waypoint_dispatcher` + `bringup`
- [x] 室内 smoke 通过
- [x] 采点脚本修正：自动拉起/收掉 `nmea_navsat_driver`
- [x] **首次室外实车：车辆成功从 Launch Pose 出发，到达目标附近**
- [x] Jetson docs 已同步（commands, architecture, workflow, gps_planning, devlog）

---

## 当前 Blockers

1. **终点精度不足** — 到达目标附近但有几米级误差
   - 可能原因：GNSS 会话漂移、IMU 初始 yaw ��确定性
   - 需要更多室外数据来定位主因

---

## Next Steps

1. 继续室外测试，收集多次数据评估重复性
2. 记录每次的：起点误差、末端误差、会话间变化
3. 根据数据判断主要误差来源，决定改进方向：
   - 启动位一致性强化
   - 简化版 yaw 校准
   - 目标点会话对齐优化
4. corridor v1 作为 stable baseline 保留，增量改进

---

## 历史摘要

2026-03-21 当天完成了从概念到实车验证的完整迭代：

1. 锁定"两点直线 GPS 导航"概念
2. 否决 v7，收敛为 launch 直启 corridor
3. Codex 部署到 Jetson + 室内 smoke
4. 首次室外验证通过

v7 scene graph 方案（分支 `feature/gps-route-ready-v2`）已废弃，不再作为开发主线。

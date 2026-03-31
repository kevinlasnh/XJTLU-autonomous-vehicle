# FYP 自主导航车辆文档索引

> 最后更新: 2026-03-31

## 当前系统摘要

- 当前主运行模式: `make launch-explore`
- **室内无 GPS 点击点导航**: `make launch-indoor-nav`（RViz 发目标，无需 GNSS）
- GPS 融合模式已部署: `make launch-explore-gps`
- GPS 目标导航模式已在 `feature/gps-navigation-v4` 完成软件部署并通过室内 smoke: `make launch-nav-gps`
- **GPS Corridor v2 已切换到 MPPI 控制器（`gps-mppi` 分支）**: `make launch-corridor`
  - 控制器从 RotationShim + RPP 切换到 MPPI（commit `9d71823`），获得原生采样避障能力
  - Costmap 高度过滤调优（commit `ce5226f`）：只保留车体高度范围内障碍，消除假障碍
  - 障碍地图范围扩展到 15m（commit `2c2b8e6`），匹配 Livox MID360 量程
  - **室内实车验证通过**：MPPI 成功��开人体、走廊整圈巡航无漂移、内存稳定 ~2.67GB
  - FAST-LIO2 Jacobian 修复（commit `e4945f4`）+ syncPackage 空点云守卫（commit `9a193af`，Issue #4）均已包含
  - 当前状态：**室内无 GPS 导航已验证通过；后续开发统一在 `gps-mppi` 分支**
- 当前导航与建图主栈: FAST-LIO2 + PGO + Nav2 (MPPI)
- 运行时数据根目录: `~/XJTLU-autonomous-vehicle/runtime-data`
- 参数统一入口: `src/bringup/config/master_params.yaml`
- 日志统一入口: `scripts/launch_with_logs.sh`

## 核心文档

| 主题 | 文件 |
|------|------|
| 系统结构与数据流 | [architecture.md](architecture.md) |
| 常用命令 | [commands.md](commands.md) |
| 开发规范 | [conventions.md](conventions.md) |
| 执行工作流 | [workflow.md](workflow.md) |
| 已知问题与当前阻塞 | [known_issues.md](known_issues.md) |
| 硬件规格参数 | [hardware_spec.md](hardware_spec.md) |

## 技术深度文档

| 主题 | 文件 |
|------|------|
| FAST-LIO2 工作原理 | [knowledge/fastlio2.md](knowledge/fastlio2.md) |
| PGO + GPS Factor | [knowledge/pgo.md](knowledge/pgo.md) |
| Nav2 调参与运行约束 | [knowledge/nav2_tuning.md](knowledge/nav2_tuning.md) |
| GPS 全局导航与路网规划 | [knowledge/gps_planning.md](knowledge/gps_planning.md) |

## 开发日志

| 时间段 | 文件 |
|--------|------|
| 2025-11 | [devlog/2025-11.md](devlog/2025-11.md) |
| 2025-12 | [devlog/2025-12.md](devlog/2025-12.md) |
| 2026-03 | [devlog/2026-03.md](devlog/2026-03.md) |

## 仓库级辅助文档

| 文件 | 用途 |
|------|------|
| [`../README.md`](../README.md) | 仓库总览与快速开始 |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | 贡献流程与 PR 要求 |
| [`../CLAUDE.md`](../CLAUDE.md) | Agent 侧执行约束摘要 |

## 归档说明

- `docs/devlog/legacy/` 为历史原始文档归档，仅保留参考价值，不按当前结构继续维护。
- `src/third_party/` 下的上游文档不属于本项目自维护文档范围。

## 维护原则

1. 代码、launch、参数、系统环境、流程有变动时，同步更新对应文档。
2. 当月开发记录统一追加到 `devlog/YYYY-MM.md`。
3. 新问题或状态变化同步到 `known_issues.md`。
4. 命令和流程文档必须反映当前仓库真实可执行状态，而不是历史习惯。

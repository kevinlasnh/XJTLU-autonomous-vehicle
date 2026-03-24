# FYP 自主导航车辆文档索引

> 最后更新: 2026-03-24

## 当前系统摘要

- 当前主运行模式: `make launch-explore`
- GPS 融合模式已部署: `make launch-explore-gps`
- GPS 目标导航模式已在 `feature/gps-navigation-v4` 完成软件部署并通过室内 smoke: `make launch-nav-gps`
- **GPS Corridor v2 独立 Global Aligner 架构已在 `gps` 分支部署**: `make launch-corridor`
  - waypoint 1 已稳定到达，运行期微调修正 v2 已部署
  - 当前等待现场 GPS fix 后继续实车验证
- 当前导航与建图主栈: FAST-LIO2 + PGO + Nav2
- 运行时数据根目录: `~/fyp_runtime_data`
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

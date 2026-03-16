# FYP 自主导航车辆 — 项目文档

> 最后更新: 2026-03-16

## 快速入口

| 我想... | 看这个 |
|---------|--------|
| 了解系统架构 | [architecture.md](architecture.md) |
| 查操作命令 | [commands.md](commands.md) |
| 看开发规范 | [conventions.md](conventions.md) |
| 看工作流指南 | [workflow.md](workflow.md) |
| 查已知问题 | [known_issues.md](known_issues.md) |

## 技术深度文档

| 主题 | 文件 |
|------|------|
| FASTLIO2 算法详解 | [knowledge/fastlio2.md](knowledge/fastlio2.md) |
| PGO 位姿图优化详解 | [knowledge/pgo.md](knowledge/pgo.md) |
| Nav2 参数调优记录 | [knowledge/nav2_tuning.md](knowledge/nav2_tuning.md) |
| GPS 全局路径规划设计 | [knowledge/gps_planning.md](knowledge/gps_planning.md) |

## 开发日志

| 时间段 | 文件 |
|--------|------|
| 2025年11月 | [devlog/2025-11.md](devlog/2025-11.md) |
| 2025年12月 | [devlog/2025-12.md](devlog/2025-12.md) |
| 2026年3月 | [devlog/2026-03.md](devlog/2026-03.md) |

## 原始文档归档

原始 7 个开发文档已 1:1 备份至 [devlog/legacy/](devlog/legacy/)，仅供参考，不再更新。

## 文档维护约定

- **Claude 自动维护**: 每次 session 结束时更新相关文档
- **开发日志**: 按月份追加到 `devlog/YYYY-MM.md`
- **已知问题**: 发现新问题或解决旧问题时更新 `known_issues.md`
- **命令手册**: 新增常用命令时更新 `commands.md`
- **参数调优**: 调整参数时更新 `knowledge/nav2_tuning.md`

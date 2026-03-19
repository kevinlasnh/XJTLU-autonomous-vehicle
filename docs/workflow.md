# 项目工作流指南

> 当前标准: 代码与文档改动都走分支 + PR，`main` 只接收已验证结果。

## 1. 角色分工

| 角色 | 责任 |
|------|------|
| kevinlasnh | 提需求、做最终决策、执行实车测试 |
| Claude | 架构、调研、方案设计、结果复审 |
| Codex | 执行实现、构建验证、提交、PR、文档同步 |
| 团队开发者 | 按同样分支和 PR 规则协作 |

## 2. 标准开发流

### 2.1 会话开始

```bash
ssh jetson@100.97.227.24
cd ~/fyp_autonomous_vehicle
git status
git checkout main
git pull --ff-only
git branch -v
git log --oneline -5
```

如果上次已经构建过并准备继续调试：

```bash
source install/setup.bash
```

### 2.2 创建分支

```bash
git checkout -b feature/your-topic
```

允许的前缀：

- `feature/`
- `fix/`
- `tune/`
- `docs/`
- `experiment/`

### 2.3 研究与实施

1. 先核对真实代码状态、launch 链和当前参数。
2. 再做改动，不凭历史记忆直接写。
3. 如果改动涉及系统行为，先确认影响的运行模式。

### 2.4 构建

```bash
colcon build --packages-select <pkg> --symlink-install --parallel-workers 1
source install/setup.bash
```

规则：

1. `--parallel-workers 1` 是硬性要求。
2. 每次构建后都要重新 `source install/setup.bash`。
3. Python 包虽可借助 `--symlink-install` 免重编，但仍要做运行验证。

### 2.5 启动与验证

按改动范围选择合适模式：

```bash
make launch-slam
make launch-explore
make launch-explore-gps
make launch-travel
```

验证时至少检查：

- 相关节点是否都在线
- 关键 topic 是否有数据
- `map -> odom -> base_link` TF 是否完整
- session 日志是否落到 `~/fyp_runtime_data/logs/latest/`

实车相关改动需要补上人工现场测试结论。

## 3. AI 协作流

当任务由 Claude + Codex 共同执行时，控制面不在这个仓库内，而在 PC command-center 仓库中维护：

- `task_plan.md`
- `findings.md`
- `progress.md`

这个 Jetson 仓库负责真实实现、构建、运行和归档文档。

## 4. 提交与 PR

### 4.1 提交

```bash
git add path/to/file1 path/to/file2
git commit -m "Explain what changed and why"
git push -u origin feature/your-topic
```

要求：

1. 只添加具体文件。
2. 不提交无关改动。
3. Commit message 用英文。

### 4.2 PR 与合并

```bash
gh auth status
gh pr create
gh pr merge --merge --delete-branch
git checkout main
git pull --ff-only
git fetch --prune
```

如果 Jetson 上 `gh auth status` 失败，可以在已登录 GitHub CLI 的本地工作站上对同一分支执行 PR 和 merge，然后再让 Jetson 回拉 `main`。

## 5. 文档触发规则

以下变化发生时，不允许只改代码不改文档：

| 变化类型 | 最少要同步的文档 |
|----------|------------------|
| 节点源码 | `devlog`、相关 `knowledge`、必要时 `architecture.md` |
| launch 文件 | `devlog`、`commands.md`、`workflow.md`、必要时 `architecture.md` |
| YAML 参数 | `devlog`、对应知识文档 |
| 脚本与工具 | `devlog`、`commands.md`、必要时 `workflow.md` |
| bug 修复 / 新 bug | `devlog`、`known_issues.md` |
| 系统环境变化 | `devlog`、`commands.md`、`workflow.md` |
| 工作流变化 | `workflow.md`、`conventions.md` |

## 6. 会话结束检查表

会话在以下项目全部完成前不算收口：

1. 改动已验证。
2. 相关文档已同步。
3. 分支已推送。
4. PR 已创建并合并。
5. Jetson 已回到最新 `main`。
6. 如果有新的系统事实、问题或阻塞，已写入开发日志和问题追踪。

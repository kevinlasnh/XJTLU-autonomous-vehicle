# WORKFLOW.md — Development Workflow v6

> **Source of truth** for the FYP autonomous vehicle project workflow.
> Claude and Codex 各自的职责摘要见 `CLAUDE.md` 和 `AGENTS.md`，完整流程以本文件为准。
> 如需修改工作流，直接编辑本文件。

---

## Agents

| Agent | 身份 | 工具 |
|-------|------|------|
| CC (Claude Code) | 架构师 + 文档师 | 本地代码编辑、SSH、调研、子代理 |
| Codex | 部署师 | 本地代码编辑、SSH、编译、系统测试 |
| User (kevinlasnh) | 决策者 | 需求定义、实车测试、物理评审 |

---

## SESSION 开始（Step 0）

```
                  哪个 Agent 启动？
                        │
          ┌─────────────┼─────────────┐
          ▼                           ▼
      Claude (CC)                  Codex
          │                           │
          ▼                           ▼
   0. 读 L2 文件                0. 读 L2 文件
      git diff 看增量              git diff 看增量
      全文看断点                    全文看断点
          │                           │
          ▼                           ▼
   0a. 有断点？                 0a. 有断点？
       ├── 有 → 跳到断点            ├── 有 → 跳到断点
       │   CC 阶段继续              │   Codex 阶段继续
       │                            │
       └── 无 → step 1              └── 无 → 问用户：
                                         "CC 写好计划了吗？"
                                         ├── 有 → 读计划 → step 17
                                         └── 没有 → 等 CC 先写
```

---

## CC 初始化阶段（Step 1-7）

| Step | 执行者 | 动作 |
|------|--------|------|
| 1 | CC | SSH 到 Jetson |
| 2 | CC | 检查仓库状态（git status / branch / log） |
| 3 | CC | 检查整车硬件状态（运行 check-jetson-hardware skill） |
| 4 | CC | source install/setup.bash |
| 5 | CC | 问用户："你想让我干嘛？" |
| 6 | User | 描述需求 |
| 7 | CC | 创建/切换分支 |

---

## Claude 调研阶段（Step 8-16）

| Step | 执行者 | 动作 |
|------|--------|------|
| 8 | CC | 读当前分支所有相关代码，理解真实开发现状 |
| 9 | CC | 加载 Superpowers skill（强化思维） |
| 10 | CC | 审核评估用户需求 |
| 11 | CC | 按任务难度/复杂度，派适当数量子代理调研 |
| 12 | CC | 等调研结果返回 |

### Claude 自我迭代循环（Step 13）

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  13. 自审计划：                                      │
│      - 是否最佳满足用户需求？                         │
│      - 架构方法是否最佳？                             │
│      - 基于代码库 + 联网信息，正确性是否最佳？         │
│                                                     │
│      ├── 不满意 → 回到 9                             │
│      │   重新加载 Superpowers                        │
│      │   再派子代理补充调研                            │
│      │                                              │
│      └── 满意 → 跳出循环                             │
│                                                     │
└─────────────────────────────────────────────────────┘
```

| Step | 执行者 | 动作 |
|------|--------|------|
| 14 | CC | 输出计划给用户审阅 |
| 15 | User | 审阅确认 |
| 16 | CC | 调用 planning-with-files 记录计划 |

**CC 在此等待，直到用户在 step 32 喊回来写文档。**

---

## Codex 部署性审查阶段（Step 17-20）

| Step | 执行者 | 动作 |
|------|--------|------|
| 17 | Codex | 全面阅读 CC 写的计划 + 所有相关文档 |
| 18 | Codex | 阅读代码库中最相关的代码 |

### Codex 部署性审查循环（Step 19）

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  19. 判断：该计划是否具备可部署性？                    │
│      （不审架构，只审实战可部署性）                     │
│                                                     │
│      ├── 可部署 → 告诉用户："计划可部署，等你指示"     │
│      │                                              │
│      └── 不可部署 → 在保留原架构前提下微调计划         │
│          使用 planning-with-files 记录微调            │
│          → 回到 19 重新审查                          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

| Step | 执行者 | 动作 |
|------|--------|------|
| 20 | User | 确认："去部署"→ **计划锁定** |

---

## Codex 部署+系统测试阶段（Step 21-25）

### Codex 部署+测试循环

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  21. 本地改代码（PC 上直接改）                        │
│      ▼                                              │
│  22. git push 到 GitHub                             │
│      ▼                                              │
│  23. SSH 到 Jetson → git pull                       │
│      ▼                                              │
│  24. colcon build + source install/setup.bash        │
│      ▼                                              │
│  25. 从系统启动点启动整个系统                          │
│      验证每个部件都正常运行                            │
│                                                     │
│      ├── 通过 → 告诉用户："可以实车测试"              │
│      └── 失败 → 回到 21，循环直到通过                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 实车测试+分析阶段（Step 26-30）

| Step | 执行者 | 动作 |
|------|--------|------|
| 26 | User | 实车测试：手动启动整车，运行测试 |
| 27 | User | 得出两个结果：a) 物理运行状态人工评审 b) 系统全量日志 |
| 28 | User | 告诉 Codex：物理评审结果 + 改进意见 |
| 29 | Codex | 综合分析：接收物理评审 + SSH 读最新全量日志 → 输出问题和改进方向 |

### Step 30: 关键判断

```
[User] 30. 判断问题性质
        │
        ├── 架构问题 → 回到 8（Claude 重新调研，全流程重走）
        │
        ├── 小问题 → 回到 21（Codex 直接改，循环到再次实车测试）
        │
        └── PASS ↓
```

---

## PASS 后交接（Step 31-32）

| Step | 执行者 | 动作 |
|------|--------|------|
| 31 | Codex | 调用 planning-with-files 更新 L2 文件（记录测试通过） |
| 32 | User | 告诉 CC 进入文档阶段。触发条件：a) PASS 了 b) 今天太晚了要下班了 |

---

## CC 文档阶段（Step 33-38）

| Step | 执行者 | 动作 |
|------|--------|------|
| 33 | CC | 读 L2 文件（git diff 看 Codex 更新了什么） |
| 34 | CC | 读 docs/index.md，了解当前文档结构 |
| 35 | CC | 判断：基于当前开发进度，需要新增文档类型吗？需要则创建 + 更新 index.md |
| 36 | CC | 更新所有相关文档（按触发矩阵判断哪些 docs 要改） |
| 37 | CC | 调用 planning-with-files 记录进度 |
| 38 | CC | git commit + push |

---

## SESSION 结束

---

## 断点机制（任何步骤均可触发）

用户在任意步骤说 **"停一下"** / **"先到这"** / **"去吃饭"** 等：

1. 当前 Agent 调用 **planning-with-files** 更新 L2 文件
   - `progress.md` 记录断点位置（哪一步、做到哪了）
   - `task_plan.md` 标记完成/未完成步骤
   - `findings.md` 记录新发现（如有）
2. 更新 **devlog**（docs/devlog/YYYY-MM.md）
3. **git commit + push**

下次 SESSION 开始时，任何 Agent 读 L2 → 发现断点 → 跳到对应步骤继续。

---

## 关键规则

- **本地改代码，Jetson 只做编译和运行**
- **分支命名**：直接用描述名（`gps`、`nav-tuning`、`lidar-fix`），不加前缀
- **commit message**：英文，what + why
- **colcon build 必须 `--parallel-workers 1`**（Jetson 内存限制）
- **build 后必须 `source install/setup.bash`**
- **不改 YAML 参数除非记录原因**
- **不改 src/third_party/**
- **PR 合并策略另行决定**

---

## 文档触发矩阵

| 变化类型 | 必须检查和更新的文档 |
|----------|---------------------|
| C++/Python 节点源码 | devlog, knowledge/（算法变化时）, architecture.md（数据流变化时） |
| Launch 文件 | devlog, commands.md, architecture.md, workflow.md |
| Makefile | devlog, commands.md, workflow.md |
| YAML 参数 | devlog, 对应 knowledge 文档 |
| Bug 修复 | devlog, known_issues.md |
| 新发现 Bug | devlog, known_issues.md |
| 新增/删除 ROS2 包 | devlog, architecture.md, commands.md |
| 脚本/工具变更 | devlog, commands.md, workflow.md |
| GPS/GNSS 相关 | devlog, gps_planning.md, pgo.md |
| 硬件变更 | devlog, architecture.md, known_issues.md |
| 工作流/规范变更 | workflow.md, conventions.md |
| 物理测试结论 | devlog, nav2_tuning.md, known_issues.md |
| 新月份开始 | 创建 devlog/YYYY-MM.md, 更新 index.md |

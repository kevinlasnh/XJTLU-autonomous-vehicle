# 贡献指南

本文档面向这个仓库的工程维护者。当前标准流程以 Jetson 代码仓为执行面，以 GitHub PR 为唯一合并入口。

## 开始前

```bash
ssh jetson@100.97.227.24
cd ~/XJTLU-autonomous-vehicle
git status
git checkout main
git pull --ff-only
```

首次部署或新机器初始化：

```bash
make setup
make build
source install/setup.bash
bash scripts/init_runtime_data.sh
```

## 标准开发流程

1. 创建分支

```bash
git checkout -b feature/your-topic
```

2. 修改代码或文档。

3. 构建并验证

```bash
colcon build --packages-select <pkg> --symlink-install --parallel-workers 1
source install/setup.bash
```

4. 如果改动影响系统运行，启动对应模式验证：

```bash
make launch-slam
make launch-explore
make launch-explore-gps
make launch-travel
```

5. 提交时只添加具体文件：

```bash
git add path/to/file1 path/to/file2
git commit -m "Explain what changed and why"
```

6. 推送分支：

```bash
git push -u origin feature/your-topic
```

7. 创建和合并 PR：

```bash
gh auth status
gh pr create
gh pr merge --merge --delete-branch
git checkout main
git pull --ff-only
git fetch --prune
```

如果 Jetson 上 `gh auth status` 失败，可以在已登录 GitHub CLI 的受信任工作站上对同一分支完成 PR 操作，然后再让 Jetson `git pull` 同步结果。

## 分支命名

- `feature/xxx`
- `fix/xxx`
- `tune/xxx`
- `docs/xxx`
- `experiment/xxx`

## 提交与 PR 要求

1. 不要直接推送到 `main`。
2. Commit message 使用英文，写明 what + why。
3. 不要使用 `git add -A` 或 `git add .`。
4. PR 必须写清楚：
   - 改了什么
   - 为什么改
   - 怎么测的
   - 影响哪些层

## 文档要求

代码、launch、参数、系统配置、工作流发生变化时，必须同步更新相关文档。
文档分 CN（中文）和 EN（英文）两个目录，**两个目录必须同时更新**。

最常见的同步目标：

- `docs-CN/devlog/YYYY-MM.md` + `docs-EN/devlog/YYYY-MM.md`
- `docs-CN/commands.md` + `docs-EN/commands.md`
- `docs-CN/workflow.md` + `docs-EN/workflow.md`
- `docs-CN/architecture.md` + `docs-EN/architecture.md`
- `docs-CN/known_issues.md` + `docs-EN/known_issues.md`
- `docs-CN/knowledge/*.md` + `docs-EN/knowledge/*.md`

## 不变规则

1. YAML 参数改动必须记录原因。
2. 构建必须使用 `--parallel-workers 1`。
3. 每次构建后都要重新 `source install/setup.bash`。
4. `src/third_party/navigation2` 不作为项目自定义开发区。

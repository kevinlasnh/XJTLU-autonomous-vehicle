# 贡献指南

## 环境搭建

```bash
ssh jetson@100.97.227.24
cd ~/fyp_autonomous_vehicle
make setup
make build
source install/setup.bash
```

## 开发流程

1. 从 main 创建分支: `git checkout -b feature/你的功能`
2. 修改代码，确保 `colcon build` 通过
3. 提交: `git add <具体文件>` + `git commit -m "描述改动"`
4. 推送: `git push -u origin feature/你的功能`
5. 在 GitHub 上创建 PR，填写模板
6. 等待 @kevinlasnh Code Review

## 分支命名

- `feature/xxx`
- `fix/xxx`
- `tune/xxx`
- `docs/xxx`
- `experiment/xxx`

## 规则

1. **NEVER** 直接 push 到 main
2. **NEVER** 修改 YAML 参数不写注释说明
3. **ALWAYS** 用 `--parallel-workers 1` 编译
4. **ALWAYS** 在 PR 里说明测试方法
5. Commit message 用英文，描述每个文件的改动

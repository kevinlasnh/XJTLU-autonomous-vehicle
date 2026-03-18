# 项目工作流指南

> 本文档描述 FYP 自主导航车辆项目的完整开发工作流，对标公司级 ROS2 项目管理标准。

---

## 一、团队角色与分工

| 角色 | 人员 | 职责 |
|------|------|------|
| 项目负责人 | kevinlasnh | 需求定义、Code Review、实车测试、最终决策 |
| AI 开发助手 | Claude Code | SSH 远程编码、构建、调试、文档维护 |
| AI 执行助手 | Codex | 批量迁移、重构等大规模操作 |
| 开发者 | 暑期学弟 (2026 夏) | 分支开发、提交 PR、参与测试 |

**核心原则**: kevinlasnh 不直接写代码，所有代码修改通过 AI agent 或团队开发者完成。

---

## 二、环境搭建（新成员必读）

### 2.1 SSH 连接

```bash
# 局域网内
ssh jetson@<jetson-ip>

# 非局域网（通过 Tailscale）
# 1. 下载 Tailscale: https://tailscale.com/download
# 2. 登录（账号联系 Kevin）
# 3. 连接
ssh jetson@100.97.227.24
```

### 2.2 首次构建

```bash
cd ~/fyp_autonomous_vehicle

# 拉取第三方依赖（Nav2, slam_toolbox）+ 安装 rosdep
make setup

# 全量构建（约 20-30 分钟）
make build

# Source 工作空间
source install/setup.bash

# 验证
ros2 pkg list | grep bringup
```

### 2.3 运行时数据初始化

```bash
# 首次部署需要初始化运行时数据目录
bash scripts/init_runtime_data.sh

# 验证
ls ~/fyp_runtime_data/
# 应包含: config/ gnss/ maps/ planning/
```

---

## 三、日常开发流程

### 3.1 分支管理

```
main (受保护，需 PR + Review)
├── feature/xxx    新功能开发
├── fix/xxx        Bug 修复
├── tune/xxx       参数调优
├── docs/xxx       文档更新
└── experiment/xxx 实验性改动
```

### 3.1.1 铁律：绝对不在 main 上直接改代码

**开机第一件事**:
On branch feature/unified-params
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   src/bringup/launch/system_explore.launch.py
	modified:   src/bringup/launch/system_explore_gps.launch.py
	modified:   src/bringup/launch/system_slam.launch.py
	modified:   src/bringup/launch/system_travel.launch.py
	modified:   src/perception/fastlio2/launch/lio_no_rviz.py
	modified:   src/perception/fastlio2/src/lio_node.cpp
	modified:   src/perception/pgo_gps_fusion/launch/pgo_launch.py
	modified:   src/perception/pgo_gps_fusion/src/pgo_node.cpp
	modified:   src/sensor_drivers/gnss/gnss_calibration/launch/gnss_calibration_launch.py
	modified:   src/sensor_drivers/gnss/nmea_navsat_driver/launch/nmea_serial_driver.launch.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	 2
	src/bringup/config/master_params.yaml

no changes added to commit (use "git add" and/or "git commit -a")
  feature/gps-factor
* feature/unified-params
  main

如果发现当前在 main 分支且有未提交的改动:
Saved working directory and index state WIP on unified-params: 224ef1e Document persistent service shutdown validation
On branch feature/你的功能
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   src/bringup/launch/system_explore.launch.py
	modified:   src/bringup/launch/system_explore_gps.launch.py
	modified:   src/bringup/launch/system_slam.launch.py
	modified:   src/bringup/launch/system_travel.launch.py
	modified:   src/perception/fastlio2/launch/lio_no_rviz.py
	modified:   src/perception/fastlio2/src/lio_node.cpp
	modified:   src/perception/pgo_gps_fusion/launch/pgo_launch.py
	modified:   src/perception/pgo_gps_fusion/src/pgo_node.cpp
	modified:   src/sensor_drivers/gnss/gnss_calibration/launch/gnss_calibration_launch.py
	modified:   src/sensor_drivers/gnss/nmea_navsat_driver/launch/nmea_serial_driver.launch.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	 2
	src/bringup/config/master_params.yaml

no changes added to commit (use "git add" and/or "git commit -a")
Dropped refs/stash@{0} (469d112ba1ce03eea871ea16faa6539e6b39daf6)

**为什么**: 车上的代码仓就是生产环境。main 是所有人共用的稳定版本。在 main 上直接改代码，别人不知道你改了什么，出 bug 没法回滚，测试结果不可复现。

**即使只是试一下也要开分支。** experiment/xxx 分支就是干这个的。

### 3.1.2 学弟开发完整流程

1. SSH 到车上
2. 开机检查（每次必做）: git status + git checkout main + git pull
3. 创建分支: git checkout -b feature/你的功能名
4. 开发 + colcon build + 实车测试（必须有人在旁边随时急停）
5. 测试通过后: git add 具体文件 + git commit
6. git push -u origin feature/你的功能名
7. GitHub 上创建 PR，必须填写: 改了什么、为什么、怎么测的、影响哪些层
8. 等 Kevin Review，按反馈修改后再 push
9. Kevin 合并

**测试完觉得没问题 ≠ 真的没问题。** PR 里没写怎么测的一律打回。

### 3.2 标准开发流程

```
1. 创建分支
   git checkout main && git pull
   git checkout -b feature/你的功能

2. 开发
   修改代码 → colcon build → source → 测试

3. 提交
   git add <具体文件>          # 不要 git add -A
   git commit -m "描述改动"    # 英文，描述每个文件

4. 推送
   git push -u origin feature/你的功能

5. 创建 PR
   在 GitHub 上创建 Pull Request
   填写 PR 模板（改了什么、为什么、怎么测的）

6. Code Review
   等待 @kevinlasnh 审核
   根据反馈修改 → 追加 commit → 再次请求 review

7. 合并
   Review 通过后由 kevinlasnh 合并到 main
```

### 3.3 Claude 协作开发流程

当通过 Claude Code 开发时，流程简化为:

```
1. kevinlasnh 描述需求
2. Claude SSH 到 Jetson 执行开发
3. Claude 构建 + 初步验证
4. kevinlasnh 实车测试
5. Claude 提交代码 + 更新文档
6. 推送到 main（Claude 有直接推送权限）
```

---

## 四、构建规范

### 4.1 构建命令

```bash
# 全量构建
make build

# 按层构建（更快）
make build-sensor       # 传感器层
make build-perception   # 感知层
make build-planning     # 规划层
make build-navigation   # 导航层

# 单包构建（最快）
colcon build --packages-select <pkg> --symlink-install --parallel-workers 1

# 构建后必须 source
source install/setup.bash
```

### 4.2 构建注意事项

- **必须** `--parallel-workers 1`（Jetson 内存限制）
- **必须** `--symlink-install`（加速开发迭代）
- C++ 包修改后必须重新 build
- Python 包用 `--symlink-install` 后改源码即生效，无需重新 build
- 修改 CMakeLists.txt 后需要 `rm -rf build/<pkg>` 再 build

---

## 五、测试规范

### 5.1 构建测试（每次提交前）

```bash
# 至少确保修改的包能编译通过
colcon build --packages-select <你修改的包> --symlink-install --parallel-workers 1
```

### 5.2 实车测试

**测试前准备:**
1. 确认 PS2 手柄电池充足（7 号电池）
2. 一人负责随时按 X 键急停
3. 确认 RViz 中 fix_frame 设为 `map`
4. 先进入串口遥控模式 → 打开电机使能

**SLAM 模式测试:**
```bash
make launch-slam
# 预期: LiDAR 启动 → FASTLIO2 里程计 → SLAM Toolbox 建图 → RViz 显示地图
```

**Explore 模式测试:**
```bash
make launch-explore
# 预期: LiDAR + PGO → Nav2(延迟5秒) → RViz 设目标点 → 车辆自主避障行驶
```

**测试后:**
1. `make kill` 停止所有 ROS2 进程
2. 检查日志: `ls ~/fyp_runtime_data/logs/`
3. 确认充电电源关闭 + 电池关闭

### 5.3 紧急停车

| 方法 | 操作 | 优先级 |
|------|------|--------|
| PS2 X 键 | 关闭电机，车辆自由滑行 | 首选 |
| 物理红色按钮 | 按下断电，旋转释放恢复 | 情急时 |
| 终端 | `make kill` 或 `pkill -f ros2` | 远程 |

---

## 六、参数调优规范

### 6.1 规则

1. 调参前必须知道**为什么**要调这个参数
2. 少量调参: 注释掉原值，不要删除
3. 大量调参: 先备份 YAML 文件
4. 调完**立即**测试验证，不要隔几天
5. 在 YAML 中用 `# >>>>>>` 标注被调整的参数

### 6.2 记录

参数调整必须记录到 `docs/knowledge/nav2_tuning.md`，格式:
```
- 参数名: 新值 (原值: xxx)
- 原因: 为什么调
- 效果: 调了之后车的表现
- 日期: YYYY.MM.DD
```

---

## 七、文档维护

### 7.1 文档结构

```
docs/
├── index.md              入口导航
├── commands.md           操作命令手册
├── conventions.md        开发规范
├── architecture.md       系统架构
├── known_issues.md       已知问题追踪
├── workflow.md           本文件
├── knowledge/            技术深度文档
│   ├── fastlio2.md       FASTLIO2 算法
│   ├── pgo.md            PGO 算法
│   ├── nav2_tuning.md    Nav2 调优记录
│   └── gps_planning.md   GPS 规划设计
└── devlog/               开发日志
    ├── YYYY-MM.md        月度日志
    └── legacy/           原始文档归档
```

### 7.2 Claude 自动维护

每次开发 session 结束时，Claude 自动更新:

| 触发条件 | 更新文件 |
|---------|---------|
| 任何开发工作完成 | `devlog/YYYY-MM.md` 追加条目 |
| 发现或解决问题 | `known_issues.md` 更新状态 |
| 新增常用命令 | `commands.md` 追加 |
| 参数调整 | `knowledge/nav2_tuning.md` 追加 |
| 架构变更 | `architecture.md` 更新 |

### 7.3 开发日志格式

```markdown
## YYYY.MM.DD
### [层级标签]
- 做了什么
```

层级标签: `[项目管理]` `[传感器层]` `[感知层]` `[Nav2]` `[全局规划]` `[Launch]`

---

## 八、Git 规范

### 8.1 Commit Message

- **语言**: 英文
- **格式**: 简洁描述改动内容
- **粒度**: 按文件/功能分开 commit，不要一个 commit 包含所有改动

```bash
# 好的例子
git commit -m "Adjust DWB BaseObstacle.scale from 0.002 to 0.02 to fix obstacle avoidance"
git commit -m "Add PreferForward critic to prevent reverse driving"

# 坏的例子
git commit -m "update files"
git commit -m "fix stuff"
```

### 8.2 PR 规范

每个 PR 必须包含:
1. **改了什么** — 简述改动内容
2. **为什么改** — 改动原因
3. **怎么测的** — 测试方法（colcon build / 实车测试 / 仿真）
4. **影响范围** — 勾选受影响的层级

### 8.3 Git 代理处理

Jetson 配有 Clash 代理（127.0.0.1:7890），如果 push 失败:

```bash
# 临时绕过代理
git -c http.proxy= -c https.proxy= push

# 或永久禁用
git config --global --unset http.proxy
git config --global --unset https.proxy
```

---

## 九、运行时数据管理

```
~/fyp_runtime_data/        运行时数据根目录（不在 git 中）
├── config/
│   └── log_switch.yaml    各节点日志开关
├── gnss/
│   ├── gnss_offset.txt    GNSS 标定偏移
│   └── startid.txt        GNSS 起始 ID
├── logs/                  各节点运行日志
│   ├── fastlio2/
│   ├── pgo/
│   ├── twist_log/
│   └── ...
├── maps/                  地图文件
│   └── *.geojson
└── planning/
    └── angle_offset.txt   角度偏移标定
```

- 节点通过 `FYP_RUNTIME_ROOT` 环境变量定位此目录
- 默认值: `~/fyp_runtime_data`
- 此目录不纳入 git 管理

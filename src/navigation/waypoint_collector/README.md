# Waypoint Collector - 航点收集器

## 简介

`waypoint_collector` 是一个 ROS2 节点，用于在 RViz 中交互式地收集多个航点，然后通过 Nav2 的 `FollowWaypoints` Action 让机器人依次导航到各个航点。

## 功能特性

- ✅ 使用 RViz 的 **Publish Point** 工具点击地图添加中间航点
- ✅ 使用 RViz 的 **2D Goal Pose** 工具设定最终目标并触发导航
- ✅ 机器人会依次经过所有航点，最后到达最终目标
- ✅ 实时反馈当前正在前往的航点索引
- ✅ 导航完成后自动清空航点列表，可立即开始下一次任务
- ✅ **RViz 可视化**：绿色球体标记航点位置，编号显示顺序，黄色线连接路径

## 依赖

- ROS2 Humble
- Nav2 (navigation2)
- rclpy
- geometry_msgs
- nav2_msgs
- visualization_msgs

## 编译

```bash
cd ~/2025_FYP/car_ws
colcon build --packages-select waypoint_collector --symlink-install
source install/setup.bash
```

## 使用方法

### 1. 启动 Nav2 导航系统

确保你的 Nav2 系统已正常运行，包括 `waypoint_follower` 节点：

```bash
ros2 launch ros2_launch_file system_entire_launch_explore.py
```

### 2. 启动航点收集器

在新终端中运行：

```bash
source ~/2025_FYP/car_ws/install/setup.bash
ros2 run waypoint_collector waypoint_node
```

### 3. 在 RViz 中操作

#### 首先：添加 MarkerArray 显示（重要！）
1. 在 RViz 左侧 **Displays** 面板点击 **Add** 按钮
2. 选择 **By topic** → 找到 `/waypoint_markers` → 选择 **MarkerArray**
3. 点击 **OK** 添加
4. 现在你可以看到所有已添加的航点（绿色球体 + 编号）

#### 步骤 1：添加中间航点
1. 在 RViz 顶部工具栏点击 **"Publish Point"** 按钮
2. 在地图上点击你想要的中间航点位置
3. 每点击一次，终端会显示已添加的航点
4. **RViz 中会显示绿色球体和编号标记**

#### 步骤 2：设定最终目标并开始导航
1. 在 RViz 顶部工具栏点击 **"2D Goal Pose"** 按钮
2. 在地图上点击并**拖拽**设定最终目标位置和朝向
3. 机器人立即开始导航
4. **导航开始后，可视化标记会自动清除**

### 4. 观察导航过程

终端会实时显示：
- 当前正在前往的航点索引
- 导航完成状态
- 失败的航点（如果有）

## 操作流程图

```
[Publish Point] 点击位置 A  →  添加航点 #1
[Publish Point] 点击位置 B  →  添加航点 #2
[Publish Point] 点击位置 C  →  添加航点 #3
[2D Goal Pose] 点击位置 D   →  添加最终目标 + 开始导航
                            ↓
              机器人路径: A → B → C → D (最终目标)
```

## 终端输出示例

```
[waypoint_collector]: ==================================================
[waypoint_collector]: 航点收集器已启动 (FollowWaypoints)
[waypoint_collector]: ==================================================
[waypoint_collector]: 操作说明:
[waypoint_collector]:   1. 在 RViz 中使用 "Publish Point" 点击添加中间航点
[waypoint_collector]:   2. 使用 "2D Goal Pose" 设定最终目标并开始导航
[waypoint_collector]:   3. 机器人会依次经过所有航点到达最终目标
[waypoint_collector]: ==================================================
[waypoint_collector]: [+] 添加航点 #1: (2.50, 1.30)
[waypoint_collector]: [+] 添加航点 #2: (4.10, 2.80)
[waypoint_collector]: [+] 添加航点 #3: (5.00, 0.50)
[waypoint_collector]: [!] 收到最终目标: (6.20, 1.00)
[waypoint_collector]: [>] 开始导航，共 4 个航点
[waypoint_collector]: 航点列表:
[waypoint_collector]:   #1: (2.50, 1.30)
[waypoint_collector]:   #2: (4.10, 2.80)
[waypoint_collector]:   #3: (5.00, 0.50)
[waypoint_collector]:   #4: (6.20, 1.00)
[waypoint_collector]: 导航目标已接受，机器人开始移动...
[waypoint_collector]: [导航中] 正在前往航点 #1
[waypoint_collector]: [导航中] 正在前往航点 #2
[waypoint_collector]: [导航中] 正在前往航点 #3
[waypoint_collector]: [导航中] 正在前往航点 #4
[waypoint_collector]: ==================================================
[waypoint_collector]: 所有航点导航完成！
[waypoint_collector]: ==================================================
[waypoint_collector]: 可以继续添加新航点...
```

## 配置航点停留时间

如果需要在每个航点停留一段时间，可以修改 Nav2 参数文件中的 `waypoint_follower` 配置：

```yaml
waypoint_follower:
  ros__parameters:
    use_sim_time: False
    loop_rate: 20
    stop_on_failure: false
    waypoint_task_executor_plugin: "wait_at_waypoint"
    wait_at_waypoint:
      plugin: "nav2_waypoint_follower::WaitAtWaypoint"
      enabled: True
      waypoint_pause_duration: 1000  # 在每个航点停留 1000ms (1秒)
```

## 话题和 Action

### 订阅的话题
| 话题名 | 消息类型 | 说明 |
|--------|----------|------|
| `/clicked_point` | `geometry_msgs/PointStamped` | RViz Publish Point 工具发布的点 |
| `/goal_pose` | `geometry_msgs/PoseStamped` | RViz 2D Goal Pose 工具发布的目标 |

### 使用的 Action
| Action 名 | Action 类型 | 说明 |
|-----------|-------------|------|
| `/follow_waypoints` | `nav2_msgs/action/FollowWaypoints` | Nav2 航点跟随 Action |

### 发布的话题
| 话题名 | 消息类型 | 说明 |
|--------|----------|------|
| `/waypoint_markers` | `visualization_msgs/MarkerArray` | RViz 航点可视化标记 |

## 注意事项

1. **必须先启动 Nav2**：确保 `waypoint_follower` 节点已运行
2. **TF 树完整**：确保 `map` → `odom` → `base_link` 的 TF 链正常
3. **代价地图正常**：确保全局和局部代价地图正在更新
4. **航点顺序**：机器人会按照你点击的顺序依次前往各个航点

## 故障排除

### Action Server 不可用
```
[ERROR] FollowWaypoints Action Server 不可用！
```
**解决方案**：检查 Nav2 是否正常启动，运行 `ros2 action list` 确认 `/follow_waypoints` 存在

### 导航目标被拒绝
```
[ERROR] 导航目标被拒绝！
```
**解决方案**：检查航点是否在可达区域内，确保代价地图中没有障碍物阻挡

## 作者

FYP Team - 2025

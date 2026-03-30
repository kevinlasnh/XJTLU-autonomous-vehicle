# GNSS 全局路径规划器

## 当前定位

这个包保留了基于 GeoJSON + A* 的 GNSS 全局路径规划实验链，但它还没有接成当前主运行链里的生产级远距离导航能力。

当前生产环境里的 GPS 主链是：

```text
/fix -> gnss_calibration -> /gnss -> PGO GPS factor
```

而这个包更多用于继续推进：

- GPS 地图读取
- A* 节点级全局路径规划
- `/next_node` 发布实验

## 编译

```bash
cd ~/XJTLU-autonomous-vehicle
colcon build --packages-select gnss_global_path_planner --symlink-install --parallel-workers 1
source install/setup.bash
```

## 启动方法

### 1. 包级联调

```bash
ros2 launch gnss_global_path_planner gnss_combined_launch.py
```

该 launch 会拉起：

- `nmea_navsat_driver`
- `gnss_calibration`
- `global_path_planner`
- `global2local_tf`

### 2. 单独启动规划器

```bash
ros2 run gnss_global_path_planner global_path_planner.py
```

## 关键接口

| 接口 | 类型 | 说明 |
|------|------|------|
| `/gnss` | `sensor_msgs/NavSatFix` | 规划器订阅的校准后 GNSS 数据 |
| `/next_node` | `std_msgs/String` | 规划器发布的下一目标节点，经纬度格式为 `"lon,lat"` |

## 地图格式

地图使用 `GeoJSON`，当前仓库示例地图位于 `map/` 目录。

其中：

- `Point` 表示节点
- `LineString` 表示节点间连边

## 当前状态说明

1. 该包仍处于继续开发阶段。
2. 它不是 `make launch-explore-gps` 的生产主入口。
3. GPS -> Nav2 目标点转换仍未形成生产级闭环。

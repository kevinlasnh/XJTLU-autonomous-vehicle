# GNSS 全局路径规划器

## 项目简介
该 ROS2 包提供了一种基于 GNSS 数据的全局路径规划解决方案。利用 A* 算法生成从当前 GNSS 位置到用户定义目标点的路径，并通过发布下一个导航节点来引导机器人行驶。

## 安装步骤


 **编译项目**
```bash
cd ~/ros2_ws
colcon build --packages-select gnss_global_path_planner
source install/setup.bash
```

## 启动方法
### 1. 启动 GNSS 校准与路径规划
```bash
ros2 launch gnss_global_path_planner gnss_combined_launch.py
```
此命令会启动三个节点：
- `nmea_navsat_driver`：接收原始 NMEA 格式的 GNSS 数据。
- `gnss_calibration`：校准 GNSS 数据，消除静态误差。
- `global_path_planner`：路径规划节点，订阅校准后的 GNSS 数据，并发布下一导航点。

### 2. 单独启动路径规划器（调试用）
```bash
ros2 run gnss_global_path_planner global_path_planner.py
```

## 节点说明
- **`/gnss`**：订阅校准后的 GNSS 数据（NMEA 格式）。
- **`/next_node`**：发布下一个路径点的经纬度坐标（字符串格式 "lon,lat"）。

## 地图格式
地图使用 `GeoJSON` 格式存储，包含：
- **节点（Points）**：表示路径点的经纬度。
- **边（Linestrings）**：表示路径点之间的连接关系。

示例：
```json
{
  "type": "FeatureCollection",
  "features": [
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [120.7492308, 31.2788677]}},
    {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[120.7492308, 31.2788677], [120.7500000, 31.2790000]]}}
  ]
}
```

## 配置参数
- **`INTERPOLATION_THRESHOLD`**：插值节点的距离阈值（米）。
- **`PROXIMITY_THRESHOLD`**：到达判定的范围阈值（米）。
- **`YAW_THRESHOLD_FACTOR`**：偏航检测放大系数，用于调整偏航判断的阈值。
- **`INITIAL_GNSS`**：初始 GNSS 定位点，用于模拟环境。




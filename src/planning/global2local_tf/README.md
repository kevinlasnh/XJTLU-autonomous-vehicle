# Global to Local Coordinate Transformation System

## 简介
该系统将全球坐标系（经纬度）转换为局部直角坐标系，用于导航和路径规划。主要功能包括：
- **GNSS 数据处理**：计算原点。
- **磁力计方向计算**：计算当前朝向。
- **坐标变换**：将目标点的经纬度坐标转换为局部直角坐标。
- **路径规划与导航**：基于 A* 算法生成全局路径，并实时更新下一路径点。

---

## 系统架构
### 节点与功能
1. **`global2local_tf` 节点**：
   - 订阅 `/gnss` 和 `/mag`，计算原点和当前朝向。
   - 将目标点的经纬度坐标转换为局部直角坐标，并发布到 `/next_local`。

2. **`serial_reader` 节点**：
   - 从串口读取传感器数据，发布磁力计消息（`/mag`）、IMU 数据（`/imu/data_raw`）和里程计消息（`/odom`）。


---

## 启动
`ros2 launch global2local_tf global2local_tf.launch.py`


## 输入输出
### 输入话题
1. **`/gnss`**（`sensor_msgs/msg/NavSatFix`）：
   - GNSS 数据，包含经度、纬度和高度。

2. **`/mag`**（`sensor_msgs/msg/MagneticField`）：
   - 磁力计数据，用于计算当前朝向。

3. **`/next_node`**（`std_msgs/msg/String`）：
   - 下一路径点的经纬度坐标，格式为 `"longitude,latitude"`。

### 输出话题
1. **`/next_local`**（`std_msgs/msg/String`）：
   - 下一路径点的局部直角坐标，格式为 `"x,y"`。

2. **`/globalviz`**（`visualization_msgs/msg/MarkerArray`）：
   - 地图、路径、GNSS 当前位置和下一路径点的可视化数据。

3. **`/odom`**（`nav_msgs/msg/Odometry`）：
   - 里程计数据，包含位置和速度。

4. **`/imu/data_raw`**（`sensor_msgs/msg/Imu`）：
   - IMU 数据，包含四元数和角速度。

---

## 算法说明
### A* 路径规划
- 输入：起始点和目标点的经纬度坐标。
- 输出：从起始点到目标点的最优路径（节点 ID 列表）。
- 特性：
  - 使用球面距离（Haversine 公式）作为启发式函数。
  - 支持插值路径点，确保路径平滑。

### 坐标变换
- 原点：连续 3 次 GNSS 数据的平均值。
- 当前朝向：连续 20 次磁力计数据的平均值。
- 转换公式：
  - 将经纬度坐标转换为相对于原点的距离（米）。
  - 根据当前朝向进行旋转校正。

---

## 注意事项
1. **硬件要求**：
   - 需要支持串口通信的设备，用于读取传感器数据。
   - GNSS 模块需要稳定输出经纬度数据。

2. **调试建议**：
   - 使用 RViz 可视化地图和路径。
   - 检查 `/gnss`, `/mag`, `/next_local` 等话题的数据流。

3. **常见问题**：
   - 如果路径规划失败，请检查地图文件是否正确加载。
   - 如果坐标转换偏差较大，请校准原点和磁力计方向。

---

## 贡献
欢迎提交问题或 PR！如果你有任何改进建议，请随时联系作者。

---

## 许可证
本项目采用 [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) 开源许可证。
```

---

这个版本完全遵循 Markdown 格式，内容简洁明了，适合快速阅读和理解。如果还有其他需求，请告诉我！ 😊
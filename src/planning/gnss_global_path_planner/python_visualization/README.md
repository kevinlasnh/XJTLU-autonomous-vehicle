# python_visualization

这个目录下的脚本不是 ROS 2 节点，而是离线结果可视化工具。

## 当前用途

- 读取 GeoJSON 路网
- 对长边做插值并补近邻连接
- 读取校准后的 GNSS 轨迹日志
- 读取 A* 输出路径
- 用 Matplotlib 画出地图、GNSS 轨迹和规划路径

## 当前脚本

- `superviser_2.py`
  - 用于离线可视化
  - 依赖 `geojson`、`matplotlib`、`numpy`

## 当前限制

- 脚本底部仍保留旧的硬编码输入路径，指向历史工作区 `~/ros2_ws/...`。
- 因此它现在不能直接在当前 monorepo 状态下开箱即用，运行前需要先把文件路径改成当前数据位置。
- 这个目录不参与 `make launch-*` 主流程。

## 运行方式

在安装好依赖后，直接用 Python 运行:

```bash
python3 superviser_2.py
```

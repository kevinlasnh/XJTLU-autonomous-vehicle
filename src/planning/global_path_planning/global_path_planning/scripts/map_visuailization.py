import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt
import os
from pathlib import Path

# 获取当前脚本所在的目录
base_dir = Path(__file__).parent

# 使用相对路径
osm_file_path = base_dir.parent / "map" / "map_simplified2.osm"

# 从本地 OSM 文件加载图形数据
graph = ox.graph_from_xml(str(osm_file_path))

# 将图形数据转换为 GeoDataFrame
nodes, edges = ox.graph_to_gdfs(graph)

# 创建一个新文件夹来保存 Shapefiles（如果不存在）
output_folder = base_dir / "shapefiles"
output_folder.mkdir(exist_ok=True)

# 保存为 Shapefile 格式
edges.to_file(output_folder / "edges.shp")
nodes.to_file(output_folder / "nodes.shp")

# 可视化图形
fig, ax = ox.plot_graph(ox.project_graph(graph))
plt.show()

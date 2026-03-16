import os
import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

# 获取当前脚本所在的目录
base_dir = Path(__file__).resolve().parent

# 使用相对路径
osm_file_path = base_dir.parent / "map" / "map_simplified2.osm"  # 修改此处

# 从本地 OSM 文件加载图形数据
graph = ox.graph_from_xml(osm_file_path)

# 设置起始点和终点（根据用户提供的节点ID）
start_node = 9536946732  # 起点为9536946732
end_node = 8984639093    # 终点为9536946807

# A*路径规划
route = nx.astar_path(graph, start_node, end_node, weight='length')

# 打印路径
print("A*路径规划结果:")
print(route)

# 计算路径长度
total_length = 0
for u, v in zip(route[:-1], route[1:]):  # 遍历路径的边
    # 获取边的长度并累加
    edge_data = graph[u][v]
    total_length += edge_data[0]['length']  # 假设使用第一个边数据（有时会有多个数据）

# 输出路径的总长度
print(f"总路径长度：{total_length:.2f} 米")

# 可视化路径
fig, ax = plt.subplots(figsize=(10, 10))

# 绘制路径
route_edges = list(zip(route[:-1], route[1:]))  # 边是相邻节点对
for u, v in route_edges:
    # 获取节点u和v的坐标
    u_coords = (graph.nodes[u]['x'], graph.nodes[u]['y'])
    v_coords = (graph.nodes[v]['x'], graph.nodes[v]['y'])
    
    # 绘制路径的边（线段），将路径绘制为红色
    ax.plot([u_coords[0], v_coords[0]], [u_coords[1], v_coords[1]], color='r', linewidth=5)

# 设置背景颜色为白色
ax.set_facecolor('w')

# 显示图形
plt.show()

'''
本代码来源于PC的superviser_1.py，删去了original_gnss，做了本地化适配
'''

import geojson
import matplotlib.pyplot as plt
import numpy as np
from heapq import heappop, heappush
from matplotlib.patches import Ellipse
from datetime import datetime

# 配置参数
INTERPOLATION_THRESHOLD =25.0  # 插值节点的距离阈值（米）
CONNECTION_THRESHOLD = 10.0  # 连接近距离节点的阈值（米）

def haversine(lon1, lat1, lon2, lat2):
    """计算两点间的大圆距离（米）"""
    from math import radians, sin, cos, sqrt, atan2
    R = 6371000  # 地球半径（米）
    dlon = radians(lon2 - lon1)
    dlat = radians(lat2 - lat1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def interpolate_points(p1, p2, threshold):
    """在两点间插值，确保点间距不超过阈值，并返回插值点列表"""
    dist = haversine(p1[0], p1[1], p2[0], p2[1])
    if dist <= threshold:
        return []
    num_points = int(dist // threshold)
    interpolated = []
    for i in range(1, num_points + 1):
        ratio = i / (num_points + 1)
        lat = p1[1] + ratio * (p2[1] - p1[1])
        lon = p1[0] + ratio * (p2[0] - p1[0])
        interpolated.append((lon, lat))
    return interpolated

def process_geojson_with_interpolation(filepath, interpolation_threshold=25.0):
    """处理GeoJSON数据并进行插值，保留连接关系"""
    print(f"Processing map with interpolation from: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = geojson.load(f)
    nodes = []  # 存储所有节点坐标
    coord_to_id = {}  # 坐标到节点ID的映射
    adj_list = {}  # 邻接表
    original_edges = []  # 存储原始线段关系（用于插值后重建连接）

    # 第一遍：收集所有原始节点
    for feature in data['features']:
        geometry_type = feature['geometry']['type']
        coords = feature['geometry']['coordinates']
        if geometry_type == 'LineString':
            coords_list = [coords]
        elif geometry_type == 'MultiLineString':
            coords_list = coords
        else:
            continue
        for line_coords in coords_list:
            for coord in line_coords:
                coord_tuple = tuple(coord[:2])
                if coord_tuple not in coord_to_id:
                    coord_to_id[coord_tuple] = len(nodes)
                    nodes.append(coord_tuple)
                    adj_list[len(nodes) - 1] = set()

    # 第二遍：插值并构建连接关系
    for feature in data['features']:
        geometry_type = feature['geometry']['type']
        coords = feature['geometry']['coordinates']
        if geometry_type == 'LineString':
            coords_list = [coords]
        elif geometry_type == 'MultiLineString':
            coords_list = coords
        else:
            continue
        for line_coords in coords_list:
            # 存储原始线段的所有节点（包括插值点）
            segment_nodes = []
            # 处理第一个点
            p1 = tuple(line_coords[0][:2])
            if p1 not in coord_to_id:
                coord_to_id[p1] = len(nodes)
                nodes.append(p1)
                adj_list[len(nodes) - 1] = set()
            segment_nodes.append(coord_to_id[p1])
            # 处理中间点（插值）
            for i in range(len(line_coords) - 1):
                p1 = tuple(line_coords[i][:2])
                p2 = tuple(line_coords[i + 1][:2])
                # 添加插值点
                interpolated = interpolate_points(p1, p2, interpolation_threshold)
                for point in interpolated:
                    if point not in coord_to_id:
                        coord_to_id[point] = len(nodes)
                        nodes.append(point)
                        adj_list[len(nodes) - 1] = set()
                    segment_nodes.append(coord_to_id[point])
                # 添加终点
                if p2 not in coord_to_id:
                    coord_to_id[p2] = len(nodes)
                    nodes.append(p2)
                    adj_list[len(nodes) - 1] = set()
                segment_nodes.append(coord_to_id[p2])
            # 构建线段上的连接关系（链式连接）
            for i in range(len(segment_nodes) - 1):
                node1 = segment_nodes[i]
                node2 = segment_nodes[i + 1]
                adj_list[node1].add(node2)
                adj_list[node2].add(node1)

    # 第三遍：连接距离很近的节点（如交叉路口）
    print("Connecting nearby nodes...")
    connected_pairs = 0
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if haversine(*nodes[i], *nodes[j]) < CONNECTION_THRESHOLD:
                adj_list[i].add(j)
                adj_list[j].add(i)
                connected_pairs += 1
    print(f"Map loaded: {len(nodes)} nodes, {sum(len(v) for v in adj_list.values())} edges")
    print(f"Connected {connected_pairs} additional node pairs based on proximity")
    return nodes, adj_list

def read_calibrated_gnss(filepath):
    """读取校准后的GNSS日志文件（红色轨迹）"""
    print(f"开始读取校准后GNSS日志文件: {filepath}")
    gnss_points = []
    line_count = 0
    success_count = 0

    # 从下往上读取时间连续的最后一组数据
    lines = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    last_timestamp = None
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            time_part, data_part = line.split(',', 1)
            timestamp = datetime.strptime(time_part.strip(), "%Y-%m-%d %H:%M:%S")
            if last_timestamp is None or (last_timestamp - timestamp).total_seconds() <= 2:
                # 解析经纬度数据
                lat_str = [s for s in data_part.split(',') if 'Lat_calibrated' in s][0]
                lon_str = [s for s in data_part.split(',') if 'Lon_calibrated' in s][0]
                lat = float(lat_str.split(':')[-1].strip())
                lon = float(lon_str.split(':')[-1].strip())
                gnss_points.insert(0, (lon, lat))  # 插入到列表开头
                last_timestamp = timestamp
            else:
                break  # 时间断裂，停止读取
        except (ValueError, IndexError, AttributeError) as e:
            print(f"警告: 行解析失败 - {str(e)}")
            continue

    print(f"校准后GNSS日志读取完成 - 总行数: {line_count}, 成功解析: {success_count}, 有效轨迹点: {len(gnss_points)}")
    return gnss_points

def read_astar_path(filepath, map_nodes):
    """读取A*路径文件并返回路径的经纬度坐标"""
    print(f"开始读取A*路径文件: {filepath}")
    astar_path_ids = []

    # 从下往上读取时间连续的最后两行
    lines = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in reversed(lines):
        line = line.strip()
        if line.startswith("Path:"):
            # 提取路径ID列表
            path_str = line.split(":")[1].strip()
            astar_path_ids = eval(path_str)  # 将字符串转换为列表
            break

    # 根据ID获取经纬度坐标
    astar_path_coords = []
    for node_id in astar_path_ids:
        if 0 <= node_id < len(map_nodes):
            astar_path_coords.append(map_nodes[node_id])
        else:
            print(f"警告: 节点ID {node_id} 超出范围，跳过该节点")
    print(f"A*路径读取完成 - 总节点数: {len(astar_path_coords)}")
    return astar_path_coords

def visualize_map(nodes, adj_list, calibrated_gnss=None, astar_path=None):
    """可视化地图和GNSS轨迹，并显示节点ID、A*路径以及以节点为中心的圆"""
    print("开始生成可视化图表...")
    plt.figure(figsize=(14, 12))
    ax = plt.gca()  # 获取当前坐标轴

    # 绘制所有节点
    lons, lats = zip(*nodes)
    plt.scatter(lons, lats, c='blue', s=5, alpha=0.5, label='Map Nodes')

    # 为每个节点标注ID
    for node_id, (lon, lat) in enumerate(nodes):
        plt.text(lon, lat, str(node_id), fontsize=6, ha='right', color='darkblue')  # 显示真实节点ID

    # 绘制连接线
    for node_id, neighbors in adj_list.items():
        for neighbor_id in neighbors:
            if neighbor_id > node_id:  # 避免重复绘制
                plt.plot([nodes[node_id][0], nodes[neighbor_id][0]],
                         [nodes[node_id][1], nodes[neighbor_id][1]],
                         '#B7F5DE', linewidth=0.5, alpha=0.3)

    # 如果提供校准后GNSS轨迹，则绘制黄橙色轨迹
    if calibrated_gnss and len(calibrated_gnss) > 0:
        gnss_lons, gnss_lats = zip(*calibrated_gnss)
        plt.plot(gnss_lons, gnss_lats, color='#EECA40', linewidth=2, alpha=0.8, label='Calibrated GNSS Track')
        plt.scatter(gnss_lons[0], gnss_lats[0], c='#EECA40', s=100, marker='o', label='Calibrated Start')
        plt.scatter(gnss_lons[-1], gnss_lats[-1], c='#EECA40', s=100, marker='x', label='Calibrated End')

    # 如果提供A*路径，则绘制深蓝色轨迹
    if astar_path and len(astar_path) > 0:
        astar_lons, astar_lats = zip(*astar_path)
        plt.plot(astar_lons, astar_lats, color='#23BAC5', linewidth=3, alpha=0.9, label='A* Planned Path')
        # 根据起始点纬度计算纵横比
        start_latitude = astar_path[0][1]  # 使用A*路径的第一个点的纬度作为参考
        aspect_ratio = np.cos(np.radians(start_latitude))  # 经度方向的缩放因子
        # 为A*路径的每个节点绘制半径为4米的椭圆
        for lon, lat in astar_path:
            radius_meters = 4  # 半径为4米
            radius_lon = radius_meters / 111320 / aspect_ratio  # 经度方向的半径
            radius_lat = radius_meters / 111320  # 纬度方向的半径
            ellipse = Ellipse((lon, lat), width=2 * radius_lon, height=2 * radius_lat,
                              color='#D5D9E5', fill=True, alpha=0.5)
            ax.add_patch(ellipse)

    # 动态计算轨迹的最大外边界
    all_lons, all_lats = [], []
    if calibrated_gnss:
        all_lons.extend([lon for lon, _ in calibrated_gnss])
        all_lats.extend([lat for _, lat in calibrated_gnss])
    if astar_path:
        all_lons.extend([lon for lon, _ in astar_path])
        all_lats.extend([lat for _, lat in astar_path])

    # 计算最小/最大经纬度范围
    lon_min, lon_max = min(all_lons), max(all_lons)
    lat_min, lat_max = min(all_lats), max(all_lats)

    # 添加30%缓冲区
    lon_range = lon_max - lon_min
    lat_range = lat_max - lat_min
    buffer1 = 2  # 缓冲区比例
    buffer2 = 0.25 * buffer1  # 缓冲区比例
    lon_min -= buffer1 * lon_range
    lon_max += buffer1 * lon_range
    lat_min -= buffer2 * lat_range
    lat_max += buffer2 * lat_range

    # 设置纵横比
    start_latitude = (lat_min + lat_max) / 2  # 使用中心纬度作为参考
    aspect_ratio = 1 / np.cos(np.radians(start_latitude))  # 经度与纬度的比例因子
    ax.set_aspect(aspect_ratio)

    # 设置坐标轴范围
    plt.xlim(lon_min, lon_max)
    plt.ylim(lat_min, lat_max)
    plt.xlabel('Longitude', fontsize=12)
    plt.ylabel('Latitude', fontsize=12)
    plt.title('Map Visualization with GNSS Tracks, Node IDs, A* Path, and Circles', fontsize=14)
    plt.legend(fontsize=10, loc='upper right')
    plt.grid(True, alpha=0.3)
    print("可视化图表生成完成，显示中...")
    plt.show()

if __name__ == "__main__":
    # 处理地图数据
    geojson_path = "/home/jetson/ros2_ws/src/gnss_global_path_planner/map/XJ04132316.geojson"
    nodes, adj_list = process_geojson_with_interpolation(geojson_path)

    # 处理GNSS数据
    calibrated_path = "/home/jetson/ros2_ws/src/GNSS/GNSSlog/gnss_global_log.txt"
    calibrated_gnss = read_calibrated_gnss(calibrated_path)

    # 读取A*路径数据
    astar_path_file = "/home/jetson/ros2_ws/src/GNSS/GNSSlog/astar_path.txt"
    astar_path = read_astar_path(astar_path_file, nodes)

    # 可视化
    visualize_map(nodes, adj_list, calibrated_gnss, astar_path)
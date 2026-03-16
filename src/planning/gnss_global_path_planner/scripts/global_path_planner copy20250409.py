#!/usr/bin/env python3
import os
import time
import rclpy
import geojson
import threading
import queue
import matplotlib.pyplot as plt
from heapq import heappop, heappush
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import NavSatFix
from math import radians, sin, cos, sqrt, atan2, degrees, pi
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point
from datetime import datetime
from geopy.distance import geodesic
from tf2_ros import StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped
from collections import deque


# 插值节点的距离阈值（米）
INTERPOLATION_THRESHOLD = 25.0
# 临近阈值（米）
PROXIMITY_THRESHOLD = 10.0
# 偏航检测放大系数
YAW_THRESHOLD_FACTOR = 2.0

# 起始点
VISUAL_START_ID = 139 # 起始点
# 结束点
END_NODE_ID = 59  # 南边某点

current_gnss = None

def log(message):
    print(f"[LOG] {message}", flush=True)


# 计算两点间的球面距离（米）
def haversine(lon1, lat1, lon2, lat2):
    R = 6371000  # 地球半径（米）
    dlon = radians(lon2 - lon1)
    dlat = radians(lat2 - lat1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


# 插值路径点
def interpolate_points(p1, p2, threshold):
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

#  判断接近与偏航状态
def check_proximity_and_yaw(prev, curr, next, proximity_threshold):
    def angle_between(p1, p2):
        return atan2(p2[1] - p1[1], p2[0] - p1[0])
    angle_diff = (angle_between(prev, next) - angle_between(curr, next) + pi) % (2 * pi) - pi
    sharp_turn = abs(angle_diff) < pi / 2
    threshold = proximity_threshold if sharp_turn else YAW_THRESHOLD_FACTOR * proximity_threshold
    close_to_next = haversine(curr[0], curr[1], next[0], next[1]) <= threshold
    off_track = haversine(curr[0], curr[1], prev[0], prev[1]) > haversine(prev[0], prev[1], next[0], next[1]) if sharp_turn else not close_to_next
    return close_to_next, off_track

# 地图处理
def process_map(filepath):
    log(f"Processing map from: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = geojson.load(f)

    nodes = []  # 存储所有节点坐标
    coord_to_id = {}  # 坐标到节点ID的映射
    adj_list = {}  # 邻接表

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
                interpolated = interpolate_points(p1, p2, INTERPOLATION_THRESHOLD)
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

    log(f"Map loaded: {len(nodes)} nodes, {sum(len(v) for v in adj_list.values())} edges")
    return nodes, adj_list

def astar(start, goal, nodes, adj_list):
    log(f"Starting A* from {start} to {goal}")
    open_set = []
    heappush(open_set, (0, start))

    came_from = {}
    g_score = {i: float('inf') for i in range(len(nodes))}
    g_score[start] = 0

    f_score = {i: float('inf') for i in range(len(nodes))}
    f_score[start] = haversine(*nodes[start], *nodes[goal])

    open_set_hash = {start}

    while open_set:
        _, current = heappop(open_set)
        open_set_hash.remove(current)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            
            # 确保路径以 start 开头
            if path and path[-1] != start:
                path.append(start)
            
            path = path[::-1]
            log(f"Path found with {len(path)} nodes")
            return path

        for neighbor in adj_list[current]:
            tentative_g_score = g_score[current] + haversine(*nodes[current], *nodes[neighbor])

            if tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = g_score[neighbor] + haversine(*nodes[neighbor], *nodes[goal])
                if neighbor not in open_set_hash:
                    heappush(open_set, (f_score[neighbor], neighbor))
                    open_set_hash.add(neighbor)

    log("No path found")
    return None


# 定义保存路径的函数
def save_path_to_file(path, filepath="/home/jetson/ros2_ws/src/GNSS/GNSSlog/astar_path.txt"):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path_str = f"\n时间: {current_time}\nPath: {path}\n"
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(path_str)


class GnssSubscriber(Node):
    def __init__(self):
        super().__init__('gnss_subscriber')
        self.subscription = self.create_subscription(
            NavSatFix,
            '/gnss',
            self.listener_callback,
            10
        )
        self.publisher = self.create_publisher(String, '/next_node', 10)
        self.gnss_received = False  # 标志是否已接收到 /gnss 数据

    def listener_callback(self, msg):
        global current_gnss
        current_gnss = (msg.longitude, msg.latitude)
        if not self.gnss_received:
            # log("[GNSS Calibration] GNSS data received. Calibration completed.")
            self.gnss_received = True  # 标记校准完成


class RuntimeCalibration:
    def __init__(self, node):
        """
        初始化运行时校准器。
        """
        self.node = node
        self.precise_reached_points = []  # 存储最近的 3 个 precise_reached 点
        self.calibrated = False  # 标志是否已完成校准
        self.OFFSET_FILE_PATH = '/home/jetson/ros2_ws/src/GNSS/gnss_calibration/gnss_calibration/gnss_offset.txt'
        self.PROXIMITY_THRESHOLD = PROXIMITY_THRESHOLD  # 接近阈值（米）
        self.gnss1 = None  # 进入 reached 圆时的第一个 GNSS 点
        self.gnss2 = None  # 经过垂线时的第一个 GNSS 点

        # 加载已有的偏移量
        self.loaded_offset = self.load_offset()

    def load_offset(self):
        """
        从文件加载已有的偏移量。
        """
        try:
            if os.path.exists(self.OFFSET_FILE_PATH):
                with open(self.OFFSET_FILE_PATH, 'r') as offset_file:
                    lines = offset_file.readlines()
                    lat_offset = float(lines[0].strip())
                    lon_offset = float(lines[1].strip())
                    return (lat_offset, lon_offset)
            else:
                return (0.0, 0.0)  # 如果文件不存在，默认偏移量为 0
        except Exception as e:
            self.node.get_logger().error(f"Error loading offsets: {e}")
            return (0.0, 0.0)

    def check_precise_reached(self, prev_node, curr_gnss, next_coords):
        """
        检查是否达到 precise_reached 状态，并记录原始经纬度。
        """
        if self.calibrated:
            return  # 如果已经完成校准，则不再进行检查

        # 更新 gnss1 和 gnss2
        if self.gnss1 is None:
            self.gnss1 = curr_gnss
        else:
            self.gnss2 = curr_gnss

        # 检查 gnss2 是否在 reached 圆内且经过垂线
        if (haversine(curr_gnss[0], curr_gnss[1], next_coords[0], next_coords[1]) <= self.PROXIMITY_THRESHOLD and
                self.is_on_perpendicular_line(prev_node, curr_gnss, next_coords)):
            # 计算交点
            intersection_point = self.calculate_intersection(prev_node, next_coords)
            if intersection_point:
                self.node.get_logger().info(f"[RuntimeCalibration]Intersection point calculated: {intersection_point}")
                
                # 将 /gnss 坐标系下的插值点映射回 /fix 坐标系
                gnss2fix_lat = intersection_point[1] - self.loaded_offset[0]
                gnss2fix_lon = intersection_point[0] - self.loaded_offset[1]
                gnss2fix = (gnss2fix_lon, gnss2fix_lat)
                
                # 计算误差
                error_lat = next_coords[1] - gnss2fix_lat
                error_lon = next_coords[0] - gnss2fix_lon
                
                self.precise_reached_points.append({
                    'map_coords': next_coords,
                    'gnss2fix': gnss2fix,
                    'error': (error_lat, error_lon)
                })
                self.node.get_logger().info(f"[RuntimeCalibration]Data recorded: gnss2fix={gnss2fix}, error={error_lat}, {error_lon}")

                # 如果已经有 3 个点，尝试计算偏移量
                if len(self.precise_reached_points) >= 3:
                    self.calculate_and_save_offsets()

                # 清空 gnss1 和 gnss2，准备下一次记录
                self.gnss1 = None
                self.gnss2 = None
                
    def calculate_intersection(self, prev_node, next_coords):
        """
        计算 gnss1 和 gnss2 与垂线的交点。
        :param prev_node: 上一个路径点的坐标 (经度, 纬度)
        :param next_coords: 下一个路径点的坐标 (经度, 纬度)
        :return: 交点坐标 (经度, 纬度)，如果无法计算则返回 None
        """
        if not self.gnss1 or not self.gnss2:
            # 如果没有足够的 GNSS 数据，无法计算交点
            self.node.get_logger().warn("Insufficient data to calculate intersection.")
            return None

        x1, y1 = self.gnss1  # 第一个 GNSS 点
        x2, y2 = self.gnss2  # 第二个 GNSS 点
        prev_x, prev_y = prev_node  # 上一个路径点
        next_x, next_y = next_coords  # 下一个路径点

        # 垂线方程：A*x + B*y + C = 0
        A = next_y - prev_y
        B = -(next_x - prev_x)
        C = (next_x - prev_x) * prev_y - (next_y - prev_y) * prev_x

        # 直线方程（通过 gnss1 和 gnss2）：y = k*x + b
        if x2 != x1:
            k = (y2 - y1) / (x2 - x1)  # 斜率
            b = y1 - k * x1  # 截距
            # 解方程组求交点
            x_intersect = -(B * b + C) / (A + B * k)
            y_intersect = k * x_intersect + b
        else:
            # 特殊情况：直线垂直于 x 轴
            x_intersect = x1
            y_intersect = (-A * x_intersect - C) / B

        return (x_intersect, y_intersect)

    def is_on_perpendicular_line(self, prev_node, curr_gnss, next_coords):
        """
        检查 curr 是否经过了从 prev 到 next 的垂线。
        """
        x1, y1 = prev_node
        x2, y2 = next_coords
        x, y = curr_gnss

        # 计算从 prev 到 next 的方向向量
        dx, dy = x2 - x1, y2 - y1

        # 计算垂线的方向向量
        perp_dx, perp_dy = -dy, dx

        # 计算 curr 到 next 的向量
        vec_x, vec_y = x - x2, y - y2

        # 判断是否在垂线方向上
        dot_product = vec_x * perp_dx + vec_y * perp_dy
        return abs(dot_product) < 1e-6  # 阈值判断
    
    def calculate_and_save_offsets(self):
        """
        根据最近的 3 个 precise_reached 点计算偏移量并保存。
        """
        try:
            if len(self.precise_reached_points) < 3:
                return

            # 提取最近的 3 个点
            points = self.precise_reached_points[-3:]

            # 检查是否近似直线
            angle = self.calculate_angle(points)
            if abs(angle - 180) > 10:  # 阈值为 10 度
                self.node.get_logger().warn("Points are not collinear. Skipping offset calculation.")
                return

            # 计算偏移量
            lat_errors = [point['error'][0] for point in points]
            lon_errors = [point['error'][1] for point in points]

            avg_lat_error = sum(lat_errors) / len(lat_errors)
            avg_lon_error = sum(lon_errors) / len(lon_errors)

            # 保存偏移量到文件
            try:
                # 读取旧的偏移量（如果文件存在）
                if os.path.exists(self.OFFSET_FILE_PATH):
                    with open(self.OFFSET_FILE_PATH, 'r') as offset_file:
                        old_content = offset_file.read().strip()
                else:
                    old_content = "No previous offsets"

                # 写入新的偏移量
                with open(self.OFFSET_FILE_PATH, 'w') as offset_file:
                    offset_file.write(f"{avg_lat_error}\n{avg_lon_error}")
                
                # 读取新的偏移量以验证写入
                with open(self.OFFSET_FILE_PATH, 'r') as offset_file:
                    new_content = offset_file.read().strip()

                # 日志输出
                self.node.get_logger().info(f"[RuntimeCalibration] Old offsets: {old_content}")
                self.node.get_logger().info(f"[RuntimeCalibration] New offsets: {new_content}")
                self.node.get_logger().info("[RuntimeCalibration]***Success!***")
            except Exception as e:
                self.node.get_logger().error(f"[RuntimeCalibration] Error saving offsets: {e}")

            self.calibrated = True  # 标记校准完成
        except Exception as e:
            self.node.get_logger().error(f"[RuntimeCalibration]Error calculating and saving offsets: {e}")

                                
class NextNodeRepeater(Node):
    def __init__(self):
        super().__init__('next_node_repeater')
        self.subscription = self.create_subscription(String, '/next_node', self.next_node_callback, 10)
        self.publisher = self.create_publisher(String, '/next_node', 10)
        self.latest_msg = None
        self.timer = self.create_timer(2.0, self.repeat_publish)  # 0.5Hz = 每2秒一次

    def next_node_callback(self, msg):
        if self.latest_msg != msg.data:
            self.get_logger().info(f"[Repeater] Received /next_node: {msg.data}")
        self.latest_msg = msg.data

    def repeat_publish(self):
        if self.latest_msg is not None:
            self.publisher.publish(String(data=self.latest_msg))
            self.get_logger().info(f"[Repeater] Re-publishing: {self.latest_msg}")

if __name__ == "__main__":
    rclpy.init()

    # 初始化节点
    gnss_subscriber = GnssSubscriber()
    next_node_repeater = NextNodeRepeater()

    # 加载地图
    filepath = "/home/jetson/ros2_ws/src/gnss_global_path_planner/map/XJ03181720.geojson"
    nodes, adj_list = process_map(filepath)

    log("Waiting for GNSS data...")
    while not gnss_subscriber.gnss_received:
        rclpy.spin_once(gnss_subscriber)

    log("[==Transformer is calibrating==]")
    time.sleep(4)
    log("[==Transformer calibrated==]")

    # 寻找起点
    start_node = min(
        range(len(nodes)),
        key=lambda i: haversine(current_gnss[0], current_gnss[1], nodes[i][0], nodes[i][1])
    )
    end_node = END_NODE_ID

    path = astar(start_node, end_node, nodes, adj_list)
    if path is None:
        log("Error: No valid path found. Exiting...")
        rclpy.shutdown()
        exit(1)

    save_path_to_file(path)

    prev_node, curr_node = path[0], path[0]
    runtime_calibrator = RuntimeCalibration(gnss_subscriber)

    try:
        for next_node in path[1:]:
            node_id = next_node
            next_coords = nodes[next_node]

            if runtime_calibrator.calibrated:
                gnss_subscriber.publisher.publish(String(data=f"{next_coords[0]},{next_coords[1]}"))
                log(f"Publishing first calibrated next node [{node_id}]: {next_coords}")
                runtime_calibrator.calibrated = False

            if prev_node == curr_node:
                log(f"Skipping direction calculation for the first node [{node_id}]")
            else:
                prev_coords = nodes[prev_node]
                curr_coords = nodes[curr_node]

                def calculate_angle(p1, p2):
                    return atan2(p2[1] - p1[1], p2[0] - p1[0])

                current_angle = calculate_angle(prev_coords, curr_coords)
                next_angle = calculate_angle(curr_coords, next_coords)
                angle_diff = (next_angle - current_angle + pi) % (2 * pi) - pi

                if abs(degrees(angle_diff)) <= 10:
                    turn_direction = "Go Straight"
                elif angle_diff > 0:
                    turn_direction = f"Turn Left by {degrees(angle_diff):.1f}°"
                else:
                    turn_direction = f"Turn Right by {degrees(-angle_diff):.1f}°"

                log(f"Direction: {turn_direction}")

            gnss_subscriber.publisher.publish(String(data=f"{next_coords[0]},{next_coords[1]}"))
            log(f"Publishing next node [{node_id}]: {next_coords}")

            while rclpy.ok():
                rclpy.spin_once(gnss_subscriber, timeout_sec=0.1)
                rclpy.spin_once(next_node_repeater, timeout_sec=0.1)

                if haversine(current_gnss[0], current_gnss[1], next_coords[0], next_coords[1]) <= PROXIMITY_THRESHOLD:
                    log(f"======Reached waypoint [{node_id}]: {next_coords}======")
                    runtime_calibrator.check_precise_reached(
                        prev_node=nodes[prev_node],
                        curr_gnss=current_gnss,
                        next_coords=next_coords
                    )
                    break

                close, off_track = check_proximity_and_yaw(nodes[prev_node], current_gnss, next_coords, PROXIMITY_THRESHOLD)
                if off_track:
                    log("Warning: Off track! Adjusting course...")
                if close or off_track:
                    prev_node, curr_node = curr_node, next_node
                    break

        final_goal_coords = nodes[end_node]
        if haversine(current_gnss[0], current_gnss[1], final_goal_coords[0], final_goal_coords[1]) <= PROXIMITY_THRESHOLD:
            log(f"**********Destination reached [{end_node}]: {final_goal_coords}**********")
        else:
            log("Warning: Final destination not reached. Check GNSS accuracy.")
    except KeyboardInterrupt:
        log("Navigation interrupted by user.")
    finally:
        gnss_subscriber.destroy_node()
        next_node_repeater.destroy_node()
        rclpy.shutdown()
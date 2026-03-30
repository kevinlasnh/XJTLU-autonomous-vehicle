# 指定Python解释器路径，用于在Unix-like系统中运行脚本
#!/usr/bin/env python3
# 导入os模块，用于操作系统相关功能，如文件路径操作
import os
# 导入time模块，用于时间相关功能，如延时
import time
# 导入rclpy库，用于ROS2 Python接口
import rclpy
# 导入geojson库，用于处理GeoJSON格式的数据
import geojson
# 从heapq模块导入heappop和heappush函数，用于堆操作
from heapq import heappop, heappush
# 从rclpy.node模块导入Node类，用于创建ROS2节点
from rclpy.node import Node
# 从std_msgs.msg模块导入String消息类型，用于字符串消息
from std_msgs.msg import String
# 从sensor_msgs.msg模块导入NavSatFix消息类型，用于GNSS数据
from sensor_msgs.msg import NavSatFix
# 从math模块导入radians, sin, cos, sqrt, atan2, degrees, pi函数，用于数学计算
from math import radians, sin, cos, sqrt, atan2, degrees, pi
# 从datetime模块导入datetime类，用于处理日期和时间
from datetime import datetime
# 从nav_msgs.msg模块导入Path消息类型，用于路径消息
from nav_msgs.msg import Path
# 从geometry_msgs.msg模块导入PoseStamped消息类型，用于姿态消息
from geometry_msgs.msg import PoseStamped
from pathlib import Path


def get_runtime_root():
    runtime_root = os.environ.get("FYP_RUNTIME_ROOT")
    if runtime_root:
        return Path(runtime_root).expanduser()
    return Path.home() / "XJTLU-autonomous-vehicle/runtime-data"


def get_runtime_path(*parts):
    return get_runtime_root().joinpath(*parts)


# 节点名称：global_path_planner

# 节点功能（目前）：
# 这个全局路径规划节点启动后会先把本地的地理数据文件解析成带权重的路网，
# 接着等待 GNSS 定位消息来确定车辆当前在图中的起点，
# 再通过 A* 搜索等逻辑把起终点之间的节点序列整理成光滑的经纬度路径；
# 它一方面把整条路径不断打包发往全局路径话题，
# 另一方面按顺序把下一个目标节点的经纬度推送到指令话题，
# 并在导航过程中持续监听新的 GNSS 数据，
# 用距离和偏航判断是否接近目标、是否偏航，
# 同时驱动运行时标定模块修正定位偏差，
# 所以最终实现了从实时定位和地图输入到路径指引输出的完整闭环

# 节点输入数据（目前）：
# 1. /gnss（由GNSS接收器发布，提供全球坐标系下的位置信息）
# 2. /next_node（由全局路径规划节点发布，表示当前路径中的下一个目标节点）

# 节点输出数据（目前）：
# 1. /next_node（由全局路径规划节点发布，表示当前路径中的下一个目标节点）
# 2. /path4global（由全局路径规划节点发布，表示从GNSS坐标系下的完整路径）

# 定义插值节点的距离阈值常量，单位为米
INTERPOLATION_THRESHOLD = 25.0
# 定义临近阈值常量，单位为米
PROXIMITY_THRESHOLD = 10.0
# 定义偏航检测放大系数常量
YAW_THRESHOLD_FACTOR = 2.0

# 定义结束点节点ID常量
END_NODE_ID = 59

# 初始化当前GNSS数据为None
current_gnss = None

# 定义日志函数，用于打印日志信息
def log(message):
    # 打印带有时间戳的日志消息，并刷新输出
    print(f"[LOG] {message}", flush=True)

# 定义计算两点间球面距离的函数
def haversine(lon1, lat1, lon2, lat2):
    # 定义地球半径常量，单位为米
    R = 6371000
    # 计算经度差并转换为弧度
    dlon = radians(lon2 - lon1)
    # 计算纬度差并转换为弧度
    dlat = radians(lat2 - lat1)
    # 使用haversine公式计算球面距离的中间值a
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    # 返回两点间的球面距离
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

# 定义插值路径点的函数
def interpolate_points(p1, p2, threshold):
    # 计算两点间的距离
    dist = haversine(p1[0], p1[1], p2[0], p2[1])
    # 如果距离小于等于阈值，返回空列表
    if dist <= threshold:
        return []
    # 计算需要插值的点数
    num_points = int(dist // threshold)
    # 初始化插值点列表
    interpolated = []
    # 循环插值每个点
    for i in range(1, num_points + 1):
        # 计算插值比例
        ratio = i / (num_points + 1)
        # 计算插值纬度
        lat = p1[1] + ratio * (p2[1] - p1[1])
        # 计算插值经度
        lon = p1[0] + ratio * (p2[0] - p1[0])
        # 添加插值点到列表
        interpolated.append((lon, lat))
    # 返回插值点列表
    return interpolated

# 定义判断接近与偏航状态的函数
def check_proximity_and_yaw(prev, curr, next, proximity_threshold):
    # 定义计算两点间角度的内部函数
    def angle_between(p1, p2):
        # 计算两点间的角度
        return atan2(p2[1] - p1[1], p2[0] - p1[0])
    # 计算角度差
    angle_diff = (angle_between(prev, next) - angle_between(curr, next) + pi) % (2 * pi) - pi
    # 判断是否为急转弯
    sharp_turn = abs(angle_diff) < pi / 2
    # 根据是否急转弯设置阈值
    threshold = proximity_threshold if sharp_turn else YAW_THRESHOLD_FACTOR * proximity_threshold
    # 判断是否接近下一个点
    close_to_next = haversine(curr[0], curr[1], next[0], next[1]) <= threshold
    # 判断是否偏离轨道
    off_track = haversine(curr[0], curr[1], prev[0], prev[1]) > haversine(prev[0], prev[1], next[0], next[1]) if sharp_turn else not close_to_next
    # 返回接近和偏航状态
    return close_to_next, off_track

# 定义地图处理函数
def process_map(filepath):
    # 记录处理地图的日志
    log(f"Processing map from: {filepath}")
    # 打开并读取GeoJSON文件
    with open(filepath, 'r', encoding='utf-8') as f:
        data = geojson.load(f)

    # 初始化节点列表
    nodes = []
    # 初始化坐标到节点ID的映射字典
    coord_to_id = {}
    # 初始化邻接表
    adj_list = {}

    # 第一遍：收集所有原始节点
    for feature in data['features']:
        # 获取几何类型
        geometry_type = feature['geometry']['type']
        # 获取坐标
        coords = feature['geometry']['coordinates']

        # 根据几何类型处理坐标
        if geometry_type == 'LineString':
            coords_list = [coords]
        elif geometry_type == 'MultiLineString':
            coords_list = coords
        else:
            continue

        # 遍历坐标列表
        for line_coords in coords_list:
            # 遍历每个坐标
            for coord in line_coords:
                # 转换为坐标元组
                coord_tuple = tuple(coord[:2])
                # 如果坐标不在映射中，添加新节点
                if coord_tuple not in coord_to_id:
                    coord_to_id[coord_tuple] = len(nodes)
                    nodes.append(coord_tuple)
                    adj_list[len(nodes) - 1] = set()

    # 第二遍：插值并构建连接关系
    for feature in data['features']:
        # 获取几何类型
        geometry_type = feature['geometry']['type']
        # 获取坐标
        coords = feature['geometry']['coordinates']

        # 根据几何类型处理坐标
        if geometry_type == 'LineString':
            coords_list = [coords]
        elif geometry_type == 'MultiLineString':
            coords_list = coords
        else:
            continue

        # 遍历坐标列表
        for line_coords in coords_list:
            # 初始化线段节点列表
            segment_nodes = []

            # 处理第一个点
            p1 = tuple(line_coords[0][:2])
            # 如果点不在映射中，添加新节点
            if p1 not in coord_to_id:
                coord_to_id[p1] = len(nodes)
                nodes.append(p1)
                adj_list[len(nodes) - 1] = set()
            # 添加节点到线段节点列表
            segment_nodes.append(coord_to_id[p1])

            # 处理中间点（插值）
            for i in range(len(line_coords) - 1):
                # 获取当前点和下一个点
                p1 = tuple(line_coords[i][:2])
                p2 = tuple(line_coords[i + 1][:2])

                # 添加插值点
                interpolated = interpolate_points(p1, p2, INTERPOLATION_THRESHOLD)
                for point in interpolated:
                    # 如果插值点不在映射中，添加新节点
                    if point not in coord_to_id:
                        coord_to_id[point] = len(nodes)
                        nodes.append(point)
                        adj_list[len(nodes) - 1] = set()
                    # 添加节点到线段节点列表
                    segment_nodes.append(coord_to_id[point])

                # 添加终点
                if p2 not in coord_to_id:
                    coord_to_id[p2] = len(nodes)
                    nodes.append(p2)
                    adj_list[len(nodes) - 1] = set()
                # 添加节点到线段节点列表
                segment_nodes.append(coord_to_id[p2])

            # 构建线段上的连接关系（链式连接）
            for i in range(len(segment_nodes) - 1):
                # 获取相邻节点
                node1 = segment_nodes[i]
                node2 = segment_nodes[i + 1]
                # 添加双向连接
                adj_list[node1].add(node2)
                adj_list[node2].add(node1)

    # 记录地图加载信息
    log(f"Map loaded: {len(nodes)} nodes, {sum(len(v) for v in adj_list.values())} edges")
    # 返回节点列表和邻接表
    return nodes, adj_list

# 定义A*算法函数
def astar(start, goal, nodes, adj_list):
    # 记录开始A*搜索的日志
    log(f"Starting A* from {start} to {goal}")
    # 初始化开放集合
    open_set = []
    # 将起点推入堆
    heappush(open_set, (0, start))

    # 初始化came_from字典
    came_from = {}
    # 初始化g_score字典
    g_score = {i: float('inf') for i in range(len(nodes))}
    g_score[start] = 0

    # 初始化f_score字典
    f_score = {i: float('inf') for i in range(len(nodes))}
    f_score[start] = haversine(*nodes[start], *nodes[goal])

    # 初始化开放集合哈希集合
    open_set_hash = {start}

    # 当开放集合不为空时循环
    while open_set:
        # 弹出f值最小的节点
        _, current = heappop(open_set)
        # 从哈希集合中移除当前节点
        open_set_hash.remove(current)

        # 如果当前节点是目标节点
        if current == goal:
            # 重建路径
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]

            # 确保路径以起点开头
            if path and path[-1] != start:
                path.append(start)

            # 反转路径
            path = path[::-1]
            # 记录找到路径的日志
            log(f"Path found with {len(path)} nodes")
            # 返回路径
            return path

        # 遍历当前节点的邻居
        for neighbor in adj_list[current]:
            # 计算临时g分数
            tentative_g_score = g_score[current] + haversine(*nodes[current], *nodes[neighbor])

            # 如果临时g分数小于邻居的g分数
            if tentative_g_score < g_score[neighbor]:
                # 更新came_from
                came_from[neighbor] = current
                # 更新g_score
                g_score[neighbor] = tentative_g_score
                # 更新f_score
                f_score[neighbor] = g_score[neighbor] + haversine(*nodes[neighbor], *nodes[goal])
                # 如果邻居不在开放集合中
                if neighbor not in open_set_hash:
                    # 推入堆
                    heappush(open_set, (f_score[neighbor], neighbor))
                    # 添加到哈希集合
                    open_set_hash.add(neighbor)

    # 记录未找到路径的日志
    log("No path found")
    # 返回None
    return None

# 定义保存路径到文件的函数
def save_path_to_file(path, filepath=None):
    filepath = Path(filepath) if filepath else get_runtime_path("logs", "planning", "astar_path.txt")
    # 创建文件目录（如果不存在）
    filepath.parent.mkdir(parents=True, exist_ok=True)
    # 获取当前时间
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 格式化路径字符串
    path_str = f"\n时间: {current_time}\nPath: {path}\n"
    # 打开文件并追加写入
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(path_str)

# 定义GnssSubscriber类，继承自Node
class GnssSubscriber(Node):
    # 初始化方法
    def __init__(self):
        # 调用父类初始化方法
        super().__init__('gnss_subscriber')
        # 创建订阅者，订阅'/gnss'话题
        self.subscription = self.create_subscription(
            NavSatFix,
            '/gnss',
            self.listener_callback,
            10
        )
        # 创建发布者，发布到'/next_node'话题
        self.publisher = self.create_publisher(String, '/next_node', 10)
        # 初始化GNSS数据接收标志
        self.gnss_received = False

    # 定义监听器回调函数
    def listener_callback(self, msg):
        # 更新全局当前GNSS数据
        global current_gnss
        current_gnss = (msg.longitude, msg.latitude)
        # 如果尚未接收到GNSS数据
        if not self.gnss_received:
            # 标记已接收到GNSS数据
            self.gnss_received = True

# 定义RuntimeCalibration类
class RuntimeCalibration:
    # 初始化方法
    def __init__(self, node):
        # 设置节点引用
        self.node = node
        # 初始化精确到达点列表
        self.precise_reached_points = []
        # 初始化校准完成标志
        self.calibrated = False
        # 设置偏移量文件路径
        self.OFFSET_FILE_PATH = str(get_runtime_path("gnss", "gnss_offset.txt"))
        # 设置接近阈值
        self.PROXIMITY_THRESHOLD = PROXIMITY_THRESHOLD
        # 初始化GNSS1点
        self.gnss1 = None
        # 初始化GNSS2点
        self.gnss2 = None

        # 加载已有的偏移量
        self.loaded_offset = self.load_offset()

    # 定义加载偏移量的方法
    def load_offset(self):
        # 尝试加载偏移量
        try:
            # 如果文件存在
            if os.path.exists(self.OFFSET_FILE_PATH):
                # 打开文件读取
                with open(self.OFFSET_FILE_PATH, 'r') as offset_file:
                    lines = offset_file.readlines()
                    # 解析纬度偏移量
                    lat_offset = float(lines[0].strip())
                    # 解析经度偏移量
                    lon_offset = float(lines[1].strip())
                    # 返回偏移量
                    return (lat_offset, lon_offset)
            else:
                # 返回默认偏移量
                return (0.0, 0.0)
        # 捕获异常
        except Exception as e:
            # 记录错误日志
            self.node.get_logger().error(f"Error loading offsets: {e}")
            # 返回默认偏移量
            return (0.0, 0.0)

    # 定义检查精确到达的方法
    def check_precise_reached(self, prev_node, curr_gnss, next_coords):
        # 如果已经校准完成，返回
        if self.calibrated:
            return

        # 更新GNSS1和GNSS2
        if self.gnss1 is None:
            self.gnss1 = curr_gnss
        else:
            self.gnss2 = curr_gnss

        # 检查GNSS2是否在接近圆内且经过垂线
        if (haversine(curr_gnss[0], curr_gnss[1], next_coords[0], next_coords[1]) <= self.PROXIMITY_THRESHOLD and
                self.is_on_perpendicular_line(prev_node, curr_gnss, next_coords)):
            # 计算交点
            intersection_point = self.calculate_intersection(prev_node, next_coords)
            # 如果交点存在
            if intersection_point:
                # 记录交点日志
                self.node.get_logger().info(f"[RuntimeCalibration]Intersection point calculated: {intersection_point}")

                # 将GNSS坐标系下的插值点映射回fix坐标系
                gnss2fix_lat = intersection_point[1] - self.loaded_offset[0]
                gnss2fix_lon = intersection_point[0] - self.loaded_offset[1]
                gnss2fix = (gnss2fix_lon, gnss2fix_lat)

                # 计算误差
                error_lat = next_coords[1] - gnss2fix_lat
                error_lon = next_coords[0] - gnss2fix_lon

                # 添加数据到列表
                self.precise_reached_points.append({
                    'map_coords': next_coords,
                    'gnss2fix': gnss2fix,
                    'error': (error_lat, error_lon)
                })
                # 记录数据日志
                self.node.get_logger().info(f"[RuntimeCalibration]Data recorded: gnss2fix={gnss2fix}, error={error_lat}, {error_lon}")

                # 如果有3个点，尝试计算偏移量
                if len(self.precise_reached_points) >= 3:
                    self.calculate_and_save_offsets()

                # 清空GNSS1和GNSS2
                self.gnss1 = None
                self.gnss2 = None

    # 定义计算交点的方法
    def calculate_intersection(self, prev_node, next_coords):
        # 如果没有足够的GNSS数据，返回None
        if not self.gnss1 or not self.gnss2:
            self.node.get_logger().warn("Insufficient data to calculate intersection.")
            return None

        # 获取坐标
        x1, y1 = self.gnss1
        x2, y2 = self.gnss2
        prev_x, prev_y = prev_node
        next_x, next_y = next_coords

        # 计算垂线方程系数
        A = next_y - prev_y
        B = -(next_x - prev_x)
        C = (next_x - prev_x) * prev_y - (next_y - prev_y) * prev_x

        # 计算直线方程
        if x2 != x1:
            # 计算斜率和截距
            k = (y2 - y1) / (x2 - x1)
            b = y1 - k * x1
            # 计算交点x
            x_intersect = -(B * b + C) / (A + B * k)
            # 计算交点y
            y_intersect = k * x_intersect + b
        else:
            # 特殊情况：直线垂直于x轴
            x_intersect = x1
            y_intersect = (-A * x_intersect - C) / B

        # 返回交点
        return (x_intersect, y_intersect)

    # 定义检查是否在垂线上的方法
    def is_on_perpendicular_line(self, prev_node, curr_gnss, next_coords):
        # 获取坐标
        x1, y1 = prev_node
        x2, y2 = next_coords
        x, y = curr_gnss

        # 计算方向向量
        dx, dy = x2 - x1, y2 - y1

        # 计算垂线方向向量
        perp_dx, perp_dy = -dy, dx

        # 计算向量
        vec_x, vec_y = x - x2, y - y2

        # 计算点积
        dot_product = vec_x * perp_dx + vec_y * perp_dy
        # 返回是否在垂线上
        return abs(dot_product) < 1e-6

    # 定义计算并保存偏移量的方法
    def calculate_and_save_offsets(self):
        # 尝试计算和保存偏移量
        try:
            # 如果点数不足，返回
            if len(self.precise_reached_points) < 3:
                return

            # 提取最近的3个点
            points = self.precise_reached_points[-3:]

            # 检查是否近似直线
            angle = self.calculate_angle(points)
            # 如果角度偏差大于10度，跳过
            if abs(angle - 180) > 10:
                self.node.get_logger().warn("Points are not collinear. Skipping offset calculation.")
                return

            # 计算偏移量
            lat_errors = [point['error'][0] for point in points]
            lon_errors = [point['error'][1] for point in points]

            avg_lat_error = sum(lat_errors) / len(lat_errors)
            avg_lon_error = sum(lon_errors) / len(lon_errors)

            # 保存偏移量到文件
            try:
                # 读取旧的偏移量
                if os.path.exists(self.OFFSET_FILE_PATH):
                    with open(self.OFFSET_FILE_PATH, 'r') as offset_file:
                        old_content = offset_file.read().strip()
                else:
                    old_content = "No previous offsets"

                # 写入新的偏移量
                with open(self.OFFSET_FILE_PATH, 'w') as offset_file:
                    offset_file.write(f"{avg_lat_error}\n{avg_lon_error}")

                # 读取新的偏移量
                with open(self.OFFSET_FILE_PATH, 'r') as offset_file:
                    new_content = offset_file.read().strip()

                # 记录日志
                self.node.get_logger().info(f"[RuntimeCalibration] Old offsets: {old_content}")
                self.node.get_logger().info(f"[RuntimeCalibration] New offsets: {new_content}")
                self.node.get_logger().info("[RuntimeCalibration]***Success!***")
            # 捕获异常
            except Exception as e:
                # 记录错误日志
                self.node.get_logger().error(f"[RuntimeCalibration] Error saving offsets: {e}")

            # 标记校准完成
            self.calibrated = True
        # 捕获异常
        except Exception as e:
            # 记录错误日志
            self.node.get_logger().error(f"[RuntimeCalibration]Error calculating and saving offsets: {e}")

# 定义NextNodeRepeater类，继承自Node
class NextNodeRepeater(Node):
    # 初始化方法
    def __init__(self):
        # 调用父类初始化方法
        super().__init__('next_node_repeater')
        # 创建订阅者，订阅'/next_node'话题
        self.subscription = self.create_subscription(String, '/next_node', self.next_node_callback, 10)
        # 创建发布者，发布到'/next_node'话题
        self.publisher = self.create_publisher(String, '/next_node', 10)
        # 初始化最新消息
        self.latest_msg = None
        # 创建定时器，每2秒重复发布
        self.timer = self.create_timer(2.0, self.repeat_publish)

    # 定义next_node回调函数
    def next_node_callback(self, msg):
        # 如果消息不同，记录日志
        if self.latest_msg != msg.data:
            self.get_logger().info(f"Received /next_node: {msg.data}")
        # 更新最新消息
        self.latest_msg = msg.data

    # 定义重复发布方法
    def repeat_publish(self):
        # 如果有最新消息，发布
        if self.latest_msg is not None:
            self.publisher.publish(String(data=self.latest_msg))

# 定义PathPublisher类，继承自Node
class PathPublisher(Node):
    # 初始化方法
    def __init__(self):
        # 调用父类初始化方法
        super().__init__('path_publisher')
        # 创建发布者，发布到'/path4global'话题
        self.publisher = self.create_publisher(Path, '/path4global', 10)
        # 初始化最新路径
        self.latest_path = None
        # 创建定时器，每2秒重复发布
        self.timer = self.create_timer(2.0, self.repeat_publish)

    # 定义更新路径的方法
    def update_path(self, path_coords):
        # 如果路径为空，记录警告
        if not path_coords:
            self.get_logger().warn("Empty path received. Skipping update.")
            return

        # 删除第一个点
        if len(path_coords) > 1:
            path_coords = path_coords[1:]
        else:
            # 如果只有一个点，记录警告
            self.get_logger().warn("Path contains only one point or is empty. Skipping update.")
            return

        # 创建Path消息
        path_msg = Path()
        path_msg.header.frame_id = "map"
        path_msg.header.stamp = self.get_clock().now().to_msg()

        # 遍历路径坐标
        for i, (lon, lat) in enumerate(path_coords):
            # 创建PoseStamped
            pose = PoseStamped()
            pose.header.frame_id = "map"
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x = lon
            pose.pose.position.y = lat
            pose.pose.position.z = 0.0
            pose.pose.orientation.w = 1.0
            # 添加到路径消息
            path_msg.poses.append(pose)

        # 更新最新路径
        self.latest_path = path_msg
        # 记录日志
        self.get_logger().info(f"[PathPublisher] Updated /path with {len(path_coords)} waypoints")

    # 定义重复发布方法
    def repeat_publish(self):
        # 如果有最新路径，发布
        if self.latest_path is not None:
            self.publisher.publish(self.latest_path)

# 如果脚本作为主程序运行
if __name__ == "__main__":
    # 初始化rclpy
    rclpy.init()

    # 初始化节点
    gnss_subscriber = GnssSubscriber()
    next_node_repeater = NextNodeRepeater()
    path_publisher = PathPublisher()

    # 加载地图
    filepath = os.environ.get("FYP_GNSS_MAP_FILE", str(get_runtime_path("maps", "XJ04132316.geojson")))
    nodes, adj_list = process_map(filepath)

    # 记录等待GNSS数据的日志
    log("Waiting for GNSS data...")
    # 等待GNSS数据接收
    while not gnss_subscriber.gnss_received:
        rclpy.spin_once(gnss_subscriber)

    # 记录校准日志
    log("[==Transformer is calibrating==]")
    time.sleep(4)
    log("[==Transformer calibrated==]")

    # 寻找起点
    start_node = min(
        range(len(nodes)),
        key=lambda i: haversine(current_gnss[0], current_gnss[1], nodes[i][0], nodes[i][1])
    )
    end_node = END_NODE_ID

    # 执行A*算法
    path = astar(start_node, end_node, nodes, adj_list)
    # 如果未找到路径，记录错误并退出
    if path is None:
        log("Error: No valid path found. Exiting...")
        rclpy.shutdown()
        exit(1)

    # 转换路径ID到经纬度坐标
    path_coords = [nodes[node_id] for node_id in path]
    # 保存路径到文件
    save_path_to_file(path)

    # 发布初始路径
    path_publisher.update_path(path_coords)

    # 初始化前一个节点和当前节点
    prev_node, curr_node = path[0], path[0]
    # 初始化运行时校准器
    runtime_calibrator = RuntimeCalibration(gnss_subscriber)

    # 尝试执行路径导航
    try:
        # 遍历路径中的下一个节点
        for next_node in path[1:]:
            # 获取节点ID和坐标
            node_id = next_node
            next_coords = nodes[next_node]

            # 如果校准完成，发布第一个校准的下一个节点
            if runtime_calibrator.calibrated:
                gnss_subscriber.publisher.publish(String(data=f"{next_coords[0]},{next_coords[1]}"))
                log(f"Publishing first calibrated next node [{node_id}]: {next_coords}")
                runtime_calibrator.calibrated = False

            # 如果是第一个节点，跳过方向计算
            if prev_node == curr_node:
                log(f"Skipping direction calculation for the first node [{node_id}]")
            else:
                # 获取坐标
                prev_coords = nodes[prev_node]
                curr_coords = nodes[curr_node]

                # 定义计算角度的函数
                def calculate_angle(p1, p2):
                    return atan2(p2[1] - p1[1], p2[0] - p1[0])

                # 计算当前角度和下一个角度
                current_angle = calculate_angle(prev_coords, curr_coords)
                next_angle = calculate_angle(curr_coords, next_coords)
                # 计算角度差
                angle_diff = (next_angle - current_angle + pi) % (2 * pi) - pi

                # 根据角度差判断转向方向
                if abs(degrees(angle_diff)) <= 10:
                    turn_direction = "Go Straight"
                elif angle_diff > 0:
                    turn_direction = f"Turn Left by {degrees(angle_diff):.1f}°"
                else:
                    turn_direction = f"Turn Right by {degrees(-angle_diff):.1f}°"

                # 记录方向日志
                log(f"Direction: {turn_direction}")

            # 发布下一个节点
            gnss_subscriber.publisher.publish(String(data=f"{next_coords[0]},{next_coords[1]}"))
            log(f"Publishing next node [{node_id}]: {next_coords}")

            # 循环等待到达下一个节点
            while rclpy.ok():
                # 自旋节点
                rclpy.spin_once(gnss_subscriber, timeout_sec=0.1)
                rclpy.spin_once(next_node_repeater, timeout_sec=0.1)
                rclpy.spin_once(path_publisher, timeout_sec=0.1)
                # 如果接近下一个节点
                if haversine(current_gnss[0], current_gnss[1], next_coords[0], next_coords[1]) <= PROXIMITY_THRESHOLD:
                    # 记录到达日志
                    log(f"======Reached waypoint [{node_id}]: {next_coords}======")
                    # 检查精确到达
                    runtime_calibrator.check_precise_reached(
                        prev_node=nodes[prev_node],
                        curr_gnss=current_gnss,
                        next_coords=next_coords
                    )
                    # 跳出循环
                    break

                # 检查接近和偏航
                close, off_track = check_proximity_and_yaw(nodes[prev_node], current_gnss, next_coords, PROXIMITY_THRESHOLD)
                # 如果偏离轨道，记录警告
                if off_track:
                    log("Warning: Off track! Adjusting course...")
                # 如果接近或偏航，更新节点并跳出
                if close or off_track:
                    prev_node, curr_node = curr_node, next_node
                    break

        # 获取最终目标坐标
        final_goal_coords = nodes[end_node]
        # 如果接近最终目标，记录到达日志
        if haversine(current_gnss[0], current_gnss[1], final_goal_coords[0], final_goal_coords[1]) <= PROXIMITY_THRESHOLD:
            log(f"**********Destination reached [{end_node}]: {final_goal_coords}**********")
        else:
            # 否则记录警告
            log("Warning: Final destination not reached. Check GNSS accuracy.")
    # 捕获键盘中断
    except KeyboardInterrupt:
        log("Navigation interrupted by user.")
    # 最终块
    finally:
        # 销毁节点
        gnss_subscriber.destroy_node()
        next_node_repeater.destroy_node()
        # 关闭rclpy
        rclpy.shutdown()
# 指定Python解释器路径，用于在Unix-like系统中运行脚本
#!/usr/bin/env python3

# 导入rclpy库，用于ROS2 Python接口
import rclpy
# 从rclpy.node模块导入Node类，用于创建ROS2节点
from rclpy.node import Node
# 从sensor_msgs.msg模块导入NavSatFix消息类型，用于GNSS数据
from sensor_msgs.msg import NavSatFix
# 导入os模块，用于操作系统相关功能，如文件路径操作
import os
# 从datetime模块导入datetime类，用于处理日期和时间
from datetime import datetime
# 从collections模块导入deque类，用于实现双端队列
from collections import deque
# 从math模块导入radians, sin, cos, sqrt, atan2函数，用于数学计算
from math import radians, sin, cos, sqrt, atan2
# 导入sys模块，用于系统相关功能
import math
import sys
# 导入yaml模块，用于读取配置文件
import yaml
from pathlib import Path


def get_runtime_root():
    runtime_root = os.environ.get("FYP_RUNTIME_ROOT")
    if runtime_root:
        return Path(runtime_root).expanduser()
    return Path.home() / "fyp_runtime_data"


def get_runtime_path(*parts):
    return get_runtime_root().joinpath(*parts)


def get_session_log_path(filename, fallback_subdir):
    session_dir = os.environ.get("FYP_LOG_SESSION_DIR")
    if session_dir:
        os.makedirs(session_dir, exist_ok=True)
        return str(Path(session_dir) / filename)

    log_dir = get_runtime_path(fallback_subdir)
    os.makedirs(log_dir, exist_ok=True)
    now = datetime.now()
    return str(Path(log_dir) / f"log_{now.strftime('%Y%m%d_%H%M%S')}.txt")

LOG_SWITCH_PATH = get_runtime_path("config", "log_switch.yaml")
OFFSET_FILE_PATH = get_runtime_path("gnss", "gnss_offset.txt")
START_ID_FILE_PATH = get_runtime_path("gnss", "startid.txt")

# 定义校准所需的数据次数常量
CALIBRATION_TIMES = 5

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

# 定义校准点的字典，包含编号、经纬度和描述
CALIBRATION_POINTS = {
    # 校准点1：前门口北拐角前
    1: (31.274927, 120.737548, "前门口北拐角前"),
    # 校准点2：后门向北的丁字口
    2: (31.274953, 120.738415, "后门向北的丁字口"),
    # 校准点3：后门东北大路口
    3: (31.274964, 120.73881,  "后门东北大路口"),
    # 校准点4：前门口
    4: (31.274842, 120.737268, "前门口")
}

# 定义GnssCalibrationNode类，继承自Node类
class GnssCalibrationNode(Node):
    # 初始化方法，接收选择的校准点编号
    def __init__(self, selected_point):
        # 调用父类Node的初始化方法，设置节点名称
        super().__init__('gnss_calibration_node')
        # 创建订阅者，订阅'/fix'话题，消息类型为NavSatFix，回调函数为listener_callback，队列大小为10
        self.subscription = self.create_subscription(
            NavSatFix,
            '/fix',
            self.listener_callback,
            10
        )
        # 创建发布者，发布到'gnss'话题，消息类型为NavSatFix，队列大小为10
        self.publisher_ = self.create_publisher(NavSatFix, 'gnss', 10)
        # 初始化最新有效数据为None
        self.latest_valid_data = None
        # 设置选择的校准点编号
        self.selected_point = selected_point
        # 从校准点字典中获取参考纬度、经度和位置名称
        self.ref_lat, self.ref_lon, location_name = CALIBRATION_POINTS[selected_point]

        # 初始化纬度偏移量为0.0
        self.lat_offset = 0.0
        # 初始化经度偏移量为0.0
        self.lon_offset = 0.0

        # 初始化校准完成标志为False
        self.calibration_done = False

        # 初始化GNSS数据队列，使用deque，最大长度为校准次数
        self.gnss_data_queue = deque(maxlen=CALIBRATION_TIMES)
        # 初始化校准尝试次数为0
        self.calibration_attempts = 0

        # 检查是否启用日志
        enable_log = self.should_enable_logging("gnss_calibration_node")
        
        if enable_log:
            self.log_path = get_session_log_path("gnss_calibration.log", "logs/gnss_calibration")
            self.get_logger().info(f'Logging enabled: {self.log_path}')
        else:
            self.log_path = None
            self.get_logger().info('Logging disabled by config')

        # 记录日志，显示开始位置
        self.get_logger().info(f'Starting at {location_name}')

    # 检查是否启用日志的辅助方法
    def should_enable_logging(self, node_key: str) -> bool:
        """检查是否应该启用日志"""
        try:
            config_path = LOG_SWITCH_PATH
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # 直接读取节点配置
            if node_key in config:
                return config[node_key].get('enable_logging', True)
            
            # 如果找不到配置，默认启用日志
            self.get_logger().warn(f"No logging config found for '{node_key}', enabling by default")
            return True
            
        except Exception as e:
            self.get_logger().error(f"Failed to read log config: {e}")
            return True  # 配置文件读取失败，默认启用日志

    # 定义监听器回调函数，处理接收到的NavSatFix消息
    def listener_callback(self, msg):
        if msg.status.status < 0:
            self.get_logger().warn('GNSS status indicates no fix, skipping sample')
            return

        if not all(math.isfinite(value) for value in (msg.latitude, msg.longitude, msg.altitude)):
            self.get_logger().warn('Invalid GNSS sample (non-finite lat/lon/alt), skipping sample')
            return

        # 检查纬度和经度是否为0.0，如果是则认为是无效数据
        if msg.latitude == 0.0 and msg.longitude == 0.0:
            self.get_logger().warn('Invalid GNSS data')
            return

        if msg.position_covariance_type == NavSatFix.COVARIANCE_TYPE_UNKNOWN:
            self.get_logger().warn('GNSS covariance type unknown, skipping sample')
            return

        # 如果校准尚未完成
        if not self.calibration_done:
            # 将当前GNSS数据（纬度、经度）添加到队列中
            self.gnss_data_queue.append((msg.latitude, msg.longitude))

            # 获取当前队列长度作为进度
            progress = len(self.gnss_data_queue)
            # 记录信息日志，显示校准进度
            self.get_logger().info(f'Calibrating...Freeze! {progress}/{CALIBRATION_TIMES}')

            # 如果队列长度小于校准次数，直接返回等待更多数据
            if len(self.gnss_data_queue) < CALIBRATION_TIMES:
                return

            # 检查数据是否稳定
            if self.is_data_stable():
                # 计算队列中纬度的平均值
                avg_lat = sum(lat for lat, lon in self.gnss_data_queue) / CALIBRATION_TIMES
                # 计算队列中经度的平均值
                avg_lon = sum(lon for lat, lon in self.gnss_data_queue) / CALIBRATION_TIMES

                # 计算纬度偏移量：参考纬度减去平均纬度
                self.lat_offset = self.ref_lat - avg_lat
                # 计算经度偏移量：参考经度减去平均经度
                self.lon_offset = self.ref_lon - avg_lon
                # 设置校准完成标志为True
                self.calibration_done = True

                # 保存偏移量到文件
                self.save_offsets()

                # 记录信息日志，显示校准结果
                self.get_logger().info(f'Calibrated: lat_offset = {self.lat_offset}, lon_offset = {self.lon_offset}')
            else:
                # 如果数据不稳定，清空队列
                self.gnss_data_queue.clear()
                # 增加校准尝试次数
                self.calibration_attempts += 1
                # 记录警告日志，表示校准尝试失败
                self.get_logger().warn(f'Calibration attempt {self.calibration_attempts} failed: Data is unstable, restarting calibration.')
                # 返回，重新开始校准
                return

        # 设置最新有效数据为当前消息
        self.latest_valid_data = msg
        # 发布校准后的数据
        self.publish_calibrated_data()

    # 定义保存偏移量的方法
    def save_offsets(self):
        # 尝试打开偏移量文件进行写入
        try:
            if not math.isfinite(self.lat_offset) or not math.isfinite(self.lon_offset):
                self.get_logger().error('Refusing to save non-finite GNSS offsets')
                return

            OFFSET_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(OFFSET_FILE_PATH, 'w') as offset_file:
                # 写入纬度偏移量和经度偏移量，每行一个
                offset_file.write(f"{self.lat_offset}\n{self.lon_offset}")
            # 记录信息日志，表示偏移量已保存
            self.get_logger().info(f'Offset saved at {OFFSET_FILE_PATH}')
        # 捕获异常
        except Exception as e:
            # 记录错误日志，表示保存失败
            self.get_logger().error(f'保存偏移量失败: {e}')

    # 定义加载偏移量的方法
    def load_offsets(self):
        # 尝试加载偏移量
        try:
            # 检查偏移量文件是否存在
            if os.path.exists(OFFSET_FILE_PATH):
                # 打开文件读取
                with open(OFFSET_FILE_PATH, 'r') as offset_file:
                    # 读取所有行
                    lines = offset_file.readlines()
                    # 如果行数为2
                    if len(lines) == 2:
                        # 解析纬度偏移量
                        lat_offset = float(lines[0].strip())
                        # 解析经度偏移量
                        lon_offset = float(lines[1].strip())

                        if not math.isfinite(lat_offset) or not math.isfinite(lon_offset):
                            self.get_logger().warn(f'偏移量文件包含无效数值，忽略: {OFFSET_FILE_PATH}')
                            return None

                        # 返回加载的偏移量
                        return lat_offset, lon_offset
        # 捕获异常
        except Exception as e:
            # 记录警告日志，表示加载失败
            self.get_logger().warn(f'加载偏移量失败: {e}')
        return None

    # 定义检查数据是否稳定的方法
    def is_data_stable(self):
        # 如果队列长度小于校准次数，返回False
        if len(self.gnss_data_queue) < CALIBRATION_TIMES:
            return False

        # 获取队列中第一个点作为中心点
        center_lat, center_lon = self.gnss_data_queue[0]

        # 遍历队列中的每个点
        for lat, lon in self.gnss_data_queue:
            # 计算当前点与中心点的距离，如果超过1米，返回False
            if haversine(center_lon, center_lat, lon, lat) > 1.0:
                return False

        # 如果所有点都在1米内，返回True
        return True

    # 定义发布校准数据的方法
    def publish_calibrated_data(self):
        # 如果有最新有效数据
        if self.latest_valid_data:
            loaded_offsets = self.load_offsets()

            if loaded_offsets is None:
                self.get_logger().warn('从文件加载偏移量失败，使用变量中的偏移量')
                if not math.isfinite(self.lat_offset) or not math.isfinite(self.lon_offset):
                    self.get_logger().error('内存中的 GNSS 偏移量无效，跳过发布 /gnss')
                    return
                loaded_lat_offset, loaded_lon_offset = self.lat_offset, self.lon_offset
            else:
                loaded_lat_offset, loaded_lon_offset = loaded_offsets

            if not math.isfinite(loaded_lat_offset) or not math.isfinite(loaded_lon_offset):
                self.get_logger().error('GNSS 偏移量非有限数，跳过发布 /gnss')
                return

            # 创建校准后的NavSatFix消息
            calibrated_msg = NavSatFix()
            # 复制消息头
            calibrated_msg.header = self.latest_valid_data.header
            # 复制状态
            calibrated_msg.status = self.latest_valid_data.status
            # 应用纬度偏移量
            calibrated_msg.latitude = self.latest_valid_data.latitude + loaded_lat_offset
            # 应用经度偏移量
            calibrated_msg.longitude = self.latest_valid_data.longitude + loaded_lon_offset
            # 复制高度
            calibrated_msg.altitude = self.latest_valid_data.altitude
            # 复制位置协方差
            calibrated_msg.position_covariance = self.latest_valid_data.position_covariance
            # 复制位置协方差类型
            calibrated_msg.position_covariance_type = self.latest_valid_data.position_covariance_type
            # 发布校准后的消息
            self.publisher_.publish(calibrated_msg)

            # 由 Python 时间改动成 ROS 标准时间戳
            # ===========================================================================================================================
            # # 获取当前时间戳
            # timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # # 格式化日志条目
            # log_entry = f"{timestamp}, Lat_calibrated: {calibrated_msg.latitude:.10f}, Lon_calibrated: {calibrated_msg.longitude:.10f}\n"
            # ===========================================================================================================================

            # 改动后的代码块，现在日志中会显示标准的 ROS 时间戳
            # 获取ROS系统时间戳（19位纳秒格式）
            ros_time = self.get_clock().now()
            ros_timestamp = ros_time.nanoseconds  # 19位纳秒时间戳
            # 同时保留人类可读的时间（可选）
            readable_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # 格式化日志条目，包含两种时间戳
            log_entry = f"ROS_timestamp: {ros_timestamp}, Readable_time: [{readable_time}], Lat_calibrated: {calibrated_msg.latitude:.10f}, Lon_calibrated: {calibrated_msg.longitude:.10f}\n"

            # 直接写入日志文件（不通过ROS2日志系统）
            # 只有当日志功能启用时才写入
            if self.log_path:
                try:
                    with open(self.log_path, 'a') as log_file:
                        log_file.write(log_entry)
                except Exception as e:
                    self.get_logger().error(f'写入日志文件失败: {e}')

# 定义主函数
def main(args=None):
    # 初始化rclpy
    rclpy.init(args=args)

    # 尝试读取校准点ID
    try:
        # 定义startid文件路径
        start_id_path = START_ID_FILE_PATH
        # 打开文件读取
        with open(start_id_path, 'r') as file:
            # 读取内容并转换为整数
            point_id = int(file.read().strip())
            # 检查点ID是否在校准点字典中
            if point_id not in CALIBRATION_POINTS:
                # 抛出值错误
                raise ValueError('无效的校准点编号，请传递 1-4 的编号！')
    # 捕获文件未找到或值错误
    except (FileNotFoundError, ValueError) as e:
        # 打印错误信息
        print(f'错误: {e}')
        # 关闭rclpy
        rclpy.shutdown()
        # 返回
        return

    # 创建GnssCalibrationNode实例
    node = GnssCalibrationNode(point_id)
    # 启动节点
    rclpy.spin(node)
    # 关闭rclpy
    rclpy.shutdown()

# 如果脚本作为主程序运行，调用main函数
if __name__ == '__main__':
    main()
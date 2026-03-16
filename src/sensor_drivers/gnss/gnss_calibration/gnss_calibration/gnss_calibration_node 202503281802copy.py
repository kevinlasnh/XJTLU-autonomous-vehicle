#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix
import os
from datetime import datetime
from collections import deque
from math import radians, sin, cos, sqrt, atan2

# 定义宏：校准所需的数据次数
CALIBRATION_TIMES = 10  # 校准需要的 GNSS 数据点数

# 计算两点间的球面距离（米）
def haversine(lon1, lat1, lon2, lat2):
    R = 6371000  # 地球半径（米）
    dlon = radians(lon2 - lon1)
    dlat = radians(lat2 - lat1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

# 固定校准点
CALIBRATION_POINTS = {
    1: (31.274747, 120.738441, "后门口"),
    2: (31.274953, 120.738415, "后门向北的丁字口"),
    3: (31.274964, 120.73881, "后门东北大路口"),
    4: (31.274842, 120.737268, "前门口")
}

LOG_PATH = '/home/jetson/ros2_ws/src/GNSS/GNSSlog/gnss_global_log.txt'

class GnssCalibrationNode(Node):
    def __init__(self, selected_point):
        super().__init__('gnss_calibration_node')
        self.subscription = self.create_subscription(
            NavSatFix,
            '/fix',
            self.listener_callback,
            10
        )
        self.publisher_ = self.create_publisher(NavSatFix, 'gnss', 10)
        self.latest_valid_data = None
        self.selected_point = selected_point
        self.ref_lat, self.ref_lon, location_name = CALIBRATION_POINTS[selected_point]
        self.calibration_done = False
        self.lat_offset = 0.0
        self.lon_offset = 0.0

        # 新增：用于存储连续 GNSS 数据
        self.gnss_data_queue = deque(maxlen=CALIBRATION_TIMES)
        self.calibration_attempts = 0

        self.get_logger().info(f'成功启动在位置 {location_name}')
        self.get_logger().info('GNSS 校准节点已初始化，等待有效的传感器数据...')

    def listener_callback(self, msg):
        if msg.latitude == 0.0 and msg.longitude == 0.0:
            self.get_logger().warn('接收到无效的 GNSS 数据，已丢弃')
            return

        if not self.calibration_done:
            # 将当前数据加入队列
            self.gnss_data_queue.append((msg.latitude, msg.longitude))

            # 显示进度
            progress = len(self.gnss_data_queue)
            self.get_logger().info(f'正在校准，请勿移动 {progress}/{CALIBRATION_TIMES}')

            # 如果队列未满，直接返回
            if len(self.gnss_data_queue) < CALIBRATION_TIMES:
                return

            # 检查数据是否稳定在 1 米范围内
            if self.is_data_stable():
                # 计算平均值作为校准基准
                avg_lat = sum(lat for lat, lon in self.gnss_data_queue) / CALIBRATION_TIMES
                avg_lon = sum(lon for lat, lon in self.gnss_data_queue) / CALIBRATION_TIMES

                # 使用平均值作为校准偏移量
                self.lat_offset = self.ref_lat - avg_lat
                self.lon_offset = self.ref_lon - avg_lon
                self.calibration_done = True
                self.get_logger().info(f'完成校准: 纬度误差 {self.lat_offset}, 经度误差 {self.lon_offset}')
            else:
                # 数据不稳定，放弃这组数据
                self.gnss_data_queue.clear()
                self.calibration_attempts += 1
                self.get_logger().warn(f'第 {self.calibration_attempts} 次校准失败：数据不稳定，重新开始校准')
                return

        # 校准完成后发布校准数据
        self.latest_valid_data = msg
        self.publish_calibrated_data()

    def is_data_stable(self):
        """检查队列中的所有点是否在 1 米范围内"""
        if len(self.gnss_data_queue) < CALIBRATION_TIMES:
            return False

        # 获取第一个点作为中心点
        center_lat, center_lon = self.gnss_data_queue[0]

        # 计算每个点与中心点的距离
        for lat, lon in self.gnss_data_queue:
            if haversine(center_lon, center_lat, lon, lat) > 1.0:  # 超过 1 米
                return False

        return True

    def publish_calibrated_data(self):
        if self.latest_valid_data:
            calibrated_msg = NavSatFix()
            calibrated_msg.header = self.latest_valid_data.header
            calibrated_msg.status = self.latest_valid_data.status
            calibrated_msg.latitude = self.latest_valid_data.latitude + self.lat_offset
            calibrated_msg.longitude = self.latest_valid_data.longitude + self.lon_offset
            calibrated_msg.altitude = self.latest_valid_data.altitude
            calibrated_msg.position_covariance = self.latest_valid_data.position_covariance
            calibrated_msg.position_covariance_type = self.latest_valid_data.position_covariance_type
            self.publisher_.publish(calibrated_msg)

            # 记录日志
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"{timestamp}, Lat_calibrated: {calibrated_msg.latitude:.10f}, Lon_calibrated: {calibrated_msg.longitude:.10f}\n"
            
            # 检查文件大小，如果是新运行则添加分隔线
            if not os.path.exists(LOG_PATH) or os.stat(LOG_PATH).st_size == 0:
                with open(LOG_PATH, 'a') as log_file:
                    log_file.write('\n\n\n' + '-' * 50 + '\n')
            
            with open(LOG_PATH, 'a') as log_file:
                log_file.write(log_entry)

def main(args=None):
    rclpy.init(args=args)
    
    try:
        # 读取 startid.txt
        start_id_path = '/home/jetson/ros2_ws/src/GNSS/gnss_calibration/gnss_calibration/startid.txt'
        with open(start_id_path, 'r') as file:
            point_id = int(file.read().strip())
            if point_id not in CALIBRATION_POINTS:
                raise ValueError('无效的校准点编号，请传递 1-4 的编号！')
    except (FileNotFoundError, ValueError) as e:
        print(f'错误: {e}')
        rclpy.shutdown()
        return

    node = GnssCalibrationNode(point_id)
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
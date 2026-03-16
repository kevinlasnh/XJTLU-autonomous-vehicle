#!/usr/bin/env python3
"""
FASTLIO2 测试数据发布器
发布模拟的 IMU 和激光雷达数据用于测试 FASTLIO2 节点
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from livox_ros_driver2.msg import CustomMsg
import time
import math
import numpy as np

class FastLIO2TestPublisher(Node):
    def __init__(self):
        super().__init__('fastlio2_test_publisher')

        # 创建发布者
        self.imu_publisher = self.create_publisher(Imu, '/livox/imu', 10)
        self.lidar_publisher = self.create_publisher(CustomMsg, '/livox/lidar', 10)

        # 创建定时器
        self.imu_timer = self.create_timer(0.01, self.publish_imu)  # 100Hz IMU
        self.lidar_timer = self.create_timer(0.1, self.publish_lidar)  # 10Hz 激光雷达

        # 初始化数据
        self.start_time = self.get_clock().now()
        self.imu_seq = 0
        self.lidar_seq = 0

        self.get_logger().info('FASTLIO2 测试数据发布器已启动')
        self.get_logger().info('发布话题: /livox/imu, /livox/lidar')

    def publish_imu(self):
        """发布模拟 IMU 数据"""
        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'imu'
        msg.header.seq = self.imu_seq

        # 模拟简单的旋转运动
        t = (self.get_clock().now() - self.start_time).nanoseconds / 1e9
        msg.angular_velocity.x = 0.1 * math.sin(t)
        msg.angular_velocity.y = 0.05 * math.cos(t)
        msg.angular_velocity.z = 0.02 * math.sin(2*t)

        # 模拟重力加速度
        msg.linear_acceleration.x = 0.0
        msg.linear_acceleration.y = 0.0
        msg.linear_acceleration.z = 9.81

        # 设置协方差 (可选)
        msg.angular_velocity_covariance = [0.01, 0.0, 0.0, 0.0, 0.01, 0.0, 0.0, 0.0, 0.01]
        msg.linear_acceleration_covariance = [0.01, 0.0, 0.0, 0.0, 0.01, 0.0, 0.0, 0.0, 0.01]

        self.imu_publisher.publish(msg)
        self.imu_seq += 1

        if self.imu_seq % 100 == 0:  # 每100条消息打印一次
            self.get_logger().info(f'已发布 IMU 消息: {self.imu_seq}')

    def publish_lidar(self):
        """发布模拟激光雷达数据"""
        msg = CustomMsg()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'lidar'
        msg.header.seq = self.lidar_seq

        # 模拟激光雷达点云数据
        # 创建一个简单的圆形点云
        num_points = 1000
        radius = 5.0
        height = 2.0

        points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            z = height * math.sin(angle * 2)  # 添加一些高度变化

            # 添加一些噪声
            x += np.random.normal(0, 0.01)
            y += np.random.normal(0, 0.01)
            z += np.random.normal(0, 0.01)

            # Livox 点格式: x, y, z, intensity, tag, line
            point = [x, y, z, 100.0, 0, i % 6]  # intensity=100, tag=0, line=0-5
            points.append(point)

        msg.points = points
        msg.lidar_id = 0

        self.lidar_publisher.publish(msg)
        self.lidar_seq += 1

        self.get_logger().info(f'已发布激光雷达消息: {self.lidar_seq}, 点数: {len(points)}')

def main(args=None):
    rclpy.init(args=args)
    node = FastLIO2TestPublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
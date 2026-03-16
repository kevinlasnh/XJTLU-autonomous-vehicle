#!/usr/bin/env python3
import os
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix, Imu
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped  
from math import radians, cos, sin, atan2, degrees, pi, asin
from geopy.distance import geodesic
from datetime import datetime
from nav_msgs.msg import Path  

class CoordinateTransformer(Node):
    def __init__(self):
        super().__init__('coordinate_transformer')
        # 参数初始化
        self.origin = None  # 原点经纬度
        self.orientation_angle = None  # 初始朝向角度（北偏角度）
        self.gnss_data_queue = []  # 存储 GNSS 数据
        self.imu_angle_queue = []  # 存储 IMU 角度数据
        self.initialized = False  # 标志是否已完成初始化
        self.start_time = None  # 初始化开始时间
        # 读取角度偏置文件
        self.angle_offset = self.load_angle_offset("/home/jetson/ros2_ws/src/global2local_tf/global2local_tf/angle_offset.txt")
        self.get_logger().info(f"Loaded angle offset: {self.angle_offset} degrees")
        # 日志文件路径
        self.log_file_path = "/home/jetson/ros2_ws/src/GNSS/GNSSlog/imu_yaw.txt"
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
        # 最近一次的 IMU 数据
        self.latest_imu_yaw = None  # 存储最近一次的 IMU yaw 角度
        # 订阅 /gnss 和 /imu/data_raw
        self.gnss_subscription = self.create_subscription(
            NavSatFix,
            '/gnss',
            self.gnss_callback,
            10
        )
        self.imu_subscription = self.create_subscription(
            Imu,
            '/imu/data_raw',
            self.imu_callback,
            10
        )
        # 订阅 /next_node 并发布 /next_local
        self.next_node_subscription = self.create_subscription(
            String,
            '/next_node',
            self.next_node_callback,
            10
        )
        self.next_local_publisher = self.create_publisher(PoseStamped, '/target_pos', 10)  # 修改消息类型
        self.get_logger().info("Coordinate Transformer initialized.")

        # 新增订阅 /path4global 并发布 /path4local
        self.global_path_subscription = self.create_subscription(
            Path,
            '/path4global',
            self.global_path_callback,
            10
        )
        self.local_path_publisher = self.create_publisher(Path, '/path4local', 10)
        self.get_logger().info("Global path transformer initialized.")

    def load_angle_offset(self, file_path):
        """
        从文件中加载角度偏置值。
        :param file_path: 文件路径。
        :return: 角度偏置值（浮点数）。
        """
        try:
            with open(file_path, 'r') as f:
                angle_offset = float(f.read().strip())
            return angle_offset
        except Exception as e:
            self.get_logger().error(f"Error loading angle offset from {file_path}: {e}")
            return 0.0
        
    def global_path_callback(self, msg):
        """
        处理 /path4global 数据，进行坐标变换并发布到 /path4local。
        """
        if not self.initialized:
            self.get_logger().warn("Coordinate transformation not ready yet.")
            return

        try:
            # 创建新的 Path 消息
            local_path_msg = Path()
            local_path_msg.header.stamp = self.get_clock().now().to_msg()  # 时间戳
            local_path_msg.header.frame_id = "map"  # 设置参考坐标系（例如 "map"）

            # 遍历原始路径中的每个点，进行坐标变换
            for pose_stamped in msg.poses:
                lon = pose_stamped.pose.position.x  # 假设 x 是经度
                lat = pose_stamped.pose.position.y  # 假设 y 是纬度

                # 转换为局部直角坐标
                local_x, local_y = self.transform_coordinates(lon, lat)

                # 创建新的 PoseStamped 消息
                new_pose_stamped = PoseStamped()
                new_pose_stamped.header.stamp = self.get_clock().now().to_msg()
                new_pose_stamped.header.frame_id = "map"
                new_pose_stamped.pose.position.x = local_x
                new_pose_stamped.pose.position.y = local_y
                new_pose_stamped.pose.position.z = 0.0  # 假设是平面
                new_pose_stamped.pose.orientation = pose_stamped.pose.orientation  # 保留原始方向

                # 添加到新的路径消息中
                local_path_msg.poses.append(new_pose_stamped)

            # 发布新的路径消息
            self.local_path_publisher.publish(local_path_msg)

            # 打印日志
            # self.get_logger().info(f"Published /path4local with {len(local_path_msg.poses)} points.")

        except Exception as e:
            self.get_logger().error(f"Error transforming global path: {e}")
    
    def gnss_callback(self, msg):
        """
        处理 /gnss 数据，用于计算原点，并记录最近一次的 IMU yaw 角度。
        """
        if self.initialized:
            return  # 如果已初始化，直接返回

        if len(self.gnss_data_queue) >= 3:
            return  # 如果已经收集了 3 个 GNSS 数据，不再继续收集

        try:
            lon, lat = msg.longitude, msg.latitude
            self.gnss_data_queue.append((lon, lat))

            # 如果收集到 3 次数据，计算平均值作为原点
            if len(self.gnss_data_queue) == 3:
                avg_lon = sum(lon for lon, _ in self.gnss_data_queue) / len(self.gnss_data_queue)
                avg_lat = sum(lat for _, lat in self.gnss_data_queue) / len(self.gnss_data_queue)
                self.origin = (avg_lon, avg_lat)
                self.get_logger().info(f"Origin set: {self.origin}")

                # 如果 IMU 角度也已经完成初始化，则标记为完成
                if len(self.imu_angle_queue) > 0:
                    self.finalize_initialization()

            # 记录最近一次的 IMU yaw 角度
            if self.latest_imu_yaw is not None:
                self.log_imu_yaw()

        except Exception as e:
            self.get_logger().error(f"Error processing /gnss data: {e}")

    def imu_callback(self, msg):
        """
        处理 /imu/data_raw 数据，更新最近一次的 IMU yaw 角度，并计算平均值。
        """
        if self.initialized:
            return  # 如果已初始化，直接返回

        try:
            # 提取四元数
            x, y, z, w = msg.orientation.x, msg.orientation.y, msg.orientation.z, msg.orientation.w

            # 将四元数转换为欧拉角（偏航、俯仰、翻滚）
            roll, pitch, yaw = self.quaternion_to_euler(x, y, z, w)

            # 更新角度值（Yaw 是偏航角，单位为弧度）
            # 注意：IMU 的角度是顺时针减小的，因此需要取反
            angle = (degrees(-yaw) + 360) % 360  # 转换为 0-360 度

            # 加上角度偏置
            angle = (angle + self.angle_offset) % 360

            # 将最新的 IMU yaw 角度添加到队列中
            if len(self.imu_angle_queue) < 3:  # 最多存储 3 个数据
                self.imu_angle_queue.append(angle)
                self.get_logger().info(f"IMU yaw added to queue: {angle:.2f} degrees")

            # 如果已经收集了 3 个数据，计算平均值
            if len(self.imu_angle_queue) == 3 and self.latest_imu_yaw is None:
                self.latest_imu_yaw = sum(self.imu_angle_queue) / len(self.imu_angle_queue)
                self.get_logger().info(f"IMU yaw average calculated: {self.latest_imu_yaw:.2f} degrees")

                # 如果 GNSS 数据也已经完成初始化，则标记为完成
                if self.origin is not None:
                    self.finalize_initialization()

        except Exception as e:
            self.get_logger().error(f"Error processing /imu/data_raw data: {e}")

    def log_imu_yaw(self):
        """
        记录最近一次的 IMU yaw 角度到文件。
        """
        try:
            if self.latest_imu_yaw is None:
                self.get_logger().warn("No IMU yaw data available to log.")
                return

            # 获取当前时间戳
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 写入文件
            with open(self.log_file_path, "a") as f:
                f.write(f"{current_time}, yaw={self.latest_imu_yaw:.2f}\n")
            self.get_logger().info(f"Logged yaw: {self.latest_imu_yaw:.2f} degrees at {current_time}")

        except Exception as e:
            self.get_logger().error(f"Error logging IMU yaw: {e}")

    def finalize_initialization(self):
        """
        完成初始化过程，包括计算初始朝向角度。
        """
        if len(self.imu_angle_queue) == 0 and self.latest_imu_yaw is not None:
            self.imu_angle_queue.append(self.latest_imu_yaw)

        if len(self.imu_angle_queue) > 0:
            self.orientation_angle = sum(self.imu_angle_queue) / len(self.imu_angle_queue)
        else:
            self.orientation_angle = 0.0

        self.initialized = True
        self.get_logger().info("Coordinate transformation matrix initialized.")
        self.get_logger().info(f"Initial orientation angle: {self.orientation_angle:.2f} degrees")

    def quaternion_to_euler(self, x, y, z, w):
        """
        将四元数转换为欧拉角（roll, pitch, yaw）。
        :param x, y, z, w: 四元数的分量。
        :return: (roll, pitch, yaw) 弧度制。
        """
        # 计算偏航角（yaw）
        t0 = +2.0 * (w * z + x * y)
        t1 = +1.0 - 2.0 * (y * y + z * z)
        yaw = atan2(t0, t1)

        # 计算俯仰角（pitch）
        t2 = +2.0 * (w * y - z * x)
        t2 = +1.0 if t2 > +1.0 else t2
        t2 = -1.0 if t2 < -1.0 else t2
        pitch = asin(t2)

        # 计算翻滚角（roll）
        t3 = +2.0 * (w * x + y * z)
        t4 = +1.0 - 2.0 * (x * x + y * y)
        roll = atan2(t3, t4)

        return roll, pitch, yaw
    def transform_coordinates(self, lon, lat):
        """
        将经纬度坐标转换为局部直角坐标。
        """
        # 计算相对于原点的距离（米）
        origin_lon, origin_lat = self.origin
        dx = geodesic((origin_lat, origin_lon), (origin_lat, lon)).meters  # 经度方向
        dy = geodesic((origin_lat, origin_lon), (lat, origin_lon)).meters  # 纬度方向

        # 如果经度减小，dx 为负；如果纬度减小，dy 为负
        if lon < origin_lon:
            dx = -dx
        if lat < origin_lat:
            dy = -dy

        # 根据初始朝向角度进行旋转校正
        theta = radians(self.orientation_angle - 90)
        rotated_x = dx * cos(theta) - dy * sin(theta)
        rotated_y = dx * sin(theta) + dy * cos(theta)

        return rotated_x, rotated_y
    
    def next_node_callback(self, msg):
        """
        处理 /next_node 数据，进行坐标变换并发布到 /next_local。
        """
        if not self.initialized:
            self.get_logger().warn("Coordinate transformation not ready yet.")
            return
        try:
            # 解析 /next_node 数据
            lon, lat = map(float, msg.data.split(','))
            # 将经纬度转换为局部直角坐标
            local_x, local_y = self.transform_coordinates(lon, lat)

            # 创建 PoseStamped 消息
            pose_stamped_msg = PoseStamped()
            pose_stamped_msg.header.stamp = self.get_clock().now().to_msg()  # 时间戳
            pose_stamped_msg.header.frame_id = "map"  # 设置参考坐标系（例如 "map"）
            pose_stamped_msg.pose.position.x = local_x  # 设置 x 坐标
            pose_stamped_msg.pose.position.y = local_y  # 设置 y 坐标
            pose_stamped_msg.pose.position.z = 0.0  # 设置 z 坐标（假设是平面）
            pose_stamped_msg.pose.orientation.w = 1.0  # 设置默认方向（无旋转）

            # 发布 PoseStamped 消息
            self.next_local_publisher.publish(pose_stamped_msg)

            # 打印变换后的坐标
            self.get_logger().info(f"Published next_local coordinates: ({local_x:.2f}, {local_y:.2f})")
        except Exception as e:
            self.get_logger().error(f"Error transforming coordinates: {e}")

def main(args=None):
    rclpy.init(args=args)

    transformer = CoordinateTransformer()

    try:
        rclpy.spin(transformer)
    except KeyboardInterrupt:
        transformer.get_logger().info("Shutting down coordinate transformer...")
    finally:
        transformer.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
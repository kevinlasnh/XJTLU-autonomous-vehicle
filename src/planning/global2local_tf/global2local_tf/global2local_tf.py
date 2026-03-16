# 指定Python解释器路径，用于在Unix-like系统中运行脚本
#!/usr/bin/env python3
# 导入os模块，用于操作系统相关功能，如文件路径操作
import os
# 导入rclpy库，用于ROS2 Python接口
import rclpy
# 从rclpy.node模块导入Node类，用于创建ROS2节点
from rclpy.node import Node
# 从sensor_msgs.msg模块导入NavSatFix和Imu消息类型，用于GNSS和IMU数据
from sensor_msgs.msg import NavSatFix, Imu
# 从std_msgs.msg模块导入String消息类型，用于字符串消息
from std_msgs.msg import String
# 从geometry_msgs.msg模块导入PoseStamped消息类型，用于姿态消息
from geometry_msgs.msg import PoseStamped
# 从math模块导入radians, cos, sin, atan2, degrees, pi, asin函数，用于数学计算
from math import radians, cos, sin, atan2, degrees, pi, asin
# 从geopy.distance模块导入geodesic函数，用于计算大地距离
from geopy.distance import geodesic
# 从datetime模块导入datetime类，用于处理日期和时间
from datetime import datetime
# 从nav_msgs.msg模块导入Path消息类型，用于路径消息
from nav_msgs.msg import Path

# 节点名称：coordinate_transformer

# 节点功能（目前）：
# 这个坐标转换节点先从GNSS话题里攒够三组经纬度来确定车辆当前的小地图原点，
# 再结合IMU提供的航向角（叠加角度偏置并求平均）锁定局部坐标系，
# 等坐标系就绪后，
# 它一旦收到“下一个目标”或全局路径的经纬度序列，
# 就用大地测距计算东西南北的偏移量，
# 按初始航向把它们旋转到车体惯常使用的平面坐标，
# 随后将转换结果分别打包成单点目标或整条局部路径发布出去，
# 实现了从经纬度和航向输入到地图坐标输出的完整流程

# 节点输入数据（目前）：
# 1. /gnss（由GNSS接收器发布，提供全球坐标系下的位置信息）
# 2. /imu/data_raw（来自外部IMU传感器的数据，提供独立的姿态和运动测量）
# 3. /next_node（由上游规划模块发布，表示路径中的下一个目标点）
# 4. /path4global（由全局路径规划器发布，表示从GNSS坐标系下的完整路径）

# 节点输出数据（目前）：
# 1. /path4local（由 coordinate_transformer 节点发布，表示转换后的局部坐标系路径）

# 定义CoordinateTransformer类，继承自Node
class CoordinateTransformer(Node):
    # 初始化方法
    def __init__(self):
        # 调用父类Node的初始化方法，设置节点名称
        super().__init__('coordinate_transformer')
        # 初始化原点经纬度为None
        self.origin = None
        # 初始化初始朝向角度为None
        self.orientation_angle = None
        # 初始化GNSS数据队列为空列表
        self.gnss_data_queue = []
        # 初始化IMU角度数据队列为空列表
        self.imu_angle_queue = []
        # 初始化初始化完成标志为False
        self.initialized = False
        # 初始化开始时间为None
        self.start_time = None
        # 加载角度偏置文件
        self.angle_offset = self.load_angle_offset("/home/jetson/ros2_ws/src/global2local_tf/global2local_tf/angle_offset.txt")
        # 记录加载的角度偏置日志
        self.get_logger().info(f"Loaded angle offset: {self.angle_offset} degrees")
        # 设置日志文件路径
        self.log_file_path = "/home/jetson/ros2_ws/src/GNSS/GNSSlog/imu_yaw.txt"
        # 创建日志文件目录（如果不存在）
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
        # 初始化最近一次的IMU数据为None
        self.latest_imu_yaw = None
        # 创建GNSS订阅者，订阅'/gnss'话题
        self.gnss_subscription = self.create_subscription(
            NavSatFix,
            '/gnss',
            self.gnss_callback,
            10
        )
        # 创建IMU订阅者，订阅'/imu/data_raw'话题
        self.imu_subscription = self.create_subscription(
            Imu,
            '/imu/data_raw',
            self.imu_callback,
            10
        )
        # 创建next_node订阅者，订阅'/next_node'话题
        self.next_node_subscription = self.create_subscription(
            String,
            '/next_node',
            self.next_node_callback,
            10
        )
        # 创建next_local发布者，发布到'/target_pos'话题
        self.next_local_publisher = self.create_publisher(PoseStamped, '/target_pos', 10)
        # 记录坐标变换器初始化日志
        self.get_logger().info("Coordinate Transformer initialized.")

        # 创建global_path订阅者，订阅'/path4global'话题
        self.global_path_subscription = self.create_subscription(
            Path,
            '/path4global',
            self.global_path_callback,
            10
        )
        # 创建local_path发布者，发布到'/path4local'话题
        self.local_path_publisher = self.create_publisher(Path, '/path4local', 10)
        # 记录全局路径变换器初始化日志
        self.get_logger().info("Global path transformer initialized.")

    # 定义加载角度偏置的方法
    def load_angle_offset(self, file_path):
        # 尝试打开文件读取角度偏置
        try:
            with open(file_path, 'r') as f:
                angle_offset = float(f.read().strip())
            # 返回角度偏置
            return angle_offset
        # 捕获异常
        except Exception as e:
            # 记录错误日志
            self.get_logger().error(f"Error loading angle offset from {file_path}: {e}")
            # 返回默认值0.0
            return 0.0

    # 定义全局路径回调方法
    def global_path_callback(self, msg):
        # 如果未初始化，记录警告并返回
        if not self.initialized:
            self.get_logger().warn("Coordinate transformation not ready yet.")
            return

        # 尝试处理路径数据
        try:
            # 创建新的Path消息
            local_path_msg = Path()
            local_path_msg.header.stamp = self.get_clock().now().to_msg()
            local_path_msg.header.frame_id = "map"

            # 遍历原始路径中的每个点
            for pose_stamped in msg.poses:
                lon = pose_stamped.pose.position.x
                lat = pose_stamped.pose.position.y

                # 转换为局部直角坐标
                local_x, local_y = self.transform_coordinates(lon, lat)

                # 创建新的PoseStamped消息
                new_pose_stamped = PoseStamped()
                new_pose_stamped.header.stamp = self.get_clock().now().to_msg()
                new_pose_stamped.header.frame_id = "map"
                new_pose_stamped.pose.position.x = local_x
                new_pose_stamped.pose.position.y = local_y
                new_pose_stamped.pose.position.z = 0.0
                new_pose_stamped.pose.orientation = pose_stamped.pose.orientation

                # 添加到新的路径消息中
                local_path_msg.poses.append(new_pose_stamped)

            # 发布新的路径消息
            self.local_path_publisher.publish(local_path_msg)

        # 捕获异常
        except Exception as e:
            # 记录错误日志
            self.get_logger().error(f"Error transforming global path: {e}")

    # 定义GNSS回调方法
    def gnss_callback(self, msg):
        # 如果已初始化，直接返回
        if self.initialized:
            return

        # 如果GNSS数据队列长度大于等于3，直接返回
        if len(self.gnss_data_queue) >= 3:
            return

        # 尝试处理GNSS数据
        try:
            lon, lat = msg.longitude, msg.latitude
            # 添加到GNSS数据队列
            self.gnss_data_queue.append((lon, lat))

            # 如果收集到3次数据，计算平均值作为原点
            if len(self.gnss_data_queue) == 3:
                avg_lon = sum(lon for lon, _ in self.gnss_data_queue) / len(self.gnss_data_queue)
                avg_lat = sum(lat for _, lat in self.gnss_data_queue) / len(self.gnss_data_queue)
                self.origin = (avg_lon, avg_lat)
                # 记录原点设置日志
                self.get_logger().info(f"Origin set: {self.origin}")

                # 如果IMU角度也已经完成初始化，则标记为完成
                if len(self.imu_angle_queue) > 0:
                    self.finalize_initialization()

            # 如果有最新的IMU yaw，记录日志
            if self.latest_imu_yaw is not None:
                self.log_imu_yaw()

        # 捕获异常
        except Exception as e:
            # 记录错误日志
            self.get_logger().error(f"Error processing /gnss data: {e}")

    # 定义IMU回调方法
    def imu_callback(self, msg):
        # 如果已初始化，直接返回
        if self.initialized:
            return

        # 尝试处理IMU数据
        try:
            # 提取四元数分量
            x, y, z, w = msg.orientation.x, msg.orientation.y, msg.orientation.z, msg.orientation.w

            # 将四元数转换为欧拉角
            roll, pitch, yaw = self.quaternion_to_euler(x, y, z, w)

            # 设置角度为268度
            angle = 268
            # 加上角度偏置
            angle = (angle + self.angle_offset) % 360

            # 如果IMU角度队列长度小于3，添加角度
            if len(self.imu_angle_queue) < 3:
                self.imu_angle_queue.append(angle)
                # 记录添加角度日志
                self.get_logger().info(f"IMU yaw added to queue: {angle:.2f} degrees")

            # 如果收集了3个数据且latest_imu_yaw为None，计算平均值
            if len(self.imu_angle_queue) == 3 and self.latest_imu_yaw is None:
                self.latest_imu_yaw = sum(self.imu_angle_queue) / len(self.imu_angle_queue)
                # 记录平均值日志
                self.get_logger().info(f"IMU yaw average calculated: {self.latest_imu_yaw:.2f} degrees")

                # 如果GNSS数据也已经完成初始化，则标记为完成
                if self.origin is not None:
                    self.finalize_initialization()

        # 捕获异常
        except Exception as e:
            # 记录错误日志
            self.get_logger().error(f"Error processing /imu/data_raw data: {e}")

    # 定义记录IMU yaw的方法
    def log_imu_yaw(self):
        # 尝试记录IMU yaw
        try:
            # 如果没有IMU yaw数据，记录警告
            if self.latest_imu_yaw is None:
                self.get_logger().warn("No IMU yaw data available to log.")
                return

            # 获取当前时间戳
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 写入文件
            with open(self.log_file_path, "a") as f:
                f.write(f"{current_time}, yaw={self.latest_imu_yaw:.2f}\n")
            # 记录日志
            self.get_logger().info(f"Logged yaw: {self.latest_imu_yaw:.2f} degrees at {current_time}")

        # 捕获异常
        except Exception as e:
            # 记录错误日志
            self.get_logger().error(f"Error logging IMU yaw: {e}")

    # 定义完成初始化方法
    def finalize_initialization(self):
        # 如果IMU角度队列为空且有latest_imu_yaw，添加到队列
        if len(self.imu_angle_queue) == 0 and self.latest_imu_yaw is not None:
            self.imu_angle_queue.append(self.latest_imu_yaw)

        # 如果IMU角度队列不为空，计算平均值作为朝向角度
        if len(self.imu_angle_queue) > 0:
            self.orientation_angle = sum(self.imu_angle_queue) / len(self.imu_angle_queue)
        else:
            # 否则设置为0.0
            self.orientation_angle = 0.0

        # 设置初始化完成标志
        self.initialized = True
        # 记录初始化完成日志
        self.get_logger().info("Coordinate transformation matrix initialized.")
        # 记录初始朝向角度日志
        self.get_logger().info(f"Initial orientation angle: {self.orientation_angle:.2f} degrees")

    # 定义四元数到欧拉角转换方法
    def quaternion_to_euler(self, x, y, z, w):
        # 计算偏航角
        t0 = +2.0 * (w * z + x * y)
        t1 = +1.0 - 2.0 * (y * y + z * z)
        yaw = atan2(t0, t1)

        # 计算俯仰角
        t2 = +2.0 * (w * y - z * x)
        t2 = +1.0 if t2 > +1.0 else t2
        t2 = -1.0 if t2 < -1.0 else t2
        pitch = asin(t2)

        # 计算翻滚角
        t3 = +2.0 * (w * x + y * z)
        t4 = +1.0 - 2.0 * (x * x + y * y)
        roll = atan2(t3, t4)

        # 返回欧拉角
        return roll, pitch, yaw

    # 定义坐标变换方法
    def transform_coordinates(self, lon, lat):
        # 获取原点经纬度
        origin_lon, origin_lat = self.origin
        # 计算经度方向距离
        dx = geodesic((origin_lat, origin_lon), (origin_lat, lon)).meters
        # 计算纬度方向距离
        dy = geodesic((origin_lat, origin_lon), (lat, origin_lon)).meters

        # 如果经度减小，dx为负
        if lon < origin_lon:
            dx = -dx
        # 如果纬度减小，dy为负
        if lat < origin_lat:
            dy = -dy

        # 根据初始朝向角度进行旋转校正
        theta = radians(self.orientation_angle - 90)
        rotated_x = dx * cos(theta) - dy * sin(theta)
        rotated_y = dx * sin(theta) + dy * cos(theta)

        # 返回旋转后的坐标
        return rotated_x, rotated_y

    # 定义next_node回调方法
    def next_node_callback(self, msg):
        # 如果未初始化，记录警告并返回
        if not self.initialized:
            self.get_logger().warn("Coordinate transformation not ready yet.")
            return
        # 尝试处理next_node数据
        try:
            # 解析数据为经纬度
            lon, lat = map(float, msg.data.split(','))
            # 转换为局部直角坐标
            local_x, local_y = self.transform_coordinates(lon, lat)

            # 创建PoseStamped消息
            pose_stamped_msg = PoseStamped()
            pose_stamped_msg.header.stamp = self.get_clock().now().to_msg()
            pose_stamped_msg.header.frame_id = "map"
            pose_stamped_msg.pose.position.x = local_x
            pose_stamped_msg.pose.position.y = local_y
            pose_stamped_msg.pose.position.z = 0.0
            pose_stamped_msg.pose.orientation.w = 1.0

            # 发布消息
            self.next_local_publisher.publish(pose_stamped_msg)

            # 记录发布坐标日志
            self.get_logger().info(f"Published next_local coordinates: ({local_x:.2f}, {local_y:.2f})")
        # 捕获异常
        except Exception as e:
            # 记录错误日志
            self.get_logger().error(f"Error transforming coordinates: {e}")

# 定义主函数
def main(args=None):
    # 初始化rclpy
    rclpy.init(args=args)

    # 创建CoordinateTransformer实例
    transformer = CoordinateTransformer()

    # 尝试运行节点
    try:
        rclpy.spin(transformer)
    # 捕获键盘中断
    except KeyboardInterrupt:
        # 记录关闭日志
        transformer.get_logger().info("Shutting down coordinate transformer...")
    # 最终块
    finally:
        # 销毁节点
        transformer.destroy_node()
        # 关闭rclpy
        rclpy.shutdown()

# 如果脚本作为主程序运行，调用main函数
if __name__ == "__main__":
    main()
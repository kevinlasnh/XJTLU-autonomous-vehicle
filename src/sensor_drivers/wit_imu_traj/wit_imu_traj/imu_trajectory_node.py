import os
import time
from pathlib import Path
from math import sin, cos, radians
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped


def get_runtime_root():
    runtime_root = os.environ.get("FYP_RUNTIME_ROOT")
    if runtime_root:
        return Path(runtime_root).expanduser()
    return Path.home() / "fyp_runtime_data"


def get_runtime_path(*parts):
    return get_runtime_root().joinpath(*parts)


class IMUTrajectoryNode(Node):
    def __init__(self):
        super().__init__('imu_trajectory_node')

        # 订阅 /imu/raw 主题
        self.imu_subscription = self.create_subscription(
            Imu,
            '/imu/data_raw',
            self.imu_callback,
            10
        )

        # 发布路径消息
        self.path_publisher = self.create_publisher(Path, '/imu/trajectory', 10)

        # 初始化变量
        self.current_position = [0.0, 0.0, 0.0]  # 当前位置 (x, y, z)
        self.current_orientation = [0.0, 0.0, 0.0]  # 当前方向角 (roll, pitch, yaw)
        self.path_msg = Path()  # 路径消息
        self.path_msg.header.frame_id = "map"

        default_log_file = get_runtime_path("logs", "imu_trajectory", "imu_trajectory_log.txt")
        self.declare_parameter("log_file_path", str(default_log_file))
        self.log_file_path = self.get_parameter("log_file_path").value
        Path(self.log_file_path).parent.mkdir(parents=True, exist_ok=True)

        self.get_logger().info(f"Trajectory log will be saved to: {self.log_file_path}")

        # 缓冲区初始化
        self.buffer_size = 5  # 缓冲区大小
        self.linear_acceleration_buffer = []  # 线性加速度缓冲区
        self.angular_velocity_buffer = []  # 角速度缓冲区
        self.timestamp_buffer = []  # 时间戳缓冲区

    def imu_callback(self, msg):
        """
        处理 /imu/raw 数据，更新位置并保存轨迹。
        """
        # 获取当前时间戳
        current_timestamp = rclpy.time.Time.from_msg(msg.header.stamp)

        # 提取 IMU 数据
        linear_acceleration = [
            msg.linear_acceleration.x,
            msg.linear_acceleration.y,
            msg.linear_acceleration.z
        ]
        angular_velocity = [
            msg.angular_velocity.x,
            msg.angular_velocity.y,
            msg.angular_velocity.z
        ]

        # 将数据添加到缓冲区
        self.linear_acceleration_buffer.append(linear_acceleration)
        self.angular_velocity_buffer.append(angular_velocity)
        self.timestamp_buffer.append(current_timestamp)

        # 如果缓冲区未满，直接返回
        if len(self.linear_acceleration_buffer) < self.buffer_size:
            return

        # 计算平均值
        avg_linear_acceleration = [
            sum(acc[i] for acc in self.linear_acceleration_buffer) / self.buffer_size
            for i in range(3)
        ]
        avg_angular_velocity = [
            sum(ang[i] for ang in self.angular_velocity_buffer) / self.buffer_size
            for i in range(3)
        ]

        # 计算时间差 dt（基于缓冲区中的第一个和最后一个时间戳）
        first_timestamp = self.timestamp_buffer[0]
        last_timestamp = self.timestamp_buffer[-1]
        dt = (last_timestamp - first_timestamp).nanoseconds * 1e-9  # 纳秒转秒

        # 清空缓冲区
        self.linear_acceleration_buffer.clear()
        self.angular_velocity_buffer.clear()
        self.timestamp_buffer.clear()

        # 更新方向角（简单积分模型）
        self.current_orientation[0] += avg_angular_velocity[0] * dt
        self.current_orientation[1] += avg_angular_velocity[1] * dt
        self.current_orientation[2] += avg_angular_velocity[2] * dt

        # 更新位置（简单积分模型）
        self.current_position[0] += avg_linear_acceleration[0] * dt**2
        self.current_position[1] += avg_linear_acceleration[1] * dt**2
        self.current_position[2] += avg_linear_acceleration[2] * dt**2

        # 创建新的路径点
        pose_stamped = PoseStamped()
        pose_stamped.header.stamp = last_timestamp.to_msg()
        pose_stamped.header.frame_id = "map"
        pose_stamped.pose.position.x = self.current_position[0]
        pose_stamped.pose.position.y = self.current_position[1]
        pose_stamped.pose.position.z = self.current_position[2]

        # 添加到路径消息中
        self.path_msg.poses.append(pose_stamped)

        # 发布路径消息
        self.path_publisher.publish(self.path_msg)

        # 保存轨迹到日志文件
        self.save_trajectory_to_file()

    def save_trajectory_to_file(self):
        """
        将当前轨迹保存到日志文件。
        """
        try:
            with open(self.log_file_path, "a") as f:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                f.write(f"{timestamp}, position={self.current_position}, orientation={self.current_orientation}\n")
        except Exception as e:
            self.get_logger().error(f"Error saving trajectory log: {e}")


def main(args=None):
    rclpy.init(args=args)

    node = IMUTrajectoryNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down IMU trajectory node...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
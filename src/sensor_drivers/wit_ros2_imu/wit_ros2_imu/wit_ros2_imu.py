# 导入时间模块，用于时间相关操作
import time
# 导入数学模块，用于数学计算
import math
# 导入串口通信模块，用于与IMU设备通信
import serial
# 导入结构体模块，用于数据打包和解包
import struct
# 导入NumPy模块，用于数值计算和数组操作
import numpy as np
# 导入线程模块，用于多线程处理
import threading
# 导入ROS2 Python客户端库
import rclpy
# 从ROS2节点模块导入Node类，用于创建ROS2节点
from rclpy.node import Node
# 从ROS2日志模块导入get_logger，用于日志记录
from rclpy.logging import get_logger
# 从传感器消息模块导入Imu消息类型，用于发布IMU数据
from sensor_msgs.msg import Imu
# 导入操作系统模块，用于文件和目录操作
import os
# 从datetime模块导入datetime类，用于时间处理
from datetime import datetime
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

# 文件最新改动时间：2025.10.9
# 文件改动人：鹏

# 初始化全局变量key，用于数据缓冲区索引
key = 0
# 初始化全局变量flag，用于状态标志
flag = 0
# 初始化全局变量buff，用于存储串口数据缓冲区
buff = {}
# 初始化全局变量angularVelocity，用于存储角速度数据
angularVelocity = [0, 0, 0]
# 初始化全局变量acceleration，用于存储加速度数据
acceleration = [0, 0, 0]
# 初始化全局变量magnetometer，用于存储磁力计数据
magnetometer = [0, 0, 0]
# 初始化全局变量angle_degree，用于存储角度数据（度）
angle_degree = [0, 0, 0]


# 定义十六进制数据转换为短整型的函数
def hex_to_short(raw_data):
    # 使用struct.unpack解包数据为四个短整型
    return list(struct.unpack("hhhh", bytearray(raw_data)))


# 定义校验和检查函数
def check_sum(list_data, check_data):
    # 计算数据列表的和并与校验数据比较
    return sum(list_data) & 0xff == check_data


# 定义处理串口数据的函数
def handle_serial_data(raw_data):
    # 声明全局变量，用于在函数内修改
    global buff, key, angle_degree, magnetometer, acceleration, angularVelocity, pub_flag
    # 初始化角度标志为False
    angle_flag = False
    # 将原始数据存储到缓冲区
    buff[key] = raw_data

    # 增加缓冲区索引
    key += 1
    # 检查数据头是否为0x55
    if buff[0] != 0x55:
        # 如果不是，重置索引
        key = 0
        # 返回，不继续处理
        return
    # 根据数据长度判断是否可以获取相应长度的数据
    if key < 11:
        # 如果长度不足，返回等待更多数据
        return
    else:
        # 获取缓冲区字典的值列表
        data_buff = list(buff.values())
        # 检查数据类型是否为加速度数据（0x51）
        if buff[1] == 0x51:
            # 校验数据校验和
            if check_sum(data_buff[0:10], data_buff[10]):
                # 解析加速度数据并转换为实际值
                acceleration = [hex_to_short(data_buff[2:10])[i] / 32768.0 * 16 * 9.8 for i in range(0, 3)]
            else:
                # 校验失败，记录警告信息
                get_logger('imu_driver').warn('0x51 Check failure')

        # 检查数据类型是否为角速度数据（0x52）
        elif buff[1] == 0x52:
            # 校验数据校验和
            if check_sum(data_buff[0:10], data_buff[10]):
                # 解析角速度数据并转换为弧度每秒
                angularVelocity = [hex_to_short(data_buff[2:10])[i] / 32768.0 * 2000 * math.pi / 180 for i in
                                   range(0, 3)]

            else:
                # 校验失败，记录警告信息
                get_logger('imu_driver').warn('0x52 Check failure')

        # 检查数据类型是否为角度数据（0x53）
        elif buff[1] == 0x53:
            # 校验数据校验和
            if check_sum(data_buff[0:10], data_buff[10]):
                # 解析角度数据并转换为度
                angle_degree = [hex_to_short(data_buff[2:10])[i] / 32768.0 * 180 for i in range(0, 3)]
                # 设置角度标志为True
                angle_flag = True
            else:
                # 校验失败，记录警告信息
                get_logger('imu_driver').warn('0x53 Check failure')
        # 检查数据类型是否为磁力计数据（0x54）
        elif buff[1] == 0x54:
            # 校验数据校验和
            if check_sum(data_buff[0:10], data_buff[10]):
                # 解析磁力计原始数据
                magnetometer_raw = hex_to_short(data_buff[2:10])

                # 应用校准值进行校准
                magnetometer_calibrated = [
                    (magnetometer_raw[0] - 4623) / 6589,
                    (magnetometer_raw[1] - 2637) / 6589,
                    (magnetometer_raw[2] - 189) / 6589
                ]

                # 更新全局磁力计变量
                magnetometer[:] = magnetometer_calibrated
            else:
                # 校验失败，记录警告信息
                get_logger('imu_driver').warn('0x54 Check failure')
        else:
            # 数据类型不匹配，清空缓冲区
            buff = {}
            # 重置索引
            key = 0

        # 清空缓冲区
        buff = {}
        # 重置索引
        key = 0
        # 返回角度标志
        return angle_flag


# 定义从欧拉角转换为四元数的函数
def get_quaternion_from_euler(roll, pitch, yaw):
    # 计算四元数的x分量
    qx = np.sin(roll / 2) * np.cos(pitch / 2) * np.cos(yaw / 2) - np.cos(roll / 2) * np.sin(pitch / 2) * np.sin(
        yaw / 2)
    # 计算四元数的y分量
    qy = np.cos(roll / 2) * np.sin(pitch / 2) * np.cos(yaw / 2) + np.sin(roll / 2) * np.cos(pitch / 2) * np.sin(
        yaw / 2)
    # 计算四元数的z分量
    qz = np.cos(roll / 2) * np.cos(pitch / 2) * np.sin(yaw / 2) - np.sin(roll / 2) * np.sin(pitch / 2) * np.cos(
        yaw / 2)
    # 计算四元数的w分量
    qw = np.cos(roll / 2) * np.cos(pitch / 2) * np.cos(yaw / 2) + np.sin(roll / 2) * np.sin(pitch / 2) * np.sin(
        yaw / 2)

    # 返回四元数列表
    return [qx, qy, qz, qw]


# 定义读取日志配置的辅助函数
def should_enable_logging(node_name):
    """从YAML配置文件读取节点的日志开关状态"""
    config_path = get_runtime_path("config", "log_switch.yaml")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            if node_name in config:
                return config[node_name].get('enable_logging', True)
            else:
                get_logger('imu_driver').warn(f"Node '{node_name}' not found in config, enabling logging by default")
                return True
    except Exception as e:
        get_logger('imu_driver').error(f"Failed to read config file: {e}, enabling logging by default")
        return True


# 定义IMU驱动节点类
class IMUDriverNode(Node):
    # 初始化函数，接收端口名称参数
    def __init__(self, port_name):
        # 调用父类构造函数，设置节点名称
        super().__init__('imu_driver_node')
        # 记录节点启动成功信息
        self.get_logger().info("Node 文件运行成功")

        # 初始化IMU消息对象
        self.imu_msg = Imu()
        # 设置IMU消息的坐标系ID
        self.imu_msg.header.frame_id = 'imu_link'

        # 创建IMU数据发布器，发布到'imu/data_raw'话题，队列大小为10
        self.imu_pub = self.create_publisher(Imu, 'imu/data_raw', 10)

        # 从配置文件读取日志开关
        enable_log = should_enable_logging('imu_driver_node')
        
        if enable_log:
            # 创建日志目录
            log_dir = get_runtime_path("logs", "wit_imu_log")
            os.makedirs(log_dir, exist_ok=True)

            # 生成日志文件名
            now = datetime.now()
            filename = f"wit_imu_log_{now.strftime('%Y%m%d_%H%M%S')}.txt"
            self.log_file_path = os.path.join(log_dir, filename)

            # 打开日志文件
            self.log_file = open(self.log_file_path, 'a')
            self.get_logger().info(f"Log file opened: {self.log_file_path}")
        else:
            self.log_file = None
            self.get_logger().info("Logging disabled by config")

        # 启动IMU驱动线程，传入端口名称
        self.driver_thread = threading.Thread(target=self.driver_loop, args=(port_name,))
        # 启动线程
        self.driver_thread.start()

    # 定义驱动循环函数，接收端口名称参数
    def driver_loop(self, port_name):
        # 尝试打开串口
        try:
            # 创建串口对象，设置端口、波特率和超时时间
            wt_imu = serial.Serial(port="/dev/imu_usb", baudrate=9600, timeout=0.5)
            # 检查串口是否已打开
            if wt_imu.isOpen():
                # 记录串口打开成功信息
                self.get_logger().info("\033[32mSerial port opened successfully...\033[0m")
            else:
                # 打开串口
                wt_imu.open()
                # 记录串口打开成功信息
                self.get_logger().info("\033[32mSerial port opened successfully...\033[0m")
        except Exception as e:
            # 记录异常信息
            get_logger('imu_driver').error(str(e))
            # 记录串口打开失败信息
            self.get_logger().info("\033[31mSerial port opening failure\033[0m")
            # 退出程序
            exit(0)

        # 循环读取IMU数据
        while True:
            # 尝试获取串口缓冲区中的数据量
            try:
                buff_count = wt_imu.inWaiting()
            except Exception as e:
                # 记录异常信息
                get_logger('imu_driver').error("exception:" + str(e))
                # 记录IMU断开连接信息
                get_logger('imu_driver').error("imu disconnect")
                # 退出程序
                exit(0)
            else:
                # 如果缓冲区有数据
                if buff_count > 0:
                    # 读取缓冲区数据
                    buff_data = wt_imu.read(buff_count)
                    # 遍历每个字节
                    for i in range(0, buff_count):
                        # 处理串口数据
                        tag = handle_serial_data(buff_data[i])
                        # 如果返回角度标志，处理IMU数据
                        if tag:
                            self.imu_data()

    # 定义IMU数据处理函数
    def imu_data(self):
        # 获取加速度数据
        accel_x, accel_y, accel_z = acceleration[0], acceleration[1], acceleration[2]
        # 定义加速度缩放因子
        accel_scale = 16 / 32768.0
        # 应用缩放因子
        accel_x, accel_y, accel_z = accel_x * accel_scale, accel_y * accel_scale, accel_z * accel_scale

        # 获取角速度数据
        gyro_x, gyro_y, gyro_z = angularVelocity[0], angularVelocity[1], angularVelocity[2]
        # 定义角速度缩放因子
        gyro_scale = 2000 / 32768.0
        # 应用缩放因子并转换为弧度
        gyro_x, gyro_y, gyro_z = math.radians(gyro_x * gyro_scale), math.radians(gyro_y * gyro_scale), math.radians(
            gyro_z * gyro_scale)

        # 定义时间间隔
        dt = 0.01
        # 获取角速度和加速度
        wx, wy, wz = gyro_x, gyro_y, gyro_z
        ax, ay, az = accel_x, accel_y, accel_z
        # 计算姿态
        roll, pitch, yaw = self.compute_orientation(wx, wy, wz, ax, ay, az, dt)

        # 添加磁偏角补偿（6.38° W）
        magnetic_declination = math.radians(-6.38)
        # 应用磁偏角补偿
        yaw += magnetic_declination

        # 更新IMU消息的时间戳
        self.imu_msg.header.stamp = self.get_clock().now().to_msg()
        # 设置线加速度
        self.imu_msg.linear_acceleration.x = accel_x
        self.imu_msg.linear_acceleration.y = accel_y
        self.imu_msg.linear_acceleration.z = accel_z
        # 设置角速度
        self.imu_msg.angular_velocity.x = gyro_x
        self.imu_msg.angular_velocity.y = gyro_y
        self.imu_msg.angular_velocity.z = gyro_z

        # 将角度转换为弧度
        angle_radian = [angle_degree[i] * math.pi / 180 for i in range(3)]

        # 从欧拉角获取四元数
        qua = get_quaternion_from_euler(angle_radian[0], angle_radian[1], angle_radian[2])

        # 设置姿态四元数
        self.imu_msg.orientation.x = qua[0]
        self.imu_msg.orientation.y = qua[1]
        self.imu_msg.orientation.z = qua[2]
        self.imu_msg.orientation.w = qua[3]

        # 发布IMU消息
        self.imu_pub.publish(self.imu_msg)

        # 计算ROS系统时间戳（19位纳秒格式）
        ros_timestamp = self.imu_msg.header.stamp.sec * 1000000000 + self.imu_msg.header.stamp.nanosec

        # 添加控制台输出
        self.get_logger().info(
            f"Publishing IMU data: accel({accel_x:.6f}, {accel_y:.6f}, {accel_z:.6f}), "
            f"gyro({gyro_x:.6f}, {gyro_y:.6f}, {gyro_z:.6f}), "
            f"orientation({qua[0]:.6f}, {qua[1]:.6f}, {qua[2]:.6f}, {qua[3]:.6f}), "
            f"timestamp: {ros_timestamp}"
        )

        # 写入日志文件（仅当日志启用时）
        if self.log_file:
            log_line = (
                f"Publishing IMU data: accel({accel_x:.6f}, {accel_y:.6f}, {accel_z:.6f}), "
                f"gyro({gyro_x:.6f}, {gyro_y:.6f}, {gyro_z:.6f}), "
                f"orientation({qua[0]:.6f}, {qua[1]:.6f}, {qua[2]:.6f}, {qua[3]:.6f}), "
                f"timestamp: {ros_timestamp}\n"
            )
            self.log_file.write(log_line)
            self.log_file.flush()

    # 定义计算姿态的函数
    def compute_orientation(self, wx, wy, wz, ax, ay, az, dt):
        # 计算绕x轴的旋转矩阵
        Rx = np.array([[1, 0, 0],
                       [0, math.cos(ax), -math.sin(ax)],
                       [0, math.sin(ax), math.cos(ax)]])
        # 计算绕y轴的旋转矩阵
        Ry = np.array([[math.cos(ay), 0, math.sin(ay)],
                       [0, 1, 0],
                       [-math.sin(ay), 0, math.cos(ay)]])
        # 计算绕z轴的旋转矩阵
        Rz = np.array([[math.cos(wz), -math.sin(wz), 0],
                       [math.sin(wz), math.cos(wz), 0],
                       [0, 0, 1]])
        # 计算总旋转矩阵
        R = Rz.dot(Ry).dot(Rx)

        # 从旋转矩阵计算欧拉角
        roll = math.atan2(R[2][1], R[2][2])
        pitch = math.atan2(-R[2][0], math.sqrt(R[2][1] ** 2 + R[2][2] ** 2))
        yaw = math.atan2(R[1][0], R[0][0])

        # 返回欧拉角
        return roll, pitch, yaw


# 定义主函数
def main():
    # 初始化ROS 2系统
    rclpy.init()
    # 创建IMU驱动节点，传入端口名称
    node = IMUDriverNode('/dev/ttyACM0')

    # 运行ROS 2节点
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        # 捕获键盘中断，记录关闭信息
        get_logger('imu_driver').info("\nShutting down IMU gracefully...")
    finally:
        # 停止ROS 2节点
        if 'node' in locals():
            node.destroy_node()
            # 关闭日志文件
            if hasattr(node, 'log_file') and node.log_file:
                node.log_file.close()
        # 关闭ROS 2系统
        rclpy.shutdown()


# 检查是否为主程序运行
if __name__ == '__main__':
    # 调用主函数
    main()

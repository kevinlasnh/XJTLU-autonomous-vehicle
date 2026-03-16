# 导入操作系统模块，用于文件路径操作
import os
# 从 ament_index_python 包中导入获取包共享目录的函数
from ament_index_python.packages import get_package_share_directory
# 从 launch 模块导入 LaunchDescription 类，用于定义启动描述
from launch import LaunchDescription
# 从 launch.actions 模块导入 TimerAction 和 SetEnvironmentVariable 类，用于定时启动和设置环境变量
from launch.actions import TimerAction, SetEnvironmentVariable
# 从 launch_ros.actions 模块导入 Node 类，用于定义 ROS2 节点
from launch_ros.actions import Node

# 文件最新改动时间：2025.10.13
# 文件改动人：鹏

# 节点启动：
# 1. imu
# 2. serial_twistctl_node
# 3. serial_reader_node
# 4. livox_lidar_publisher

# 车辆运行效果（文件运行后）：
# 这个 Sensor_Driver_layer_launch.py 文件运行后，
# 会启动所有传感器驱动节点，包括IMU、串口控制、串口读取和激光雷达发布节点

# 定义生成launch描述的函数
def generate_launch_description():
    # 打印启动信息
    print("\n----------------- Launch 文件启动：Sensor_Driver_layer_launch.py -----------------")

    # 获取livox_ros_driver2包中的配置文件路径
    livox_config_path = os.path.join(
        get_package_share_directory('livox_ros_driver2'),
        'config',
        'MID360_config.json'
    )

    # Livox LiDAR参数配置
    livox_ros2_params = [
        {"xfer_format": 1},    # 0-Pointcloud2(PointXYZRTL), 1-customized pointcloud format
        {"multi_topic": 0},    # 0-All LiDARs share the same topic, 1-One LiDAR one topic
        {"data_src": 0},       # 0-lidar, others-Invalid data src
        {"publish_freq": 10.0}, # freqency of publish, 5.0, 10.0, 20.0, 50.0, etc.
        {"output_data_type": 0},
        {"frame_id": 'livox_frame'},
        {"lvx_file_path": '/home/livox/livox_test.lvx'},
        {"user_config_path": livox_config_path},
        {"cmdline_input_bd_code": 'livox0000000001'}
    ]

    # 返回启动描述，包含节点定义
    return LaunchDescription(
        [
            # 设置环境变量，配置日志输出格式，让每条日志之间空一行
            SetEnvironmentVariable('RCUTILS_CONSOLE_OUTPUT_FORMAT', '\n[{severity}] [{time}] [{name}]: {message}'),

            # 定义定时动作，延时启动所有传感器节点，使用TimerAction
            TimerAction(
                # 指定延时周期为2.0秒
                period=2.0,
                # 指定动作列表，包含多个Node
                actions=[
                    # 创建 wit_ros2_imu 包的 IMU 节点的节点
                    # 节点名称为 imu，配置端口和波特率，重映射话题
                    Node(
                        package='wit_ros2_imu',
                        executable='wit_ros2_imu',
                        name='imu',
                        parameters=[{'port': '/dev/imu_usb'}, {"baud": 9600}],
                        remappings=[('/wit/imu', '/imu/data')],
                        output='screen'
                    ),
                    # 创建 serial_twistctl 包的串口控制节点的节点
                    # 节点名称为 serial_twistctl_node
                    Node(
                        package='serial_twistctl',
                        executable='serial_twistctl_node',
                        name='serial_twistctl_node',
                        output='screen'
                    ),
                    # 创建 serial_reader 包的串口读取节点的节点
                    # 节点名称为 serial_reader_node
                    Node(
                        package='serial_reader',
                        executable='serial_reader_node',
                        name='serial_reader_node',
                        output='screen'
                    ),
                    # 创建 livox_ros_driver2 包的激光雷达发布节点的节点
                    # 节点名称为 livox_lidar_publisher，配置相关参数
                    Node(
                        package='livox_ros_driver2',
                        executable='livox_ros_driver2_node',
                        name='livox_lidar_publisher',
                        parameters=livox_ros2_params,
                        output='screen'
                    )
                ]
            )
        ]
    )

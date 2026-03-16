from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # 获取 wit_ros2_imu 的 launch 文件路径
    wit_ros2_imu_launch_path = os.path.join(
        get_package_share_directory('wit_ros2_imu'),
        'launch',
        'rviz_and_imu.launch.py'
    )

    # 启动 global2local_tf 节点
    global2local_tf_node = Node(
        package='global2local_tf',
        executable='global2local_tf',
        name='coordinate_transformer',
        output='screen'
    )

    # 启动 wit_ros2_imu 的 rviz_and_imu.launch.py
    wit_ros2_imu_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(wit_ros2_imu_launch_path)
    )

    return LaunchDescription([
        global2local_tf_node,  # 启动 global2local_tf 节点
        wit_ros2_imu_launch   # 启动 wit_ros2_imu 的 rviz_and_imu.launch.py
    ])
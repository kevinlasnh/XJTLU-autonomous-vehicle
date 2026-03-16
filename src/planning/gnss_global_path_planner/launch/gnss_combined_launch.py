from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # 获取 gnss_calibration 的 launch 文件路径
    gnss_calibration_launch_path = os.path.join(
        get_package_share_directory('gnss_calibration'),
        'launch',
        'gnss_calibration_launch.py'
    )

    # 获取 global2local_tf 的 launch 文件路径
    global2local_tf_launch_path = os.path.join(
        get_package_share_directory('global2local_tf'),
        'launch',
        'global2local_tf.launch.py'
    )

    # 启动 gnss_calibration_launch.py，包含 nmea_navsat_driver 和 gnss_calibration 节点
    gnss_calibration_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gnss_calibration_launch_path)
    )

    # 启动 global_path_planner 节点
    global_path_planner_node = Node(
        package='gnss_global_path_planner',
        executable='global_path_planner.py',
        name='global_path_planner',
        output='screen'
    )

    # 启动 global2local_tf 的 launch 文件
    global2local_tf_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(global2local_tf_launch_path)
    )

    return LaunchDescription([
        gnss_calibration_launch,      # 启动 gnss_calibration
        global_path_planner_node,     # 启动 global_path_planner
        global2local_tf_launch        # 启动 global2local_tf 和 wit_ros2_imu
    ])
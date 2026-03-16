from launch import LaunchDescription
from launch.substitutions import EnvironmentVariable
import launch.actions
import launch_ros.actions
from ament_index_python.packages import get_package_share_directory
import os
from launch.actions import (DeclareLaunchArgument, GroupAction,
                            IncludeLaunchDescription, SetEnvironmentVariable)
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    # 获取 nmea_navsat_driver 的路径
    bringup_dir = get_package_share_directory('nmea_navsat_driver')
    launch_dir = os.path.join(bringup_dir, 'launch')

    # 启动 nmea_serial_driver.launch.py
    wheeltec_gps = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(launch_dir, 'nmea_serial_driver.launch.py')),
    )

    return LaunchDescription([
        # 启动 nmea_navsat_driver 的相关内容
        wheeltec_gps,

        # 启动 gps_path 节点
        launch_ros.actions.Node(
            package='wheeltec_gps_path', 
            executable='gps_path', 
            output='screen'
        ),
    ])


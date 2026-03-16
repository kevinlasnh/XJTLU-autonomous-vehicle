from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # 原有 nmea_navsat_driver 启动文件路径
    nmea_launch_path = os.path.join(
        get_package_share_directory('nmea_navsat_driver'),
        'launch',
        'nmea_serial_driver.launch.py'
    )

    # 启动 nmea_navsat_driver
    nmea_driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nmea_launch_path)
    )

    # 启动新的校准节点
    gnss_calibration = Node(
        package='gnss_calibration',  # 替换成你的新包名
        executable='gnss_calibration_node',
        name='gnss_calibration',
        output='screen'
    )

    return LaunchDescription([
        nmea_driver,
        gnss_calibration
    ])

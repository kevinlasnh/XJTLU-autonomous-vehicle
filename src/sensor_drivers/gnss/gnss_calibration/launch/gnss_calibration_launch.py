import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_nmea_params = os.path.join(
        get_package_share_directory("nmea_navsat_driver"),
        "config",
        "nmea_serial_driver.yaml",
    )
    nmea_launch_path = os.path.join(
        get_package_share_directory("nmea_navsat_driver"),
        "launch",
        "nmea_serial_driver.launch.py",
    )
    default_calibration_points = os.path.join(
        get_package_share_directory("gnss_calibration"),
        "config",
        "calibration_points.yaml",
    )

    params_file = LaunchConfiguration("params_file")
    calibration_points_file = LaunchConfiguration("calibration_points_file")

    nmea_driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nmea_launch_path),
        launch_arguments={"params_file": params_file}.items(),
    )

    gnss_calibration = Node(
        package="gnss_calibration",
        executable="gnss_calibration_node",
        name="gnss_calibration",
        output="screen",
        parameters=[{"calibration_points_file": calibration_points_file}],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "params_file",
                default_value=default_nmea_params,
                description="ROS2 parameter file used by nmea_navsat_driver",
            ),
            DeclareLaunchArgument(
                "calibration_points_file",
                default_value=default_calibration_points,
                description="Calibration point YAML used by gnss_calibration",
            ),
            nmea_driver,
            gnss_calibration,
        ]
    )

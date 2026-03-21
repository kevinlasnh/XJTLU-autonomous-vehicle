import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    bringup_share = get_package_share_directory('bringup')
    master_params_file = os.path.join(bringup_share, 'config', 'master_params.yaml')

    corridor_file_arg = DeclareLaunchArgument(
        'corridor_file',
        default_value=os.path.expanduser('~/fyp_runtime_data/gnss/two_point_corridor.yaml'),
        description='Runtime YAML for the fixed-launch two-point corridor',
    )
    startup_wait_timeout_arg = DeclareLaunchArgument(
        'startup_wait_timeout_s',
        default_value='90.0',
        description='Maximum wait time for stable /fix, TF, and Nav2 readiness',
    )

    explore_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'system_explore.launch.py')
        )
    )

    nmea_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                PathJoinSubstitution(
                    [FindPackageShare('nmea_navsat_driver'), 'launch', 'nmea_serial_driver.launch.py']
                )
            ]
        ),
        launch_arguments={'params_file': master_params_file}.items(),
    )

    corridor_runner = Node(
        package='gps_waypoint_dispatcher',
        executable='gps_corridor_runner_node',
        name='gps_corridor_runner_node',
        output='screen',
        parameters=[
            {
                'corridor_file': LaunchConfiguration('corridor_file'),
                'startup_wait_timeout_s': LaunchConfiguration('startup_wait_timeout_s'),
                'route_frame': 'map',
                'base_frame': 'base_link',
                'fix_topic': '/fix',
                'goal_reached_tolerance_m': 1.5,
            }
        ],
    )

    delayed_runner = TimerAction(period=8.0, actions=[corridor_runner])

    return LaunchDescription([
        corridor_file_arg,
        startup_wait_timeout_arg,
        explore_launch,
        nmea_launch,
        delayed_runner,
    ])
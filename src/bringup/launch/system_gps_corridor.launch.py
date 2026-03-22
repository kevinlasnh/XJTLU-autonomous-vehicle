import os
from datetime import datetime

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, Shutdown, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    bringup_share = get_package_share_directory('bringup')
    master_params_file = os.path.join(bringup_share, 'config', 'master_params.yaml')

    route_file_arg = DeclareLaunchArgument(
        'route_file',
        default_value=os.path.expanduser('~/fyp_runtime_data/gnss/current_route.yaml'),
        description='Runtime YAML for the GPS route corridor',
    )
    startup_wait_timeout_arg = DeclareLaunchArgument(
        'startup_wait_timeout_s',
        default_value='90.0',
        description='Maximum wait time for stable /fix, TF, and Nav2 readiness',
    )
    use_rviz_arg = DeclareLaunchArgument(
        'use_rviz',
        default_value='false',
        description='Whether to launch RViz together with the corridor stack',
    )

    explore_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'system_explore.launch.py')
        ),
        launch_arguments={'use_rviz': LaunchConfiguration('use_rviz')}.items(),
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
        executable='gps_route_runner_node',
        name='gps_route_runner',
        output='screen',
        on_exit=Shutdown(reason='gps_route_runner exited'),
        parameters=[
            master_params_file,
            {
                'route_file': LaunchConfiguration('route_file'),
                'startup_wait_timeout_s': LaunchConfiguration('startup_wait_timeout_s'),
                'route_frame': 'map',
                'base_frame': 'base_link',
                'fix_topic': '/fix',
                'alignment_topic': '/gps_corridor/enu_to_map',
            }
        ],
    )

    session_data_dir = os.environ.get('FYP_LOG_SESSION_DIR', '')
    if session_data_dir:
        session_root = os.path.dirname(session_data_dir)
    else:
        session_root = os.path.expanduser(
            f'~/fyp_runtime_data/logs/{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}'
        )
    bag_dir = os.path.join(session_root, 'bag')
    os.makedirs(session_root, exist_ok=True)

    bag_record = ExecuteProcess(
        cmd=[
            'ros2',
            'bag',
            'record',
            '--output',
            bag_dir,
            '/fix',
            '/fastlio2/lio_odom',
            '/tf',
            '/tf_static',
            '/gps_corridor/status',
            '/gps_corridor/goal_map',
            '/gps_corridor/path_map',
            '/cmd_vel',
            '/local_costmap/costmap',
            '/global_costmap/costmap',
            '/plan',
        ],
        output='log',
    )

    delayed_runner = TimerAction(period=8.0, actions=[corridor_runner])

    return LaunchDescription([
        route_file_arg,
        startup_wait_timeout_arg,
        use_rviz_arg,
        explore_launch,
        nmea_launch,
        bag_record,
        delayed_runner,
    ])

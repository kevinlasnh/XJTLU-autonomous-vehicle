import launch_ros.actions
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    default_pgo_config = PathJoinSubstitution(
        [FindPackageShare('pgo'), 'config', 'pgo.yaml']
    )
    pgo_config = LaunchConfiguration('pgo_config')
    use_rviz = LaunchConfiguration('use_rviz')

    livox_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('livox_ros_driver2'),
                'launch_ROS2',
                'msg_MID360_launch.py'
            ])
        ])
    )

    gnss_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('gnss_calibration'),
                'launch',
                'gnss_calibration_launch.py'
            ])
        ])
    )

    pgo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('pgo'),
                'launch',
                'pgo_launch.py'
            ])
        ]),
        launch_arguments={
            'pgo_config': pgo_config,
            'use_rviz': use_rviz,
        }.items()
    )

    serial_node = launch_ros.actions.Node(
        package='serial_twistctl',
        executable='serial_twistctl_node',
        name='serial_twistctl_node',
        output='screen',
        parameters=[
            {'port': '/dev/serial_twistctl'},
            {'baudrate': 115200},
            {'send_attempts': 1},
            {'delay_between_attempts_ms': 0}
        ]
    )

    serial_reader_node = launch_ros.actions.Node(
        package='serial_reader',
        executable='serial_reader_node',
        name='serial_reader_node',
        output='screen',
        parameters=[
            {'port': '/dev/serial_twistctl'},
            {'baud': 115200}
        ]
    )

    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('nav2_bringup'),
                'launch',
                'navigation_launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': 'false',
            'params_file': PathJoinSubstitution([
                FindPackageShare('bringup'),
                'config',
                'nav2_explore.yaml'
            ]),
        }.items()
    )

    delayed_nav2 = TimerAction(
        period=5.0,
        actions=[nav2_launch]
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'pgo_config',
            default_value=default_pgo_config,
            description='Path to the PGO YAML config file',
        ),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Whether to launch RViz together with PGO',
        ),
        livox_launch,
        gnss_launch,
        pgo_launch,
        serial_node,
        serial_reader_node,
        delayed_nav2,
    ])

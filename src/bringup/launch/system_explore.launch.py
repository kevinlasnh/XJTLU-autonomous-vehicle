import os

import launch
import launch_ros.actions
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    """
    Explore 模式 launch 文件（导航专用）

    启动顺序：
    1. 同时启动：Livox MID360 激光雷达、PGO(FASTLIO2+SLAM)+RViz、串口控制节点
    2. 启动 Nav2 导航系统（延时 5 秒）
    """

    bringup_share = get_package_share_directory("bringup")
    master_params_file = os.path.join(bringup_share, "config", "master_params.yaml")
    nav2_params_file = os.path.join(bringup_share, "config", "nav2_explore.yaml")
    corridor_bt_xml = os.path.join(
        bringup_share,
        "behavior_trees",
        "navigate_to_pose_w_replanning_3hz_and_recovery.xml",
    )
    rewritten_nav2_params = RewrittenYaml(
        source_file=nav2_params_file,
        param_rewrites={"default_nav_to_pose_bt_xml": corridor_bt_xml},
        convert_types=True,
    )

    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz",
        default_value="true",
        description="Whether to launch RViz together with the Explore stack",
    )

    livox_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                PathJoinSubstitution(
                    [
                        FindPackageShare("livox_ros_driver2"),
                        "launch_ROS2",
                        "msg_MID360_launch.py",
                    ]
                )
            ]
        )
    )

    pgo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                PathJoinSubstitution(
                    [FindPackageShare("pgo"), "launch", "pgo_launch.py"]
                )
            ]
        ),
        launch_arguments={
            "params_file": master_params_file,
            "use_rviz": LaunchConfiguration("use_rviz"),
        }.items(),
    )

    serial_node = launch_ros.actions.Node(
        package="serial_twistctl",
        executable="serial_twistctl_node",
        name="serial_twistctl_node",
        output="screen",
        parameters=[master_params_file],
    )

    serial_reader_node = launch_ros.actions.Node(
        package="serial_reader",
        executable="serial_reader_node",
        name="serial_reader_node",
        output="screen",
        parameters=[master_params_file],
    )

    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                PathJoinSubstitution(
                    [FindPackageShare("nav2_bringup"), "launch", "navigation_launch.py"]
                )
            ]
        ),
        launch_arguments={
            "use_sim_time": "false",
            "params_file": rewritten_nav2_params,
        }.items(),
    )

    delayed_nav2 = TimerAction(period=5.0, actions=[nav2_launch])

    return LaunchDescription(
        [
            use_rviz_arg,
            livox_launch,
            pgo_launch,
            serial_node,
            serial_reader_node,
            delayed_nav2,
        ]
    )

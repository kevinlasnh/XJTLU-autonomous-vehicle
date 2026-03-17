import launch_ros.actions
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    default_pgo_config = PathJoinSubstitution(
        [FindPackageShare("pgo"), "config", "pgo.yaml"]
    )
    pgo_config = LaunchConfiguration("pgo_config")
    use_rviz = LaunchConfiguration("use_rviz")

    rviz_cfg = PathJoinSubstitution(
        [FindPackageShare("pgo"), "rviz", "pgo.rviz"]
    )
    lio_config_path = PathJoinSubstitution(
        [FindPackageShare("fastlio2"), "config", "lio.yaml"]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "pgo_config",
                default_value=default_pgo_config,
                description="Path to the PGO YAML config file",
            ),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="true",
                description="Whether to launch RViz together with PGO",
            ),
            launch_ros.actions.Node(
                package="fastlio2",
                namespace="fastlio2",
                executable="lio_node",
                name="lio_node",
                output="screen",
                parameters=[{"config_path": lio_config_path}],
            ),
            launch_ros.actions.Node(
                package="pgo",
                namespace="pgo",
                executable="pgo_node",
                name="pgo_node",
                output="screen",
                parameters=[{"config_path": pgo_config}],
            ),
            launch_ros.actions.Node(
                package="rviz2",
                namespace="pgo",
                executable="rviz2",
                name="rviz2",
                output="screen",
                arguments=["-d", rviz_cfg],
                condition=IfCondition(use_rviz),
            ),
        ]
    )

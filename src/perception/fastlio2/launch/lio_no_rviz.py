import os

import launch
import launch_ros.actions
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration


def _launch_setup(context, *args, **kwargs):
    del args, kwargs

    params_file = LaunchConfiguration("params_file").perform(context).strip()
    lio_config = LaunchConfiguration("lio_config").perform(context).strip()

    fastlio_share = get_package_share_directory("fastlio2")

    lio_params = []
    if params_file:
        lio_params.append(params_file)

    legacy_lio_config = lio_config
    if not legacy_lio_config and not params_file:
        legacy_lio_config = os.path.join(fastlio_share, "config", "lio.yaml")
    if legacy_lio_config:
        lio_params.append({"config_path": legacy_lio_config})

    return [
        launch_ros.actions.Node(
            package="fastlio2",
            namespace="fastlio2",
            executable="lio_node",
            name="lio_node",
            output="screen",
            parameters=lio_params,
        ),
    ]


def generate_launch_description():
    return launch.LaunchDescription(
        [
            DeclareLaunchArgument(
                "params_file",
                default_value="",
                description=(
                    "ROS2 parameter file used by FAST-LIO2. "
                    "Leave empty to use the legacy fastlio2/config/lio.yaml file."
                ),
            ),
            DeclareLaunchArgument(
                "lio_config",
                default_value="",
                description="Optional legacy FAST-LIO2 flat YAML config path.",
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )

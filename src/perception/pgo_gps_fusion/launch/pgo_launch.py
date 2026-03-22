import os

import launch_ros.actions
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration


def _as_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on"}


def _launch_setup(context, *args, **kwargs):
    del args, kwargs

    params_file = LaunchConfiguration("params_file").perform(context).strip()
    pgo_config = LaunchConfiguration("pgo_config").perform(context).strip()
    extra_params_file = LaunchConfiguration("extra_params_file").perform(context).strip()
    use_rviz = _as_bool(LaunchConfiguration("use_rviz").perform(context))

    fastlio_share = get_package_share_directory("fastlio2")
    pgo_share = get_package_share_directory("pgo")

    lio_params = []
    if params_file:
        lio_params.append(params_file)
    else:
        lio_params.append(
            {"config_path": os.path.join(fastlio_share, "config", "lio.yaml")}
        )

    pgo_params = []
    if params_file:
        pgo_params.append(params_file)

    legacy_pgo_config = pgo_config
    if not legacy_pgo_config and not params_file:
        legacy_pgo_config = os.path.join(pgo_share, "config", "pgo.yaml")
    if legacy_pgo_config:
        pgo_params.append({"config_path": legacy_pgo_config})
    if extra_params_file:
        pgo_params.append(extra_params_file)

    rviz_cfg = os.path.join(pgo_share, "rviz", "pgo.rviz")

    actions = [
        launch_ros.actions.Node(
            package="fastlio2",
            namespace="fastlio2",
            executable="lio_node",
            name="lio_node",
            output="screen",
            parameters=lio_params,
        ),
        launch_ros.actions.Node(
            package="pgo",
            namespace="pgo",
            executable="pgo_node",
            name="pgo_node",
            output="screen",
            parameters=pgo_params,
        ),
    ]

    if use_rviz:
        actions.append(
            launch_ros.actions.Node(
                package="rviz2",
                namespace="pgo",
                executable="rviz2",
                name="rviz2",
                output="screen",
                arguments=["-d", rviz_cfg],
            )
        )

    return actions


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "params_file",
                default_value="",
                description=(
                    "ROS2 parameter file used by FAST-LIO2 and PGO. "
                    "Leave empty to use legacy package-local YAML files."
                ),
            ),
            DeclareLaunchArgument(
                "pgo_config",
                default_value="",
                description=(
                    "Optional legacy PGO flat YAML config path. "
                    "Only needed for backward compatibility such as pgo_no_gps.yaml."
                ),
            ),
            DeclareLaunchArgument(
                "extra_params_file",
                default_value="",
                description="Optional ROS2 parameter file appended only to the PGO node.",
            ),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="true",
                description="Whether to launch RViz together with PGO",
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )

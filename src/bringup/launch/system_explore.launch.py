import os
import launch
import launch_ros.actions
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    """
    Explore 模式 launch 文件（导航专用）
    
    启动顺序：
    1. 同时启动：Livox MID360 激光雷达、PGO(FASTLIO2+SLAM)+RViz、串口控制节点
    2. 启动 Nav2 导航系统（延时 5 秒）
    
    使用方法：
    ros2 launch system_entire_launch system_entire_launch_explore.py
    """

    # 1. 包含 Livox MID360 激光雷达 launch 文件
    livox_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('livox_ros_driver2'),
                'launch_ROS2',
                'msg_MID360_launch.py'
            ])
        ])
    )

    # 2. 包含 PGO launch 文件 (包含 FASTLIO2 + PGO + RViz)
    pgo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('pgo'),
                'launch',
                'pgo_launch.py'
            ])
        ])
    )

    # 3. 启动串口控制节点
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

    # 3.1 启动串口读取节点
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

    # 已注释掉该部分，暂时不启用
    # # 3.2 启动 pointcloud_to_laserscan 节点（将3D点云转为2D激光扫描）
    # pkg_share = get_package_share_directory('pointcloud_to_laserscan')
    # pointcloud_params_file = os.path.join(
    #     pkg_share, 'config', 'pointcloud_to_laserscan_params.yaml'
    # )
    
    # pointcloud_to_laserscan_node = launch_ros.actions.Node(
    #     package='pointcloud_to_laserscan',
    #     executable='pointcloud_to_laserscan_node',
    #     name='pointcloud_to_laserscan',
    #     output='screen',
    #     parameters=[pointcloud_params_file],
    #     remappings=[
    #         ('cloud_in', '/fastlio2/body_cloud'),   # 输入：FASTLIO2 的 Body 坐标系点云
    #         ('scan', '/scan')                       # 输出：2D 激光扫描
    #     ]
    # )

    # 暂时注释掉这个 Nav2 的启动，改为手动启动，方便进行 debug
    # 4. 导航模式：Nav2 导航系统 launch 文件 (延时 5 秒启动)
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
            # 文件名以对应加上 pgo 后缀
            'params_file': '' + os.path.join(get_package_share_directory('bringup'), 'config', 'nav2_explore.yaml') + ''
        }.items()
    )

    # 5. 创建延时动作 (5 秒后启动 Nav2)
    delayed_nav2 = TimerAction(
        period=5.0,  # 延时 5 秒
        actions=[nav2_launch]
    )
    
    return LaunchDescription([
        # 同时启动传感器层和定位层
        livox_launch,
        pgo_launch,
        serial_node,
        serial_reader_node,
        # 已注释，暂时不启用
        # pointcloud_to_laserscan_node,  # 点云转激光扫描
        delayed_nav2
    ])
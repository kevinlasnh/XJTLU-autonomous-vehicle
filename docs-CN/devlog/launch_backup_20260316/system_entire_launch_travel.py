
# 该分支已停止开发

import os
import launch
import launch_ros.actions
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    """
    系统完整启动 launch 文件 (支持建图/导航模式切换)
    
    启动模式：
    - mapping_mode=true:  建图模式 (SLAM Toolbox + Map Saver)
    - mapping_mode=false: 导航模式 (Nav2 导航系统，默认)
    
    启动顺序：
    1. 同时启动：Livox MID360激光雷达、PGO(FASTLIO2+SLAM)+RViz、串口控制节点
    2. 延时 5 秒
    3. 根据 mapping_mode 启动：
       - 建图模式：SLAM Toolbox + Map Saver Server
       - 导航模式：Nav2 导航系统
    
    使用方法：
    # 建图模式
    ros2 launch system_entire_launch system_entire_launch_pgo.py mapping_mode:=true
    
    # 导航模式 (默认)
    ros2 launch system_entire_launch system_entire_launch_pgo.py
    或
    ros2 launch system_entire_launch system_entire_launch_pgo.py mapping_mode:=false
    """
    
    # 声明 Launch 参数
    mapping_mode_arg = DeclareLaunchArgument(
        'mapping_mode',
        default_value='false',
        description='是否启用建图模式 (true=建图, false=导航)'
    )
    
    # 获取 Launch 参数
    mapping_mode = LaunchConfiguration('mapping_mode')

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

    # 3.2 启动 pointcloud_to_laserscan 节点（将3D点云转为2D激光扫描）
    pkg_share = get_package_share_directory('pointcloud_to_laserscan')
    pointcloud_params_file = os.path.join(pkg_share, 'config', 'pointcloud_to_laserscan_params.yaml')
    
    pointcloud_to_laserscan_node = launch_ros.actions.Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        output='screen',
        parameters=[
            pointcloud_params_file,
            {
                # 显式设置 QoS 参数以兼容 SLAM Toolbox/Nav2
                'qos_overrides./scan.publisher.reliability': 'best_effort',
                'qos_overrides./scan.publisher.durability': 'volatile',
                'qos_overrides./scan.publisher.history': 'keep_last',
                'qos_overrides./scan.publisher.depth': 10,
            }
        ],
        remappings=[
            ('cloud_in', '/fastlio2/body_cloud'),   # 输入：FASTLIO2 的 Body 坐标系点云
            ('scan', '/scan')                       # 输出：2D 激光扫描
        ]
    )

    # 4. 建图模式：SLAM Toolbox + Map Saver Server
    # 获取 SLAM Toolbox 配置文件路径 (使用自定义配置包)
    slam_toolbox_dir = get_package_share_directory('slam_toolbox')
    slam_params_file = os.path.join(slam_toolbox_dir, 'config', 'mapper_params_online_async.yaml')
    
    # SLAM Toolbox 节点
    slam_toolbox_node = launch_ros.actions.Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[slam_params_file],
        condition=IfCondition(mapping_mode)
    )
    
    # Map Saver Server 节点 (建图模式下启动)
    map_saver_server = launch_ros.actions.Node(
        package='nav2_map_server',
        executable='map_saver_server',
        name='map_saver_server',
        output='screen',
        parameters=[{'save_map_timeout': 5000.0}],
        condition=IfCondition(mapping_mode)
    )
    
    # Lifecycle Manager (建图模式下管理 map_saver_server)
    lifecycle_manager_mapping = launch_ros.actions.Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_mapping',
        output='screen',
        parameters=[{
            'autostart': True,
            'node_names': ['map_saver_server']
        }],
        condition=IfCondition(mapping_mode)
    )
    
    # 延时启动建图组件 (5 秒后)
    delayed_slam = TimerAction(
        period=5.0,
        actions=[
            slam_toolbox_node,
            map_saver_server,
            lifecycle_manager_mapping
        ]
    )

    # 5. 导航模式：Nav2 导航系统 launch 文件 (延时 5 秒启动)
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
            'params_file': '/home/jetson/2025_FYP/car_ws/src/navigation2/nav2_bringup/params/nav2_manual_adjust_travel.yaml'
        }.items(),
        condition=UnlessCondition(mapping_mode)
    )

    # 6. 创建延时动作 (5 秒后启动 Nav2)
    delayed_nav2 = TimerAction(
        period=5.0,  # 延时 5 秒
        actions=[nav2_launch]
    )

    return LaunchDescription([
        # 声明参数
        mapping_mode_arg,
        
        # 同时启动传感器层和定位层
        livox_launch,
        pgo_launch,
        serial_node,
        serial_reader_node,
        pointcloud_to_laserscan_node,  # 点云转激光扫描

        # 延时 5 秒后根据模式启动对应系统
        delayed_slam,    # 建图模式 (条件启动)
        delayed_nav2     # 导航模式 (条件启动)
    ])
#!/usr/bin/env python3
"""
测试 pointcloud_to_grid 与 FASTLIO2 的对接
将 FASTLIO2 的点云数据转换为 2D 栅格地图
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    
    # 声明参数
    cloud_topic_arg = DeclareLaunchArgument(
        'cloud_topic',
        default_value='/fastlio2/world_cloud',
        description='输入点云话题 (可选: /fastlio2/world_cloud 或 /fastlio2/body_cloud)'
    )
    
    resolution_arg = DeclareLaunchArgument(
        'resolution',
        default_value='0.2',
        description='栅格分辨率 (米/像素)'
    )
    
    # 获取参数
    cloud_topic = LaunchConfiguration('cloud_topic')
    resolution = LaunchConfiguration('resolution')
    
    # pointcloud_to_grid 节点
    pointcloud_to_grid_node = Node(
        package='pointcloud_to_grid',
        executable='pointcloud_to_grid_node',
        name='pointcloud_to_grid',
        output='screen',
        parameters=[
            # 输入点云话题
            {'cloud_in_topic': cloud_topic},
            
            # 地图中心位置 (相对于点云坐标系)
            {'position_x': 0.0},    # 地图中心 X 坐标
            {'position_y': 0.0},    # 地图中心 Y 坐标
            
            # 栅格参数
            {'cell_size': resolution},  # 栅格分辨率
            {'length_x': 50.0},     # 地图 X 方向长度 (米)
            {'length_y': 50.0},     # 地图 Y 方向长度 (米)
            
            # 高度过滤参数 (过滤地面和过高的点)
            {'intensity_factor': 1.0},   # 强度权重
            {'height_factor': 1.0},      # 高度权重
            
            # 调试信息
            {'verbose1': True},     # 打印基本信息
            {'verbose2': False},    # 打印详细信息
            
            # OccupancyGrid 输出话题
            {'mapi_topic_name': 'intensity_grid'},
            {'maph_topic_name': 'height_grid'},
            
            # GridMap 输出话题
            {'mapi_gridmap_topic_name': 'intensity_gridmap'},
            {'maph_gridmap_topic_name': 'height_gridmap'},
        ]
    )
    
    return LaunchDescription([
        cloud_topic_arg,
        resolution_arg,
        pointcloud_to_grid_node,
    ])

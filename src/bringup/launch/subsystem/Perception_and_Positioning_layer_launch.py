# 导入操作系统模块，用于文件路径操作
import os
import sys
import launch
# 从 ament_index_python 包中导入获取包共享目录的函数
from ament_index_python.packages import get_package_share_directory
# 从 launch 模块导入 LaunchDescription 类，用于定义启动描述
from launch import LaunchDescription, LaunchContext
# 从 launch.actions 模块导入 TimerAction 和 SetEnvironmentVariable 类，用于定时启动和设置环境变量
from launch.actions import TimerAction, SetEnvironmentVariable, ExecuteProcess
# 从 launch_ros.actions 模块导入 Node 类，用于定义 ROS2 节点
from launch_ros.actions import Node
# 从 launch.substitutions 模块导入 PathJoinSubstitution 类，用于路径拼接
from launch.substitutions import PathJoinSubstitution
# 从 launch_ros.substitutions 模块导入 FindPackageShare 类，用于查找包共享目录
from launch_ros.substitutions import FindPackageShare

# 文件最新改动时间：2025.11.02
# 文件改动人：AI Assistant (修复：移除 Localizer + 添加 map→lidar 静态 TF)

# 节点启动：
# 1. lio_node (FAST-LIO2) - 发布 lidar→body TF
# 2. body_to_base_link_alias - 静态 TF：body→base_link（Nav2 需要）
# 3. lidar_to_odom_alias - 静态 TF：lidar→odom（Nav2 需要）
# 4. map_to_lidar_identity - 静态 TF：map→lidar（没有全局地图时使用）

# TF 树结构（无全局地图模式）：
# map (静态，等于 lidar)
#  └─> lidar (FAST-LIO2 的世界帧) ≈ odom (静态别名)
#       └─> body (FAST-LIO2 发布) ≈ base_link (静态别名)

# 车辆运行效果（文件运行后）：
# 这个 Perception_and_Positioning_layer_launch.py 文件运行后，
# 会启动 FAST-LIO2 激光雷达惯性里程计节点，用于实时 SLAM。
# 添加 TF 别名和静态 map 帧，使 Nav2 和 go_forward_node 能够在没有全局地图的情况下工作。
# 导航将基于里程计进行（dead reckoning）。

# 定义生成launch描述的函数
def generate_launch_description():
    # 打印启动信息（修复：改为正确的文件名）
    print("\n----------------- Launch 文件启动：Perception_and_Positioning_layer_launch.py -----------------")

    # 使用 PathJoinSubstitution 和 FindPackageShare 构建配置文件路径
    # FAST-LIO2 配置文件路径
    lio_config_path = PathJoinSubstitution(
        [FindPackageShare("fastlio2"), "config", "lio.yaml"]
    )
    
    # 静态 TF 发布器脚本路径
    tf_publisher_script = os.path.join(
        get_package_share_directory('ROS2_launch_file'),
        '..',  # 返回上级
        '..',  # 再返回上级
        'src',
        'ROS2_launch_file',
        'scripts',
        'static_tf_publisher.py'
    )

    # 返回启动描述，包含节点定义
    return LaunchDescription(
        [
            # 设置环境变量，配置日志输出格式，让每条日志之间空一行
            SetEnvironmentVariable('RCUTILS_CONSOLE_OUTPUT_FORMAT', '\n[{severity}] [{time}] [{name}]: {message}'),

            # 定时启动 FAST-LIO2
            TimerAction(
                # 指定延时周期为2.0秒
                period=2.0,
                # 指定动作列表，包含Node
                actions=[
                    # 创建 fastlio2 包的 lio_node 可执行文件的节点
                    # 设置命名空间为 fastlio2，节点名称为 lio_node，输出到屏幕
                    # 参数包含配置文件路径
                    Node(
                        package="fastlio2",
                        namespace="fastlio2",
                        executable="lio_node",
                        name="lio_node",
                        output="screen",
                        parameters=[{
                            "config_path": lio_config_path.perform(LaunchContext())
                        }]
                    )
                ]
            ),
            
            # 启动 Python 静态 TF 发布器（替代 static_transform_publisher）
            # 发布完整的 TF 树：map → lidar → body + 别名 (body≈base_link, lidar≈odom)
            TimerAction(
                period=3.0,
                actions=[
                    ExecuteProcess(
                        cmd=['python3', tf_publisher_script],
                        output='screen',
                        name='static_tf_publisher'
                    )
                ]
            ),
        ]
    )

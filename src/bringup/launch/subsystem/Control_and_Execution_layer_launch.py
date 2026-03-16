# 导入操作系统模块，用于文件路径操作
import os
# 从 ament_index_python 包中导入获取包共享目录的函数
from ament_index_python.packages import get_package_share_directory
# 从 launch 模块导入 LaunchDescription 类，用于定义启动描述
from launch import LaunchDescription
# 从 launch.actions 模块导入 TimerAction 和 SetEnvironmentVariable 类，用于定时启动和设置环境变量
from launch.actions import TimerAction, SetEnvironmentVariable
# 从 launch_ros.actions 模块导入 Node 类，用于定义 ROS2 节点
from launch_ros.actions import Node

# 文件最新改动时间：2025.10.13
# 文件改动人：鹏

# 节点启动：
# 1. traj_pid_node

# 车辆运行效果（文件运行后）：
# 这个 Control_and_Execution_layer_launch.py 文件运行后，
# 会启动轨迹PID控制节点，用于接收规划轨迹并控制车辆运动

# 定义生成launch描述的函数
def generate_launch_description():
    # 打印启动信息
    print("\n----------------- Launch 文件启动：Control_and_Execution_layer_launch.py -----------------")

    # 返回启动描述，包含节点定义
    return LaunchDescription(
        [
            # 设置环境变量，配置日志输出格式，让每条日志之间空一行
            SetEnvironmentVariable('RCUTILS_CONSOLE_OUTPUT_FORMAT', '\n[{severity}] [{time}] [{name}]: {message}'),

            # 定义定时动作，延时启动traj_pid_node，使用TimerAction
            TimerAction(
                # 指定延时周期为2.0秒
                period=2.0,
                # 指定动作列表，包含Node
                actions=[
                    # 创建 traj_pid 包的 traj_pid_node 可执行文件的节点
                    # 节点名称为 traj_pid_node
                    Node(
                        package='traj_pid',
                        executable='traj_pid_node',
                        name='traj_pid_node',
                        output='screen'
                    )
                ]
            )
        ]
    )

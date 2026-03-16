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
# 1. planner
# 2. test_sdfmap

# 车辆运行效果（文件运行后）：
# 这个 Local_planning_and_Decision_making_layer_launch.py 文件运行后，
# 会启动规划器管理节点和测试SDF地图节点，用于局部路径规划和决策

# 定义生成launch描述的函数
def generate_launch_description():
    # 打印启动信息
    print("\n----------------- Launch 文件启动：Local_planning_and_Decision_making_layer_launch.py -----------------")

    # 使用 os.path.join 和 get_package_share_directory 构建配置文件路径
    # 路径指向 planner 包的 config 目录下的 sdf_map_param.yaml 文件
    config_file = os.path.join(
        get_package_share_directory('planner'),
        'config',
        'sdf_map_param.yaml'
    )

    # 返回启动描述，包含节点定义
    return LaunchDescription(
        [
            # 设置环境变量，配置日志输出格式，让每条日志之间空一行
            SetEnvironmentVariable('RCUTILS_CONSOLE_OUTPUT_FORMAT', '\n[{severity}] [{time}] [{name}]: {message}'),

            # 定义定时动作，延时启动planner和test_sdfmap节点，使用TimerAction
            TimerAction(
                # 指定延时周期为2.0秒
                period=2.0,
                # 指定动作列表，包含多个Node
                actions=[
                    # 创建 planner 包的 planner_manager 可执行文件的节点
                    # 节点名称为 planner
                    Node(
                        package='planner',
                        executable='planner_manager',
                        name='planner',
                        output='screen'
                    ),
                    # 创建 planner 包的 test_sdfmap 可执行文件的节点
                    # 节点名称为 test_sdfmap
                    Node(
                        package='planner',
                        executable='test_sdfmap',
                        name='test_sdfmap',
                        output='screen'
                    )
                ]
            )
        ]
    )

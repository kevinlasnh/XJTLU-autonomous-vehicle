import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import launch

################### user configure parameters for ros2 start ###################
xfer_format   = 1    # 0-Pointcloud2(PointXYZRTL), 1-customized pointcloud format
multi_topic   = 0    # 0-All LiDARs share the same topic, 1-One LiDAR one topic
data_src      = 0    # 0-lidar, others-Invalid data src

# ========== Livox 激光雷达发布频率配置 ==========
# publish_freq: 激光雷达点云消息的发布频率（单位：Hz）
# 
# 配置说明：
#   - 当前配置：100.0 Hz（每 10ms 发布一次点云数据）
#   - 原始配置：10.0 Hz（激光雷达硬件扫描频率）
#
# 频率选项：
#   - 10.0 Hz：激光雷达原始扫描频率，最低延迟，数据量小
#   - 20.0 Hz：适中频率，平衡性能和实时性
#   - 50.0 Hz：高频发布，提高 SLAM 实时性
#   - 100.0 Hz：超高频发布（当前配置），最大化实时性能
#
# 高频率发布的优势：
#   1. 降低 SLAM 算法的数据延迟，提高定位精度
#   2. 与 FASTLIO2 的 50Hz 处理频率更好匹配
#   3. 使点云数据流更加平滑连续
#   4. 提高导航系统的响应速度
#
# 注意事项：
#   - 高频率会增加 CPU 和网络带宽占用
#   - Jetson 平台建议监控 CPU 使用率
#   - 如果系统负载过高，可降低至 50.0 Hz 或 20.0 Hz
#   - 实际点云数据仍受激光雷达硬件扫描速度限制（10Hz）
#   - 高频发布主要是重新发布已有数据帧，减少缓冲延迟
#
# 文件最新改动时间：2025.11.12
# 文件改动人：助手
publish_freq  = 100.0 # 激光雷达点云发布频率（Hz）：10.0, 20.0, 50.0, 100.0 等
output_type   = 0
frame_id      = 'livox_frame'
lvx_file_path = '/home/livox/livox_test.lvx'
cmdline_bd_code = 'livox0000000001'

cur_path = os.path.split(os.path.realpath(__file__))[0] + '/'
cur_config_path = cur_path + '../config'
rviz_config_path = os.path.join(cur_config_path, 'livox_lidar.rviz')
user_config_path = os.path.join(cur_config_path, 'HAP_config.json')
################### user configure parameters for ros2 end #####################

livox_ros2_params = [
    {"xfer_format": xfer_format},
    {"multi_topic": multi_topic},
    {"data_src": data_src},
    {"publish_freq": publish_freq},
    {"output_data_type": output_type},
    {"frame_id": frame_id},
    {"lvx_file_path": lvx_file_path},
    {"user_config_path": user_config_path},
    {"cmdline_input_bd_code": cmdline_bd_code}
]


def generate_launch_description():
    livox_driver = Node(
        package='livox_ros_driver2',
        executable='livox_ros_driver2_node',
        name='livox_lidar_publisher',
        output='screen',
        parameters=livox_ros2_params
        )

    return LaunchDescription([
        livox_driver,
        # launch.actions.RegisterEventHandler(
        #     event_handler=launch.event_handlers.OnProcessExit(
        #         target_action=livox_rviz,
        #         on_exit=[
        #             launch.actions.EmitEvent(event=launch.events.Shutdown()),
        #         ]
        #     )
        # )
    ])

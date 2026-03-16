import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import launch

################### user configure parameters for ros2 start ###################
# 已改动消息类型为 PointCloud2 格式 <xfer_format = 0>
# ！！！！！！这个参数很关键！！！！！！
# 其直接决定了 fastlio2 节点能不能接收到 livox_ros_driver2 节点发布的消息
# 目前暂时用原始配置：当参数为 1 的时候，fastlio2 节点可以接收到消息，但是点云的原始数据不能被记录到 log 文件中
# 当参数为 0 的时候，fastlio2 节点接收不到消息，但是点云的原始数据可以被记录到 log 文件中
# 如果要想让 fastlio2 节点接收到消息，并且点云的原始数据也能被记录到 log 文件中，需要对 lddc 中的代码逻辑进行修改，目前暂时没时间改，等车运行起来之后再改
xfer_format   = 1    # 0-Pointcloud2(PointXYZRTL), 1-customized pointcloud format
multi_topic   = 0    # 0-All LiDARs share the same topic, 1-One LiDAR one topic
data_src      = 0    # 0-lidar, others-Invalid data src

# ========== Livox 激光雷达发布频率配置 ==========
# publish_freq: 激光雷达点云消息的发布频率（单位：Hz）
# 
# 关键理解：
#   ⚠️  Livox 雷达硬件扫描频率是固定的 10Hz
#   ⚠️  提高 publish_freq 只是重复发布相同帧，不会增加新点云数据
#   ⚠️  过高频率会浪费 CPU 和网络带宽，不会提高 SLAM 精度
#
# 配置说明：
#   - 当前配置：10.0 Hz（推荐，与硬件同步）
#   - 硬件扫描：10.0 Hz（物理限制，无法改变）
#
# 频率选项分析：
#   - 10.0 Hz ✅ 推荐：
#       • 与雷达硬件扫描频率匹配
#       • CPU 和带宽占用最低
#       • 每帧都是全新的点云数据
#       • 适合 Jetson 嵌入式平台
#
#   - 20.0 Hz ⚠️  可选（如果需要降低延迟）：
#       • 每个真实点云帧会被发布 2 次
#       • 降低 50ms 的缓冲延迟
#       • CPU 和带宽占用增加 2 倍
#       • 对 SLAM 精度提升有限
#
#   - 50.0-100.0 Hz ❌ 不推荐：
#       • 重复发布相同数据 5-10 次（浪费资源）
#       • FASTLIO2 的 50Hz 处理已经足够快
#       • Jetson 平台 CPU 负载过高
#       • 性价比极低
#
# 设计原理：
#   1. FASTLIO2 以 50Hz 处理数据（20ms 定时器）
#   2. 即使雷达以 10Hz 发布，FASTLIO2 也能及时处理（50Hz > 10Hz）
#   3. 10Hz 点云 + 100-200Hz IMU 融合，已经提供足够的定位精度
#   4. 提高雷达发布频率不会改善 SLAM 性能，只会增加系统负载
#
# 性能对比：
#   10Hz:  100% CPU,  100% 带宽, 100% 数据新鲜度 ← 最佳性价比
#   20Hz:  200% CPU,  200% 带宽, 100% 数据新鲜度
#   50Hz:  500% CPU,  500% 带宽, 100% 数据新鲜度
#   100Hz: 1000% CPU, 1000% 带宽, 100% 数据新鲜度 ← 资源浪费
#
# 文件最新改动时间：2025.11.12
# 文件改动人：助手
publish_freq  = 10.0 # 激光雷达点云发布频率（Hz），推荐保持 10.0 与硬件同步
output_type   = 0
frame_id      = 'livox_frame'
lvx_file_path = '/home/livox/livox_test.lvx'
cmdline_bd_code = 'livox0000000001'

cur_path = os.path.split(os.path.realpath(__file__))[0] + '/'
cur_config_path = cur_path + '../config'
user_config_path = os.path.join(cur_config_path, 'MID360_config.json')
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

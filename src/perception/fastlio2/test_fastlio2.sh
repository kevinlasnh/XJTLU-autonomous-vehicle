#!/bin/bash
# FASTLIO2 节点测试脚本
# 测试 FASTLIO2 SLAM 节点的功能

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "  FASTLIO2 节点测试脚本"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

# 设置工作空间路径
WORKSPACE="/home/jetson/2025_FYP/car_ws"

# 检查工作空间是否存在
if [ ! -d "$WORKSPACE" ]; then
    echo "❌ 错误: 找不到工作空间: $WORKSPACE"
    exit 1
fi

echo "✓ 工作空间: $WORKSPACE"

# 切换到工作空间
cd "$WORKSPACE" || exit 1

echo ""
echo "🔧 步骤1: 编译 FASTLIO2 包..."
colcon build --packages-select fastlio2 --allow-overriding fastlio2
if [ $? -ne 0 ]; then
    echo "❌ 编译失败"
    exit 1
fi
echo "✓ 编译成功"

echo ""
echo "🔧 步骤2: 配置ROS2环境..."
source ./install/setup.bash
echo "✓ 环境配置完成"

echo ""
echo "📋 FASTLIO2 节点依赖说明:"
echo "  FASTLIO2 需要以下传感器数据才能正常工作:"
echo "  1. IMU 数据话题: /livox/imu"
echo "  2. 激光雷达数据话题: /livox/lidar"
echo ""
echo "  需要先启动 livox_ros_driver2 节点提供传感器数据"
echo ""

read -p "是否已启动 livox_ros_driver2 节点? (y/n), 或使用模拟数据 (s): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo ""
    echo "🚀 使用模拟传感器数据进行测试..."
    echo "启动模拟数据发布器..."
    python3 "$WORKSPACE/src/Perception_and_Positioning_layer/FASTLIO2_ROS2/fastlio2/test_data_publisher.py" &
    PUBLISHER_PID=$!
    echo "✓ 模拟数据发布器已启动 (PID: $PUBLISHER_PID)"
    sleep 2
elif [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "请先启动 livox_ros_driver2 节点:"
    echo "  ros2 launch livox_ros_driver2 [your_launch_file].launch.py"
    echo ""
    echo "或者使用以下命令启动 (根据你的配置):"
    echo "  ros2 run livox_ros_driver2 livox_ros_driver2_node"
    echo ""
    exit 1
fi

echo ""
echo "🚀 步骤3: 启动 FASTLIO2 节点..."
echo "节点将订阅以下话题:"
echo "  - /livox/imu (IMU数据)"
echo "  - /livox/lidar (激光雷达数据)"
echo ""
echo "输出话题:"
echo "  - /odometry/imu (IMU里程计)"
echo "  - /odometry/imu_incremental (增量里程计)"
echo "  - /path/imu (轨迹)"
echo "  - /cloud_registered (配准点云)"
echo "  - /cloud_registered_body (机体坐标系点云)"
echo ""

# 获取配置文件路径
CONFIG_PATH="$WORKSPACE/src/Perception_and_Positioning_layer/FASTLIO2_ROS2/fastlio2/config/lio.yaml"
if [ ! -f "$CONFIG_PATH" ]; then
    echo "❌ 错误: 找不到配置文件: $CONFIG_PATH"
    exit 1
fi

echo "配置文件: $CONFIG_PATH"
echo ""

# 启动 FASTLIO2 节点
echo "启动 FASTLIO2 节点..."
ros2 run fastlio2 lio_node --ros-args --params-file "$CONFIG_PATH"

echo ""
echo "🔚 清理测试进程..."
# 清理模拟数据发布器
if [ ! -z "$PUBLISHER_PID" ] && kill -0 $PUBLISHER_PID 2>/dev/null; then
    echo "停止模拟数据发布器 (PID: $PUBLISHER_PID)..."
    kill $PUBLISHER_PID
    wait $PUBLISHER_PID 2>/dev/null
    echo "✓ 模拟数据发布器已停止"
fi

# 清理所有 ROS2 进程
echo "清理所有 ROS2 进程..."
pkill -f ros2
echo "✓ ROS2 进程已清理"

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
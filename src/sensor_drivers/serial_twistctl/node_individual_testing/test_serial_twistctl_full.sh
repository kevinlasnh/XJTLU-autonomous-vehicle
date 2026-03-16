#!/bin/bash
# serial_twistctl 节点完整测试脚本
# 包含编译、启动节点、运行测试的全流程

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "  serial_twistctl 节点完整测试脚本"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

# 设置工作空间路径
WORKSPACE="/home/jetson/2025_FYP/car_ws"
TEST_SCRIPT="$WORKSPACE/src/Sensor_Driver_layer/serial_twistctl/node_individual_testing/test_serial_twistctl.py"

# 检查工作空间是否存在
if [ ! -d "$WORKSPACE" ]; then
    echo "❌ 错误: 找不到工作空间: $WORKSPACE"
    exit 1
fi

echo "✓ 工作空间: $WORKSPACE"

# 切换到工作空间
cd "$WORKSPACE" || exit 1

echo ""
echo "🔧 步骤1: 编译 serial_twistctl 包..."
colcon build --packages-select serial_twistctl --allow-overriding serial_twistctl
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
echo "🚀 步骤3: 启动 serial_twistctl 节点..."
# 在后台启动节点
ros2 run serial_twistctl serial_twistctl_node &
NODE_PID=$!
echo "✓ 节点已启动 (PID: $NODE_PID)"

# 等待节点完全启动
sleep 3

echo ""
echo "🧪 步骤4: 运行测试脚本..."
if [ ! -f "$TEST_SCRIPT" ]; then
    echo "❌ 错误: 找不到测试脚本: $TEST_SCRIPT"
    kill $NODE_PID 2>/dev/null
    exit 1
fi

# 运行测试脚本
python3 "$TEST_SCRIPT"
TEST_EXIT_CODE=$?

echo ""
echo "🔚 步骤5: 清理..."
# 停止节点
if kill -0 $NODE_PID 2>/dev/null; then
    echo "停止节点进程 (PID: $NODE_PID)..."
    kill $NODE_PID
    wait $NODE_PID 2>/dev/null
    echo "✓ 节点已停止"
else
    echo "⚠️ 节点进程已退出"
fi

# 清理所有 ROS2 相关进程
echo "清理所有 ROS2 进程..."
pkill -f ros2
echo "✓ ROS2 进程已清理"

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ 测试完成 - 所有步骤成功"
else
    echo "❌ 测试完成 - 测试脚本返回错误码: $TEST_EXIT_CODE"
fi

echo "═══════════════════════════════════════════════════════════════════════════════"
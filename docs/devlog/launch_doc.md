# Launch 备忘

## 开发板块

### 最高优先级（需要立马解决的问题，对系统运行有直接影响）

### 中等优先级（短时间内需要解决，对系统运行无直接影响）

### 低优先级（解决了更优，不解决亦可）

## 杂项
1. 

## 控制台命令

### 杂项
1. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 launch ros2_launch_file system_entire_launch_pgo.py
2. cd /home/jetson/2025_FYP/car_ws && colcon build --packages-select ros2_launch_file --symlink-install

# Launch 开发日志

## 2025.11.11
1. 无

## 2025.11.22
1. 确认整个系统的 launch 文件中的 yaml 文件参数已经更新
2. 在 launch 文件中添加了 serial reader 的节点启动，为了给 velocity_smoother 节点提供底层 C 板的里程计数据
3. 添加了新的 Nav2 导航框架的 launch 文件

## 2025.12.01
1. explore launch 文件中的点云转扫描节点已注释掉，暂时不启用
2. explore launch 文件中的 Nav2 部分暂时注释掉改成手动启动，这样更方便进行 debug
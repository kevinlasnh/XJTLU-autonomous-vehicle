# 驱动层备忘

## 开发板块

### 最高优先级（需要立马解决的问题，对系统运行有直接影响）

### 中等优先级（短时间内需要解决，对系统运行无直接影响）

### 低优先级（解决了更优，不解决亦可）

## IMU 的运行原理
1. 

## 杂项
1. 对于 LiDAR 日志写入功能的启用，launch 文件里面的参数决定了发布消息的时候调用哪个函数，需要在 PublishCustomPointData() 函数中添加类似PublishPointcloud2Data() 的日志记录逻辑，现已添加，能够成功的在既输出数据到 fastlio2 节点中的同时也能记录 log 到文件中

## 控制台命令

### 杂项
1. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 launch livox_ros_driver2 msg_MID360_launch.py
2. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 run wit_ros2_imu wit_ros2_imu
3. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 run serial_reader serial_reader_node
4. cd /home/jetson/2025_FYP/car_ws/src/Sensor_Driver_layer/serial_twistctl/node_individual_testing/ && ./test_serial_twistctl_full.sh
5. cd /home/jetson/2025_FYP/car_ws && ros2 run fastlio2 lio_node --ros-args -p config_path:=/home/jetson/2025_FYP/car_ws/src/Perception_and_Positioning_layer/FASTLIO2_ROS2/fastlio2/config/lio.yaml
6. cd /home/jetson/2025_FYP/car_ws && ros2 run serial_twistctl serial_twistctl_node
7. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 launch nmea_navsat_driver nmea_serial_driver.launch.py
8. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 launch wheeltec_gps_path gps_path.launch.py
9. cd /home/jetson/2025_FYP/car_ws && timeout 100 ros2 launch gnss_calibration gnss_calibration_launch.py

### 编译
1. cd ~/2025_FYP/car_ws && colcon build --packages-select serial_reader && source install/setup.bash

# 驱动层开发日志

## 2025.11.10
1. LiDAR 节点在输出点云数据时不能记录数据到 log 中的问题已经通过改动激光雷达驱动文件中的具体函数来进行解决

## 2025.11.11
1. LiDAR 消息时间戳已改动至由系统时间决定
2. 已确认维特 IMU 的消息发布时间戳是由系统时间决定的，更改 log 中的时间戳为纳秒格式
3. 已确认 serial reader 读取节点的消息发布时间戳是由系统时间决定的，时间戳格式更改为纳秒格式
4. 更改了 nmea 的 log 时间戳为 ROS 标准时间戳，在 log 中加入了 ROS 系统标准时间戳
5. 更改了 wheeltec 的 log 时间戳，添加了 ROS 系统标准时间戳
6. 在串口发送节点 serial_twistctl 节点中添加了往日志中添加时间戳写入功能
7. 对每个现在能产生 log 的传感器源代码文件都加上了是否启用 log 功能的参数检测判断，这样是为了有时候关掉 log 来减轻系统运行压力
8. 创建了 log 管理系统，统一使用一个 yaml 文件来对每个节点的 log 功能进行控制

## 2025.11.13
1. 目前室外GPS数据正常，不确定是否非常准确，可以检测到小范围移动，精确到0.1米，大概有27颗卫星在线，附带时间戳但还尚未检查
2. 摄像头目前没法使用，因为目前 jetson 板子的 USB 为 2.0 接口，需要 3.0 接口才能使用
3. 尝试将下位机的里程计数据发送给 Nav2 来做闭环的速度控制，然后发现这个小车直接发疯了

## 2025.11.24
1. 尝试将下位机的里程计数据发回给 Nav2 来做闭环的速度控制，然后发现这个小车直接发疯了，目前不知道这个传输回来的数据是哪里出了问题
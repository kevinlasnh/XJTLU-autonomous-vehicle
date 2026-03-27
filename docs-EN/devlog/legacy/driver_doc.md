# Driver Layer Memo

## Development Modules

### Highest Priority (Issues requiring immediate resolution, directly impacting system operation)

### Medium Priority (Issues to resolve in the short term, no direct impact on system operation)

### Low Priority (Better if resolved, acceptable if not)

## IMU Operating Principles
1.

## Miscellaneous
1. For enabling the LiDAR log writing feature, the parameter in the launch file determines which function is called when publishing messages. Logging logic similar to `PublishPointcloud2Data()` needed to be added to the `PublishCustomPointData()` function. This has been implemented, successfully enabling data output to the FAST-LIO2 node while also writing logs to file.

## Console Commands

### Miscellaneous
1. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 launch livox_ros_driver2 msg_MID360_launch.py
2. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 run wit_ros2_imu wit_ros2_imu
3. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 run serial_reader serial_reader_node
4. cd /home/jetson/2025_FYP/car_ws/src/Sensor_Driver_layer/serial_twistctl/node_individual_testing/ && ./test_serial_twistctl_full.sh
5. cd /home/jetson/2025_FYP/car_ws && ros2 run fastlio2 lio_node --ros-args -p config_path:=/home/jetson/2025_FYP/car_ws/src/Perception_and_Positioning_layer/FASTLIO2_ROS2/fastlio2/config/lio.yaml
6. cd /home/jetson/2025_FYP/car_ws && ros2 run serial_twistctl serial_twistctl_node
7. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 launch nmea_navsat_driver nmea_serial_driver.launch.py
8. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 launch wheeltec_gps_path gps_path.launch.py
9. cd /home/jetson/2025_FYP/car_ws && timeout 100 ros2 launch gnss_calibration gnss_calibration_launch.py

### Build
1. cd ~/2025_FYP/car_ws && colcon build --packages-select serial_reader && source install/setup.bash

# Driver Layer Development Log

## 2025.11.10
1. Resolved the issue where the LiDAR node could not write data to log while outputting point cloud data, by modifying the specific function in the LiDAR driver file.

## 2025.11.11
1. Changed LiDAR message timestamps to use system time.
2. Confirmed that WIT IMU message publish timestamps are determined by system time; changed log timestamps to nanosecond format.
3. Confirmed that serial reader node message publish timestamps are determined by system time; changed timestamp format to nanoseconds.
4. Changed nmea log timestamps to ROS standard timestamps, added ROS system standard timestamps to logs.
5. Changed wheeltec log timestamps, added ROS system standard timestamps.
6. Added timestamp writing functionality to the serial output node `serial_twistctl`.
7. Added log enable/disable parameter detection to every sensor source code file currently capable of producing logs, so that log writing can be disabled to reduce system load when needed.
8. Created a log management system using a unified YAML file to control log functionality for each node.

## 2025.11.13
1. Outdoor GPS data is currently normal; accuracy uncertain but can detect small-range movement, accurate to 0.1 meters, approximately 27 satellites online, with timestamps attached but not yet verified.
2. Camera currently unusable because the Jetson board's USB ports are 2.0; USB 3.0 is required.
3. Attempted sending lower-level board odometry data to Nav2 for closed-loop speed control, and the vehicle went completely haywire.

## 2025.11.24
1. Attempted sending lower-level board odometry data back to Nav2 for closed-loop speed control, and the vehicle went completely haywire; currently unknown what is wrong with the transmitted data.

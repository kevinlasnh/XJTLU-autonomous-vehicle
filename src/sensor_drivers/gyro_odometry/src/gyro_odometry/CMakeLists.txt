cmake_minimum_required(VERSION 3.5)
project(gyro_odometry)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(serial REQUIRED)

add_executable(gyro_odometry src/gyro_odometry.cpp)
ament_target_dependencies(gyro_odometry rclcpp std_msgs geometry_msgs serial)


## Include headers
target_include_directories(${PROJECT_NAME} PRIVATE include)

install(TARGETS
  gyro_odometry
  DESTINATION lib/${PROJECT_NAME})

ament_package()

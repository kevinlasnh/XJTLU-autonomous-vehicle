// 包含iostream头文件，用于标准输入输出流操作，如cout和cin
#include <iostream>
// 包含chrono头文件，用于时间相关的操作，如时间点和持续时间
#include <chrono>
// 包含vector头文件，用于动态数组容器
#include <vector>
// 包含csignal头文件，用于信号处理函数
#include <csignal>
// 包含thread头文件，用于多线程操作
#include <thread>

// 包含livox_ros_driver2.h头文件，定义Livox ROS驱动器的主要接口
#include "include/livox_ros_driver2.h"
// 包含ros_headers.h头文件，包含ROS相关的头文件定义
#include "include/ros_headers.h"
// 包含driver_node.h头文件，定义驱动器节点的类
#include "driver_node.h"
// 包含lddc.h头文件，定义激光雷达数据分发控制类
#include "lddc.h"
// 包含lds_lidar.h头文件，定义激光雷达数据源类
#include "lds_lidar.h"

// 此文件为激光雷达驱动节点的实现文件，包含了节点的初始化、参数获取以及数据分发线程的创建等功能。

// 文件最新改动时间：2025.10.9
// 文件改动人：鹏

// 使用livox_ros命名空间，避免命名冲突
using namespace livox_ros;

// 如果定义了BUILDING_ROS1宏，则编译ROS1版本的代码
#ifdef BUILDING_ROS1
// 定义main函数，程序的入口点，接受命令行参数
int main(int argc, char **argv) {
  // 如果成功设置ROS控制台日志级别为Debug，则通知日志级别更改
  if (ros::console::set_logger_level(ROSCONSOLE_DEFAULT_NAME, ros::console::levels::Debug)) {
    // 通知ROS日志系统日志级别已更改
    ros::console::notifyLoggerLevelsChanged();
  }

  // 初始化ROS系统，设置节点名称为livox_lidar_publisher
  ros::init(argc, argv, "livox_lidar_publisher");

  // 创建livox_ros命名空间下的DriverNode对象
  livox_ros::DriverNode livox_node;

  // 记录驱动器版本信息到日志
  DRIVER_INFO(livox_node, "Livox Ros Driver2 Version: %s", LIVOX_ROS_DRIVER2_VERSION_STRING);

  // 初始化默认系统参数：数据传输格式为点云2消息
  int xfer_format = kPointCloud2Msg;
  // 初始化默认系统参数：多主题为0，表示所有LiDAR共享同一主题
  int multi_topic = 0;
  // 初始化默认系统参数：数据源为原始激光雷达
  int data_src = kSourceRawLidar;
  // 初始化默认系统参数：发布频率为10.0 Hz
  double publish_freq  = 10.0;
  // 初始化默认系统参数：输出类型为输出到ROS
  int output_type      = kOutputToRos;
  // 初始化默认系统参数：坐标系框架ID为livox_frame
  std::string frame_id = "livox_frame";
  // 初始化默认系统参数：激光雷达包启用为true
  bool lidar_bag = true;
  // 初始化默认系统参数：IMU包启用为false
  bool imu_bag   = false;

  // 从ROS参数服务器获取xfer_format参数值
  livox_node.GetNode().getParam("xfer_format", xfer_format);
  // 从ROS参数服务器获取multi_topic参数值
  livox_node.GetNode().getParam("multi_topic", multi_topic);
  // 从ROS参数服务器获取data_src参数值
  livox_node.GetNode().getParam("data_src", data_src);
  // 从ROS参数服务器获取publish_freq参数值
  livox_node.GetNode().getParam("publish_freq", publish_freq);
  // 从ROS参数服务器获取output_data_type参数值
  livox_node.GetNode().getParam("output_data_type", output_type);
  // 从ROS参数服务器获取frame_id参数值
  livox_node.GetNode().getParam("frame_id", frame_id);
  // 从ROS参数服务器获取enable_lidar_bag参数值
  livox_node.GetNode().getParam("enable_lidar_bag", lidar_bag);
  // 从ROS参数服务器获取enable_imu_bag参数值
  livox_node.GetNode().getParam("enable_imu_bag", imu_bag);

  // 记录数据源信息到日志
  RCLCPP_INFO(livox_node.GetNode().get_logger(), "data source:%u.", data_src);

  // 如果发布频率大于100.0，则设置为100.0
  if (publish_freq > 100.0) {
    // 设置发布频率为100.0
    publish_freq = 100.0;
  // 否则如果发布频率小于0.5，则设置为0.5
  } else if (publish_freq < 0.5) {
    // 设置发布频率为0.5
    publish_freq = 0.5;
  // 否则保持原值
  } else {
    // 保持发布频率不变
    publish_freq = publish_freq;
  }

  // 获取退出信号的未来对象
  livox_node.future_ = livox_node.exit_signal_.get_future();

  // 创建Lddc对象的唯一指针，用于激光雷达数据分发控制
  livox_node.lddc_ptr_ = std::make_unique<Lddc>(xfer_format, multi_topic, data_src, output_type,
                        publish_freq, frame_id, lidar_bag, imu_bag);
  // 设置ROS节点指针到Lddc对象
  livox_node.lddc_ptr_->SetRosNode(&livox_node);

  // 如果数据源是原始激光雷达
  if (data_src == kSourceRawLidar) {
    // 记录数据源是原始激光雷达的信息
    DRIVER_INFO(livox_node, "Data Source is raw lidar.");

    // 声明用户配置文件路径字符串
    std::string user_config_path;
    // 从ROS参数获取用户配置文件路径
    livox_node.getParam("user_config_path", user_config_path);
    // 记录配置文件路径信息
    DRIVER_INFO(livox_node, "Config file : %s", user_config_path.c_str());

    // 获取LdsLidar实例指针
    LdsLidar *read_lidar = LdsLidar::GetInstance(publish_freq);
    // 将LdsLidar注册到Lddc
    livox_node.lddc_ptr_->RegisterLds(static_cast<Lds *>(read_lidar));

    // 如果初始化LdsLidar成功
    if ((read_lidar->InitLdsLidar(user_config_path))) {
      // 记录初始化成功的日志
      DRIVER_INFO(livox_node, "Init lds lidar successfully!");
    // 否则
    } else {
      // 记录初始化失败的错误日志
      DRIVER_ERROR(livox_node, "Init lds lidar failed!");
    }
  // 否则
  } else {
    // 记录无效数据源的错误日志
    DRIVER_ERROR(livox_node, "Invalid data src (%d), please check the launch file", data_src);
  }

  // 创建点云数据轮询线程
  livox_node.pointclouddata_poll_thread_ = std::make_shared<std::thread>(&DriverNode::PointCloudDataPollThread, &livox_node);
  // 创建IMU数据轮询线程
  livox_node.imudata_poll_thread_ = std::make_shared<std::thread>(&DriverNode::ImuDataPollThread, &livox_node);
  // 当ROS运行时，休眠10毫秒
  while (ros::ok()) { usleep(10000); }

  // 返回0，表示程序正常退出
  return 0;
}

#elif defined BUILDING_ROS2
// 定义livox_ros命名空间
namespace livox_ros
{
// DriverNode类的构造函数，接受节点选项参数
DriverNode::DriverNode(const rclcpp::NodeOptions & node_options)
: Node("livox_driver_node", node_options)
{
  // 记录节点启动成功信息
  DRIVER_INFO(*this, "Node 文件运行成功");
  // 输出到控制台
  std::cout << "LIVOX ROS2 Driver Node Started Successfully" << std::endl;
  // 记录驱动器版本信息到日志
  DRIVER_INFO(*this, "Livox Ros Driver2 Version: %s", LIVOX_ROS_DRIVER2_VERSION_STRING);

  // 初始化默认系统参数：数据传输格式为点云2消息
  int xfer_format = kPointCloud2Msg;
  // 初始化默认系统参数：多主题为0
  int multi_topic = 0;
  // 初始化默认系统参数：数据源为原始激光雷达
  int data_src = kSourceRawLidar;
  // 初始化默认系统参数：发布频率为10.0 Hz
  double publish_freq = 10.0;
  // 初始化默认系统参数：输出类型为输出到ROS
  int output_type = kOutputToRos;
  // 声明坐标系框架ID字符串
  std::string frame_id;

  // 声明xfer_format参数，默认值为xfer_format
  this->declare_parameter("xfer_format", xfer_format);
  // 声明multi_topic参数，默认值为0
  this->declare_parameter("multi_topic", 0);
  // 声明data_src参数，默认值为data_src
  this->declare_parameter("data_src", data_src);
  // 声明publish_freq参数，默认值为10.0
  this->declare_parameter("publish_freq", 10.0);
  // 声明output_data_type参数，默认值为output_type
  this->declare_parameter("output_data_type", output_type);
  // 声明frame_id参数，默认值为"frame_default"
  this->declare_parameter("frame_id", "frame_default");
  // 声明user_config_path参数，默认值为"path_default"
  this->declare_parameter("user_config_path", "path_default");
  // 声明cmdline_input_bd_code参数，默认值为"000000000000001"
  this->declare_parameter("cmdline_input_bd_code", "000000000000001");
  // 声明lvx_file_path参数，默认值为"/home/livox/livox_test.lvx"
  this->declare_parameter("lvx_file_path", "/home/livox/livox_test.lvx");

  // 获取xfer_format参数值
  this->get_parameter("xfer_format", xfer_format);
  // 获取multi_topic参数值
  this->get_parameter("multi_topic", multi_topic);
  // 获取data_src参数值
  this->get_parameter("data_src", data_src);
  // 获取publish_freq参数值
  this->get_parameter("publish_freq", publish_freq);
  // 获取output_data_type参数值
  this->get_parameter("output_data_type", output_type);
  // 获取frame_id参数值
  this->get_parameter("frame_id", frame_id);

  // 如果发布频率大于100.0，则设置为100.0
  if (publish_freq > 100.0) {
    // 设置发布频率为100.0
    publish_freq = 100.0;
  // 否则如果发布频率小于0.5，则设置为0.5
  } else if (publish_freq < 0.5) {
    // 设置发布频率为0.5
    publish_freq = 0.5;
  // 否则保持原值
  } else {
    // 保持发布频率不变
    publish_freq = publish_freq;
  }

  // 获取退出信号的未来对象
  future_ = exit_signal_.get_future();

  // 创建Lddc对象的唯一指针，用于激光雷达数据分发控制
  lddc_ptr_ = std::make_unique<Lddc>(xfer_format, multi_topic, data_src, output_type, publish_freq, frame_id);
  // 设置ROS节点指针到Lddc对象
  lddc_ptr_->SetRosNode(this);

  // 如果数据源是原始激光雷达
  if (data_src == kSourceRawLidar) {
    // 记录数据源是原始激光雷达的信息
    DRIVER_INFO(*this, "Data Source is raw lidar.");

    // 声明用户配置文件路径字符串
    std::string user_config_path;
    // 获取用户配置文件路径参数
    this->get_parameter("user_config_path", user_config_path);
    // 记录配置文件路径信息
    DRIVER_INFO(*this, "Config file : %s", user_config_path.c_str());

    // 声明命令行广播代码字符串
    std::string cmdline_bd_code;
    // 获取命令行广播代码参数
    this->get_parameter("cmdline_input_bd_code", cmdline_bd_code);

    // 获取LdsLidar实例指针
    LdsLidar *read_lidar = LdsLidar::GetInstance(publish_freq);
    // 将LdsLidar注册到Lddc
    lddc_ptr_->RegisterLds(static_cast<Lds *>(read_lidar));

    // 如果初始化LdsLidar成功
    if ((read_lidar->InitLdsLidar(user_config_path))) {
      // 记录初始化成功的日志
      DRIVER_INFO(*this, "Init lds lidar success!");
    // 否则
    } else {
      // 记录初始化失败的错误日志
      DRIVER_ERROR(*this, "Init lds lidar fail!");
    }
  // 否则
  } else {
    // 记录无效数据源的错误日志
    DRIVER_ERROR(*this, "Invalid data src (%d), please check the launch file", data_src);
  }

  // 创建点云数据轮询线程
  pointclouddata_poll_thread_ = std::make_shared<std::thread>(&DriverNode::PointCloudDataPollThread, this);
  // 创建IMU数据轮询线程
  imudata_poll_thread_ = std::make_shared<std::thread>(&DriverNode::ImuDataPollThread, this);
}

}  // namespace livox_ros

// 包含rclcpp_components头文件，用于注册节点宏
#include <rclcpp_components/register_node_macro.hpp>
// 注册livox_ros::DriverNode节点到组件系统
RCLCPP_COMPONENTS_REGISTER_NODE(livox_ros::DriverNode)

#endif  // defined BUILDING_ROS2

// 定义DriverNode类的PointCloudDataPollThread成员函数
void DriverNode::PointCloudDataPollThread()
{
  // 声明未来状态变量
  std::future_status status;
  // 线程休眠3秒
  std::this_thread::sleep_for(std::chrono::seconds(3));
  // 执行循环，直到未来状态超时
  do {
    // 分发点云数据
    lddc_ptr_->DistributePointCloudData();
    // 等待未来对象，超时时间为0微秒
    status = future_.wait_for(std::chrono::microseconds(0));
  // 当状态为超时时继续循环
  } while (status == std::future_status::timeout);
}

// 定义DriverNode类的ImuDataPollThread成员函数
void DriverNode::ImuDataPollThread()
{
  // 声明未来状态变量
  std::future_status status;
  // 线程休眠3秒
  std::this_thread::sleep_for(std::chrono::seconds(3));
  // 执行循环，直到未来状态超时
  do {
    // 分发IMU数据
    lddc_ptr_->DistributeImuData();
    // 等待未来对象，超时时间为0微秒
    status = future_.wait_for(std::chrono::microseconds(0));
  // 当状态为超时时继续循环
  } while (status == std::future_status::timeout);
}




















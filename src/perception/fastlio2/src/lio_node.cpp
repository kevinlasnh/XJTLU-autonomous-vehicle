
// 文件最新改动时间：2025/11/13 -- 20:15
// 文件最新改动人：Claude Sonnet 4.5
// 操作者：You-guesssssss

#include <mutex>
#include <vector>
#include <queue>
#include <memory>
#include <iostream>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <ctime>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <livox_ros_driver2/msg/custom_msg.hpp>

#include "utils.h"
#include "map_builder/commons.h"
#include "map_builder/map_builder.h"

#include <pcl_conversions/pcl_conversions.h>
#include "tf2_ros/transform_broadcaster.h"
#include <geometry_msgs/msg/transform_stamped.hpp>
#include <nav_msgs/msg/path.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <yaml-cpp/yaml.h>

using namespace std::chrono_literals;
struct NodeConfig
{
    std::string imu_topic = "/livox/imu";
    std::string lidar_topic = "/livox/lidar";
    std::string body_frame = "body";
    std::string world_frame = "lidar";
    bool print_time_cost = false;
};
struct StateData
{
    bool lidar_pushed = false;
    std::mutex imu_mutex;
    std::mutex lidar_mutex;
    double last_lidar_time = -1.0;
    double last_imu_time = -1.0;
    std::deque<IMUData> imu_buffer;
    std::deque<std::pair<double, pcl::PointCloud<pcl::PointXYZINormal>::Ptr>> lidar_buffer;
    nav_msgs::msg::Path path;
};

class LIONode : public rclcpp::Node
{
public:
    LIONode() : Node("lio_node")
    {
        RCLCPP_INFO(this->get_logger(), "Node 文件运行成功");
        RCLCPP_INFO(this->get_logger(), "LIO Node Started");

        bool enable_log = shouldEnableLogging("fastlio2_lio_node");
        
        if (enable_log) {
            auto now = std::chrono::system_clock::now();
            std::time_t now_time = std::chrono::system_clock::to_time_t(now);
            std::tm* now_tm = std::localtime(&now_time);

            std::ostringstream filename_stream;
            filename_stream << "/home/jetson/2025_FYP/all_kind_output_file/All_Log/fastlio2/log_"
                            << (now_tm->tm_year + 1900)  // 年份
                            << std::setw(2) << std::setfill('0') << (now_tm->tm_mon + 1) // 月份
                            << std::setw(2) << std::setfill('0') << now_tm->tm_mday // 日期
                            << "_"
                            << std::setw(2) << std::setfill('0') << now_tm->tm_hour // 小时
                            << std::setw(2) << std::setfill('0') << now_tm->tm_min // 分钟
                            << std::setw(2) << std::setfill('0') << now_tm->tm_sec // 秒
                            << ".txt"; // 文件扩展名

            m_log_file.open(filename_stream.str(), std::ios::app);

            if (!m_log_file.is_open()) {
                RCLCPP_ERROR(this->get_logger(), "Unable to open log file");
                throw std::runtime_error("Unable to open log file");
            } else {
                RCLCPP_INFO(this->get_logger(), "Logging enabled: %s", filename_stream.str().c_str());
            }
        } else {
            RCLCPP_INFO(this->get_logger(), "Logging disabled by config");
        }

        loadParameters();

        m_imu_sub = this->create_subscription<sensor_msgs::msg::Imu>(m_node_config.imu_topic, 10, std::bind(&LIONode::imuCB, this, std::placeholders::_1));
        m_lidar_sub = this->create_subscription<livox_ros_driver2::msg::CustomMsg>(m_node_config.lidar_topic, 10, std::bind(&LIONode::lidarCB, this, std::placeholders::_1));

        m_body_cloud_pub = this->create_publisher<sensor_msgs::msg::PointCloud2>("body_cloud", 10000);
        m_world_cloud_pub = this->create_publisher<sensor_msgs::msg::PointCloud2>("world_cloud", 10000);
        m_path_pub = this->create_publisher<nav_msgs::msg::Path>("lio_path", 10000);
        m_odom_pub = this->create_publisher<nav_msgs::msg::Odometry>("lio_odom", 10000);
        m_tf_broadcaster = std::make_shared<tf2_ros::TransformBroadcaster>(*this);

        m_state_data.path.poses.clear();
        m_state_data.path.header.frame_id = m_node_config.world_frame;

        m_kf = std::make_shared<IESKF>();
        m_builder = std::make_shared<MapBuilder>(m_builder_config, m_kf);

        // fastlio2 消息发布的频率更改处
        m_timer = this->create_wall_timer(20ms, std::bind(&LIONode::timerCB, this));
    }

    ~LIONode()
    {
        if (m_log_file.is_open()) {
            m_log_file.close();
            RCLCPP_INFO(this->get_logger(), "Log file closed.");
        }
    }

    bool shouldEnableLogging(const std::string& node_key)
    {
        try {
            std::string config_path = "/home/jetson/2025_FYP/all_kind_output_file/Other_File/manual_config/log_switch.yaml";
            YAML::Node config = YAML::LoadFile(config_path);
            
            if (config[node_key]) {
                bool enable = config[node_key]["enable_logging"].as<bool>();
                return enable;
            }
            
            RCLCPP_WARN(this->get_logger(), "No logging config found for '%s', enabling by default", node_key.c_str());
            return true;
            
        } catch (const std::exception& e) {
            RCLCPP_ERROR(this->get_logger(), "Failed to read log config: %s", e.what());
            return true; // 配置文件读取失败，默认启用日志
        }
    }

    void loadParameters()
    {
        this->declare_parameter("config_path", "");
        std::string config_path;
        this->get_parameter<std::string>("config_path", config_path);

        YAML::Node config = YAML::LoadFile(config_path);
        if (!config)
        {
            RCLCPP_WARN(this->get_logger(), "FAIL TO LOAD YAML FILE!");
            return;
        }

        RCLCPP_INFO(this->get_logger(), "LOAD FROM YAML CONFIG PATH: %s", config_path.c_str());

        m_node_config.imu_topic = config["imu_topic"].as<std::string>();
        m_node_config.lidar_topic = config["lidar_topic"].as<std::string>();
        m_node_config.body_frame = config["body_frame"].as<std::string>();
        m_node_config.world_frame = config["world_frame"].as<std::string>();
        m_node_config.print_time_cost = config["print_time_cost"].as<bool>();

        m_builder_config.lidar_filter_num = config["lidar_filter_num"].as<int>();
        m_builder_config.lidar_min_range = config["lidar_min_range"].as<double>();
        m_builder_config.lidar_max_range = config["lidar_max_range"].as<double>();
        m_builder_config.scan_resolution = config["scan_resolution"].as<double>();
        m_builder_config.map_resolution = config["map_resolution"].as<double>();
        m_builder_config.cube_len = config["cube_len"].as<double>();
        m_builder_config.det_range = config["det_range"].as<double>();
        m_builder_config.move_thresh = config["move_thresh"].as<double>();
        m_builder_config.na = config["na"].as<double>();
        m_builder_config.ng = config["ng"].as<double>();
        m_builder_config.nba = config["nba"].as<double>();
        m_builder_config.nbg = config["nbg"].as<double>();

        m_builder_config.imu_init_num = config["imu_init_num"].as<int>();
        m_builder_config.near_search_num = config["near_search_num"].as<int>();
        m_builder_config.ieskf_max_iter = config["ieskf_max_iter"].as<int>();
        m_builder_config.gravity_align = config["gravity_align"].as<bool>();
        m_builder_config.esti_il = config["esti_il"].as<bool>();
        std::vector<double> t_il_vec = config["t_il"].as<std::vector<double>>();
        std::vector<double> r_il_vec = config["r_il"].as<std::vector<double>>();
        m_builder_config.t_il << t_il_vec[0], t_il_vec[1], t_il_vec[2];
        m_builder_config.r_il << r_il_vec[0], r_il_vec[1], r_il_vec[2], r_il_vec[3], r_il_vec[4], r_il_vec[5], r_il_vec[6], r_il_vec[7], r_il_vec[8];
        m_builder_config.lidar_cov_inv = config["lidar_cov_inv"].as<double>();
    }

    void imuCB(const sensor_msgs::msg::Imu::SharedPtr msg)
    {
        std::lock_guard<std::mutex> lock(m_state_data.imu_mutex);
        double timestamp = Utils::getSec(msg->header);
        RCLCPP_INFO(this->get_logger(), "Received IMU data: accel(%.2f, %.2f, %.2f), gyro(%.2f, %.2f, %.2f), time: %.6f",
                    msg->linear_acceleration.x, msg->linear_acceleration.y, msg->linear_acceleration.z,
                    msg->angular_velocity.x, msg->angular_velocity.y, msg->angular_velocity.z, timestamp);
        
        if (m_log_file.is_open()) {
            auto ros_time = this->now();
            int64_t ros_timestamp = ros_time.nanoseconds();
            m_log_file << "ROS_timestamp: " << ros_timestamp 
                      << ", Received IMU data: accel(" 
                      << msg->linear_acceleration.x << ", " << msg->linear_acceleration.y << ", " << msg->linear_acceleration.z
                      << "), gyro(" 
                      << msg->angular_velocity.x << ", " << msg->angular_velocity.y << ", " << msg->angular_velocity.z
                      << "), time: " << timestamp << std::endl;
            m_log_file.flush();
        }
        
        if (timestamp < m_state_data.last_imu_time)
        {
            RCLCPP_WARN(this->get_logger(), "IMU Message is out of order");
            std::deque<IMUData>().swap(m_state_data.imu_buffer);
        }
        m_state_data.imu_buffer.emplace_back(V3D(msg->linear_acceleration.x, msg->linear_acceleration.y, msg->linear_acceleration.z) * 10.0,
                                             V3D(msg->angular_velocity.x, msg->angular_velocity.y, msg->angular_velocity.z),
                                             timestamp);
        m_state_data.last_imu_time = timestamp;
    }
    void lidarCB(const livox_ros_driver2::msg::CustomMsg::SharedPtr msg)
    {
        CloudType::Ptr cloud = Utils::livox2PCL(msg, m_builder_config.lidar_filter_num, m_builder_config.lidar_min_range, m_builder_config.lidar_max_range);
        RCLCPP_INFO(this->get_logger(), "Received LIDAR data: %zu points, time: %.6f", cloud->size(), Utils::getSec(msg->header));
        
        if (m_log_file.is_open()) {
            auto ros_time = this->now();
            int64_t ros_timestamp = ros_time.nanoseconds();
            m_log_file << "ROS_timestamp: " << ros_timestamp 
                      << ", Received LIDAR data: " << cloud->size() 
                      << " points, time: " << Utils::getSec(msg->header) << std::endl;
            m_log_file.flush();
        }
        
        std::lock_guard<std::mutex> lock(m_state_data.lidar_mutex);
        double timestamp = Utils::getSec(msg->header);
        if (timestamp < m_state_data.last_lidar_time)
        {
            RCLCPP_WARN(this->get_logger(), "Lidar Message is out of order");
            std::deque<std::pair<double, pcl::PointCloud<pcl::PointXYZINormal>::Ptr>>().swap(m_state_data.lidar_buffer);
        }
        m_state_data.lidar_buffer.emplace_back(timestamp, cloud);
        m_state_data.last_lidar_time = timestamp;
    }

    bool syncPackage()
    {
        if (m_state_data.imu_buffer.empty() || m_state_data.lidar_buffer.empty())
            return false;
        if (!m_state_data.lidar_pushed)
        {
            m_package.cloud = m_state_data.lidar_buffer.front().second;
            std::sort(m_package.cloud->points.begin(), m_package.cloud->points.end(), [](PointType &p1, PointType &p2)
                      { return p1.curvature < p2.curvature; });
            m_package.cloud_start_time = m_state_data.lidar_buffer.front().first;
            m_package.cloud_end_time = m_package.cloud_start_time + m_package.cloud->points.back().curvature / 1000.0;
            m_state_data.lidar_pushed = true;
        }
        if (m_state_data.last_imu_time < m_package.cloud_end_time)
            return false;

        Vec<IMUData>().swap(m_package.imus);
        while (!m_state_data.imu_buffer.empty() && m_state_data.imu_buffer.front().time < m_package.cloud_end_time)
        {
            m_package.imus.emplace_back(m_state_data.imu_buffer.front());
            m_state_data.imu_buffer.pop_front();
        }
        m_state_data.lidar_buffer.pop_front();
        m_state_data.lidar_pushed = false;
        return true;
    }

    void publishCloud(rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr pub, CloudType::Ptr cloud, std::string frame_id, const double &time)
    {
        if (pub->get_subscription_count() <= 0)
            return;
        sensor_msgs::msg::PointCloud2 cloud_msg;
        pcl::toROSMsg(*cloud, cloud_msg);
        cloud_msg.header.frame_id = frame_id;
        cloud_msg.header.stamp = Utils::getTime(time);
        pub->publish(cloud_msg);
    }

    void publishOdometry(rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr odom_pub, std::string frame_id, std::string child_frame, const double &time)
    {
        if (odom_pub->get_subscription_count() <= 0)
            return;
        nav_msgs::msg::Odometry odom;
        odom.header.frame_id = frame_id;
        odom.header.stamp = Utils::getTime(time);
        odom.child_frame_id = child_frame;
        odom.pose.pose.position.x = m_kf->x().t_wi.x();
        odom.pose.pose.position.y = m_kf->x().t_wi.y();
        odom.pose.pose.position.z = m_kf->x().t_wi.z();
        Eigen::Quaterniond q(m_kf->x().r_wi);
        odom.pose.pose.orientation.x = q.x();
        odom.pose.pose.orientation.y = q.y();
        odom.pose.pose.orientation.z = q.z();
        odom.pose.pose.orientation.w = q.w();

        V3D vel = m_kf->x().r_wi.transpose() * m_kf->x().v;
        odom.twist.twist.linear.x = vel.x();
        odom.twist.twist.linear.y = vel.y();
        odom.twist.twist.linear.z = vel.z();
        odom_pub->publish(odom);
    }

    void publishPath(rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr path_pub, std::string frame_id, const double &time)
    {
        if (path_pub->get_subscription_count() <= 0)
            return;
        geometry_msgs::msg::PoseStamped pose;
        pose.header.frame_id = frame_id;
        pose.header.stamp = Utils::getTime(time);
        pose.pose.position.x = m_kf->x().t_wi.x();
        pose.pose.position.y = m_kf->x().t_wi.y();
        pose.pose.position.z = m_kf->x().t_wi.z();
        Eigen::Quaterniond q(m_kf->x().r_wi);
        pose.pose.orientation.x = q.x();
        pose.pose.orientation.y = q.y();
        pose.pose.orientation.z = q.z();
        pose.pose.orientation.w = q.w();
        m_state_data.path.poses.push_back(pose);
        path_pub->publish(m_state_data.path);
    }

    void broadCastTF(std::shared_ptr<tf2_ros::TransformBroadcaster> broad_caster, std::string frame_id, std::string child_frame, const double &time)
    {
        geometry_msgs::msg::TransformStamped transformStamped;
        transformStamped.header.frame_id = frame_id;
        transformStamped.child_frame_id = child_frame;
        transformStamped.header.stamp = Utils::getTime(time);
        Eigen::Quaterniond q(m_kf->x().r_wi);
        V3D t = m_kf->x().t_wi;
        transformStamped.transform.translation.x = t.x();
        transformStamped.transform.translation.y = t.y();
        transformStamped.transform.translation.z = t.z();
        transformStamped.transform.rotation.x = q.x();
        transformStamped.transform.rotation.y = q.y();
        transformStamped.transform.rotation.z = q.z();
        transformStamped.transform.rotation.w = q.w();
        broad_caster->sendTransform(transformStamped);
    }

    void timerCB()
    {
        if (!syncPackage())
            return;
        RCLCPP_INFO(this->get_logger(), "Processing sync package: %zu IMU samples, %zu LIDAR points", 
                    m_package.imus.size(), m_package.cloud->size());
        
        if (m_log_file.is_open()) {
            auto ros_time = this->now();
            int64_t ros_timestamp = ros_time.nanoseconds();
            m_log_file << "ROS_timestamp: " << ros_timestamp 
                      << ", Processing sync package: " << m_package.imus.size() 
                      << " IMU samples, " << m_package.cloud->size() << " LIDAR points" << std::endl;
            m_log_file.flush();
        }
        
        auto t1 = std::chrono::high_resolution_clock::now();
        m_builder->process(m_package);
        auto t2 = std::chrono::high_resolution_clock::now();

        if (m_node_config.print_time_cost)
        {
            auto time_used = std::chrono::duration_cast<std::chrono::duration<double>>(t2 - t1).count() * 1000;
            RCLCPP_WARN(this->get_logger(), "Time cost: %.2f ms", time_used);
        }

        if (m_builder->status() != BuilderStatus::MAPPING)
            return;

        RCLCPP_INFO(this->get_logger(), "Current position: x=%.2f, y=%.2f, z=%.2f", 
                    m_kf->x().t_wi.x(), m_kf->x().t_wi.y(), m_kf->x().t_wi.z());
        
        if (m_log_file.is_open()) {
            auto ros_time = this->now();
            int64_t ros_timestamp = ros_time.nanoseconds();
            m_log_file << "ROS_timestamp: " << ros_timestamp 
                      << ", Current position: x=" << m_kf->x().t_wi.x() 
                      << ", y=" << m_kf->x().t_wi.y() 
                      << ", z=" << m_kf->x().t_wi.z() << std::endl;
            m_log_file.flush();
        }

        broadCastTF(m_tf_broadcaster, m_node_config.world_frame, m_node_config.body_frame, this->now().seconds());

        publishOdometry(m_odom_pub, m_node_config.world_frame, m_node_config.body_frame, this->now().seconds());

        CloudType::Ptr body_cloud = m_builder->lidar_processor()->transformCloud(m_package.cloud, m_kf->x().r_il, m_kf->x().t_il);

        publishCloud(m_body_cloud_pub, body_cloud, m_node_config.body_frame, this->now().seconds());

        CloudType::Ptr world_cloud = m_builder->lidar_processor()->transformCloud(m_package.cloud, m_builder->lidar_processor()->r_wl(), m_builder->lidar_processor()->t_wl());

        publishCloud(m_world_cloud_pub, world_cloud, m_node_config.world_frame, this->now().seconds());

        publishPath(m_path_pub, m_node_config.world_frame, this->now().seconds());
    }

private:
    rclcpp::Subscription<livox_ros_driver2::msg::CustomMsg>::SharedPtr m_lidar_sub;
    rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr m_imu_sub;

    rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr m_body_cloud_pub;
    rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr m_world_cloud_pub;
    rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr m_path_pub;
    rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr m_odom_pub;

    rclcpp::TimerBase::SharedPtr m_timer;
    StateData m_state_data;
    SyncPackage m_package;
    NodeConfig m_node_config;
    Config m_builder_config;
    std::shared_ptr<IESKF> m_kf;
    std::shared_ptr<MapBuilder> m_builder;
    std::shared_ptr<tf2_ros::TransformBroadcaster> m_tf_broadcaster;
    std::ofstream m_log_file;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);

    try {
        rclcpp::spin(std::make_shared<LIONode>());
    }
    catch (const std::exception &e) {
        RCLCPP_ERROR(rclcpp::get_logger("lio_node"), "Node 文件运行出错 %s", e.what());
    }

    rclcpp::shutdown();
    return 0;
}
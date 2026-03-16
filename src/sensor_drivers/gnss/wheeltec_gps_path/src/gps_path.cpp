#include "rclcpp/rclcpp.hpp"
#include <sensor_msgs/msg/nav_sat_fix.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <nav_msgs/msg/path.hpp>
#include <math.h>
#include <fstream>
#include <sstream>
#include <ctime>
#include <iomanip>
#include <deque>
#include <filesystem>
#include <chrono>
#include <yaml-cpp/yaml.h>

#define EARTH_RADIUS 6378.137
#define NORTH_SOUTH_OFFSET 459.13  // NS方向误差
#define EAST_WEST_OFFSET 1002.04   // EW方向误差
#define DEFAULT_THRESHOLD 3.0     // 不足20条数据时的阈值

using std::placeholders::_1;

bool pose_init;

class GpsPath : public rclcpp::Node
{
public:
    GpsPath()
    : Node("GpsPath")
    {
        // 检查是否启用日志
        bool enable_log = shouldEnableLogging("wheeltec_gps_path");
        
        if (enable_log) {
            // Grok 进行了改动
            // 原因：重新配置日志路径
            // 内容：修改日志文件的保存路径
            // 影响：日志文件将保存在新的路径中
            // Create log directory if it doesn't exist
            std::string log_dir = "/home/jetson/2025_FYP/all_kind_output_file/All_Log/wheeltec_gps_path";
            std::filesystem::create_directories(log_dir);

            // Generate log filename based on current time
            auto now = std::chrono::system_clock::now();
            auto now_time = std::chrono::system_clock::to_time_t(now);
            std::tm* now_tm = std::localtime(&now_time);
            
            std::ostringstream filename_stream;
            filename_stream << log_dir << "/log_"
                            << (now_tm->tm_year + 1900)
                            << std::setw(2) << std::setfill('0') << (now_tm->tm_mon + 1)
                            << std::setw(2) << std::setfill('0') << now_tm->tm_mday
                            << "_"
                            << std::setw(2) << std::setfill('0') << now_tm->tm_hour
                            << std::setw(2) << std::setfill('0') << now_tm->tm_min
                            << std::setw(2) << std::setfill('0') << now_tm->tm_sec
                            << ".txt";

            log_filepath_ = filename_stream.str();
            log_file_.open(log_filepath_, std::ios::app);
            
            if (!log_file_.is_open()) {
                RCLCPP_ERROR(this->get_logger(), "Unable to open log file: %s", log_filepath_.c_str());
            } else {
                RCLCPP_INFO(this->get_logger(), "Logging enabled: %s", log_filepath_.c_str());
            }
        } else {
            RCLCPP_INFO(this->get_logger(), "Logging disabled by config");
        }

        state_pub_ = create_publisher<nav_msgs::msg::Path>("gps_path", 100);
        subscription_ = this->create_subscription<sensor_msgs::msg::NavSatFix>(
            "/fix", 1, std::bind(&GpsPath::gps_callback, this, _1));
        
        timer_ = this->create_wall_timer(
            std::chrono::seconds(60),
            std::bind(&GpsPath::timer_callback, this));  // 每60秒触发一次保存
    }

    // 检查是否启用日志的辅助函数
    bool shouldEnableLogging(const std::string& node_key)
    {
        try {
            std::string config_path = "/home/jetson/2025_FYP/all_kind_output_file/Other_File/manual_config/log_switch.yaml";
            YAML::Node config = YAML::LoadFile(config_path);
            
            // 直接读取节点配置
            if (config[node_key]) {
                bool enable = config[node_key]["enable_logging"].as<bool>();
                return enable;
            }
            
            // 如果找不到配置，默认启用日志
            RCLCPP_WARN(this->get_logger(), "No logging config found for '%s', enabling by default", node_key.c_str());
            return true;
            
        } catch (const std::exception& e) {
            RCLCPP_ERROR(this->get_logger(), "Failed to read log config: %s", e.what());
            return true; // 配置文件读取失败，默认启用日志
        }
    }

    struct lla_pose
    {
        double latitude;
        double longitude;
        double altitude;
    };

    double rad(double d)
    {
        return d * M_PI / 180.0;
    }

    void save_to_file(double latitude, double longitude)
    {
        std::ofstream file;
        file.open("/home/jetson/ros2_ws/src/GNSS/GNSSlog/gps_path_std.txt", std::ios::app);

        if (file.is_open())
        {
            time_t now = time(0);
            struct tm *local_time = localtime(&now);
            std::stringstream time_stream;
            time_stream << (1900 + local_time->tm_year) << "-"
                        << (1 + local_time->tm_mon) << "-"
                        << local_time->tm_mday << " "
                        << local_time->tm_hour << ":"
                        << local_time->tm_min << ":"
                        << local_time->tm_sec;

            file << time_stream.str() 
                 << ", Latitude: " << std::fixed << std::setprecision(10) << latitude
                 << ", Longitude: " << std::fixed << std::setprecision(10) << longitude 
                 << std::endl;

            RCLCPP_INFO(this->get_logger(), "Data saved: %s, Latitude: %.10f, Longitude: %.10f", 
                        time_stream.str().c_str(), latitude, longitude);
        }
        else
        {
            RCLCPP_ERROR(this->get_logger(), "Unable to open file to save GPS path data!");
        }

        file.close();
    }

private:
    std::deque<lla_pose> recent_data_;

    bool is_outlier(double latitude, double longitude)
    {
        if (recent_data_.size() < 20)
        {
            return false;
        }

        double max_lat_diff = 0.0;
        double max_lon_diff = 0.0;
        for (size_t i = 0; i < recent_data_.size() - 1; ++i)
        {
            max_lat_diff = std::max(max_lat_diff, fabs(recent_data_[i + 1].latitude - recent_data_[i].latitude));
            max_lon_diff = std::max(max_lon_diff, fabs(recent_data_[i + 1].longitude - recent_data_[i].longitude));
        }

        double lat_threshold = std::max(DEFAULT_THRESHOLD, 3 * max_lat_diff);
        double lon_threshold = std::max(DEFAULT_THRESHOLD, 3 * max_lon_diff);

        return fabs(latitude - recent_data_.back().latitude) > lat_threshold ||
               fabs(longitude - recent_data_.back().longitude) > lon_threshold;
    }

    void gps_callback(const sensor_msgs::msg::NavSatFix::SharedPtr gps_msg)
    {

        // 这里由 grok 进行了改动
        // Log the GPS data
        if (log_file_.is_open()) {
            // 这里原本是使用 C++ 标准时间的 log 文件写入，现在在 log 文件写入中加入了 ROS 系统时间戳
            // auto now = std::chrono::system_clock::now();
            // auto now_time = std::chrono::system_clock::to_time_t(now);
            // std::tm* now_tm = std::localtime(&now_time);
            // char timestamp[20];
            // strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", now_tm);
            
            // log_file_ << "[" << timestamp << "] GPS Data - Lat: " << gps_msg->latitude 
            //          << ", Lon: " << gps_msg->longitude 
            //          << ", Alt: " << gps_msg->altitude << std::endl;

            // 新的代码块：获取 ROS 系统时间戳并写入日志
            auto ros_time = this->now();
            int64_t ros_timestamp = ros_time.nanoseconds();  // 19位纳秒格式
            // 同时保留人类可读时间（可选）
            auto now = std::chrono::system_clock::now();
            auto now_time = std::chrono::system_clock::to_time_t(now);
            std::tm* now_tm = std::localtime(&now_time);
            char readable_time[20];
            strftime(readable_time, sizeof(readable_time), "%Y-%m-%d %H:%M:%S", now_tm);
            // 写入日志，包含ROS时间戳和人类可读时间
            log_file_ << "ROS_timestamp: " << ros_timestamp 
                    << ", Time: [" << readable_time << "]"
                    << ", Lat: " << gps_msg->latitude 
                    << ", Lon: " << gps_msg->longitude 
                    << ", Alt: " << gps_msg->altitude << std::endl;
            
            log_file_.flush();
        }

        if (std::isnan(gps_msg->latitude) || std::isnan(gps_msg->longitude) || std::isnan(gps_msg->altitude))
        {
            // 此处代码由 grok 进行了改动
            RCLCPP_WARN(this->get_logger(), "Received invalid GPS data: lat=%f, lon=%f, alt=%f", gps_msg->latitude, gps_msg->longitude, gps_msg->altitude);
            return;
        }

        double adjusted_latitude = gps_msg->latitude + NORTH_SOUTH_OFFSET / 111000.0;
        double adjusted_longitude = gps_msg->longitude + EAST_WEST_OFFSET / (cos(rad(gps_msg->latitude)) * 111000.0);

        if (is_outlier(adjusted_latitude, adjusted_longitude))
        {
            RCLCPP_WARN(this->get_logger(), "Outlier detected, using previous data.");
            adjusted_latitude = recent_data_.back().latitude;
            adjusted_longitude = recent_data_.back().longitude;
        }

        recent_data_.push_back({adjusted_latitude, adjusted_longitude, gps_msg->altitude});
        if (recent_data_.size() > 20)
        {
            recent_data_.pop_front();
        }

        save_to_file(adjusted_latitude, adjusted_longitude);
    }

    void timer_callback()
    {
        if (pose_init)
        {
            save_to_file(init_pose.latitude, init_pose.longitude);
        }
    }

    nav_msgs::msg::Path ros_path_;
    lla_pose init_pose;
    rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr state_pub_;
    rclcpp::Subscription<sensor_msgs::msg::NavSatFix>::SharedPtr subscription_;
    rclcpp::TimerBase::SharedPtr timer_;
    // 这里由 grok 进行了改动
    std::ofstream log_file_;
    std::string log_filepath_;
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    pose_init = false;
    rclcpp::spin(std::make_shared<GpsPath>());
    rclcpp::shutdown();
    return 0;
}


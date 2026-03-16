#include "rclcpp/rclcpp.hpp"
#include <sensor_msgs/msg/nav_sat_fix.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <nav_msgs/msg/path.hpp>
#include <math.h>
#include <fstream>
#include <sstream>
#include <ctime>
#include <iomanip> // 用于设置小数位精度

#define EARTH_RADIUS 6378.137
using std::placeholders::_1;

bool pose_init;

class GpsPath : public rclcpp::Node
{
public:
    GpsPath()
    : Node("GpsPath")
    {
        state_pub_ = create_publisher<nav_msgs::msg::Path>("gps_path", 100);
        subscription_ = this->create_subscription<sensor_msgs::msg::NavSatFix>(
            "/fix", 1, std::bind(&GpsPath::gps_callback, this, _1));
        
        timer_ = this->create_wall_timer(
            std::chrono::seconds(60),
            std::bind(&GpsPath::timer_callback, this));  // 每60秒触发一次保存
    }

    struct lla_pose
    {
        double latitude;
        double longitude;
        double altitude;
    };

    double rad(double d)
    {
        return d * 3.1415926 / 180.0;
    }

    void save_to_file(double latitude, double longitude)
    {
        std::ofstream file;
        file.open("/home/jetson/GPS_ws/gps_path_GN.txt", std::ios::app); // 修改为新的文件路径

        if (file.is_open())
        {
            // 获取当前时间
            time_t now = time(0);
            struct tm *local_time = localtime(&now);
            std::stringstream time_stream;
            time_stream << (1900 + local_time->tm_year) << "-"
                        << (1 + local_time->tm_mon) << "-"
                        << local_time->tm_mday << " "
                        << local_time->tm_hour << ":"
                        << local_time->tm_min << ":"
                        << local_time->tm_sec;

            // 保存高精度经纬度和时间
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
    void gps_callback(const sensor_msgs::msg::NavSatFix::SharedPtr gps_msg)
    {
        // 检查是否是有效数据
        if (std::isnan(gps_msg->latitude) || std::isnan(gps_msg->longitude) || std::isnan(gps_msg->altitude))
        {
            RCLCPP_WARN(this->get_logger(), "Received invalid GPS data: Latitude = nan, Longitude = nan");
            return;
        }

        if (!pose_init)
        {
            init_pose.latitude = gps_msg->latitude;
            init_pose.longitude = gps_msg->longitude;
            init_pose.altitude = gps_msg->altitude;
            pose_init = true;
        }
        else
        {
            // 计算 XYZ 坐标
            double radLat1, radLat2, radLong1, radLong2, delta_lat, delta_long, x, y;

            radLat1 = rad(init_pose.latitude);
            radLong1 = rad(init_pose.longitude);

            radLat2 = rad(gps_msg->latitude);
            radLong2 = rad(gps_msg->longitude);

            // 计算 x
            delta_lat = radLat2 - radLat1;
            delta_long = 0;

            if (delta_lat > 0)
                x = -2 * asin(sqrt(pow(sin(delta_lat / 2), 2) + cos(radLat1) * cos(radLat2) * pow(sin(delta_long / 2), 2)));
            else
                x = -2 * asin(sqrt(pow(sin(delta_lat / 2), 2) + cos(radLat1) * cos(radLat2) * pow(sin(delta_long / 2), 2)));
            x = x * EARTH_RADIUS * 1000;

            // 计算 y
            delta_lat = 0;
            delta_long = radLong2 - radLong1;
            if (delta_long > 0)
                y = 2 * asin(sqrt(pow(sin(delta_lat / 2), 2) + cos(radLat2) * cos(radLat2) * pow(sin(delta_long / 2), 2)));
            else
                y = -2 * asin(sqrt(pow(sin(delta_lat / 2), 2) + cos(radLat2) * cos(radLat2) * pow(sin(delta_long / 2), 2)));
            y = y * EARTH_RADIUS * 1000;

            // 计算 z
            double z = gps_msg->altitude - init_pose.altitude;

            // 发布路径
            ros_path_.header.frame_id = "path";
            ros_path_.header.stamp = rclcpp::Node::now();
            geometry_msgs::msg::PoseStamped pose;
            pose.header = ros_path_.header;
            pose.pose.position.x = x;
            pose.pose.position.y = y;
            pose.pose.position.z = z;
            ros_path_.poses.push_back(pose);

            state_pub_->publish(ros_path_);

            RCLCPP_INFO(this->get_logger(), "(x: %0.6f, y: %0.6f, z: %0.6f)", x, y, z);
        }

        // 将原始经纬度数据传递给保存函数
        save_to_file(gps_msg->latitude, gps_msg->longitude);
    }

    void timer_callback()
    {
        // 定时器回调，每60秒保存一次初始经纬度（高精度）
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
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    pose_init = false;
    rclcpp::spin(std::make_shared<GpsPath>());
    rclcpp::shutdown();
    return 0;
}


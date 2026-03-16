#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist_with_covariance_stamped.hpp"
#include "serial/serial.h"
#include <cstring>
#include <iostream>

bool serialopen = 0; //when serial is open, change it to 1, otherwise, change it to 0;
float data_value[13];
class TwistWithCovarianceNode : public rclcpp::Node
{
public:

    // Replace "/dev/ttyUSB0" with the actual serial port name
    TwistWithCovarianceNode() : Node("twist_with_covariance"), serial_port_("/dev/serial_twistctl", 115200, serial::Timeout::simpleTimeout(1000))
    {
        publisher_ = this->create_publisher<geometry_msgs::msg::TwistWithCovarianceStamped>("twist_with_covariance", 1000/period_ms);
        
        timer_ = this->create_wall_timer(std::chrono::milliseconds(period_ms), std::bind(&TwistWithCovarianceNode::serialCallback, this));
    }


private:
   
    void serialCallback()
    {
        if (serial_port_.available() > 0)
        {
            geometry_msgs::msg::TwistWithCovarianceStamped msg;
            // data: "x, y, z, Q.x, Q.y, Q.z, Q.w, linear.x, linear.y, linear.z, angular.x, angular.y, angular.z\n"
            std::string data = serial_port_.readline();
            int len = data.length();
            int tot = 0;
            std::string tmp = "";

            for (int i = 0; i < len; i++) {
                if (data[i] == ' ') {
                    // 跳过空格
                    continue;
                }
                if (data[i] == ',' || data[i] == '\n') {
                    // 将 tmp 转换为浮点数并存储到 data_value 数组中
                    try {
                        data_value[tot++] = std::stof(tmp);
                    } catch (const std::invalid_argument& e) {
                        std::cerr << "Error converting string to float: " << e.what() << std::endl;
                        // 处理无效的浮点数表示
                    }
                    tmp = "";
                } else {
                    tmp += data[i];
                }
            }


            // 此处使用的是独立时钟，为了让消息时间戳与系统时间同步，使用系统时间戳替代
            // ======================================
            // msg.header.stamp = rclcpp::Clock{}.now();
            // ======================================
            // 已改动成系统时间戳
            msg.header.stamp = this->now();

            msg.header.frame_id = "twist_with_covariance";
            msg.twist.twist.linear.x = data_value[8];
            msg.twist.twist.linear.y = -data_value[7];
            msg.twist.twist.linear.z = data_value[9];
            msg.twist.twist.angular.x = data_value[11];
            msg.twist.twist.angular.y = -data_value[10];
            msg.twist.twist.angular.z = data_value[12];
            publisher_->publish(msg);
        }
    }

    serial::Serial serial_port_;
    rclcpp::Publisher<geometry_msgs::msg::TwistWithCovarianceStamped>::SharedPtr publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
    int period_ms = 20; // pubilish period
};

class emptytwistNode : public rclcpp::Node
{
public:
    emptytwistNode() : Node("twist_with_covariance")
    {
        publisher_ = this->create_publisher<geometry_msgs::msg::TwistWithCovarianceStamped>("twist_with_covariance", 1000/period_ms);
        
        timer_ = this->create_wall_timer(std::chrono::milliseconds(period_ms), std::bind(&emptytwistNode::publishEmptyMessage, this));
    }


private:
   
    void publishEmptyMessage() {
        geometry_msgs::msg::TwistWithCovarianceStamped empty_twist_msg;
        // Fill the message with default values or leave it empty depending on your application
        // 此处使用的是独立时钟，为了让消息时间戳与系统时间同步，使用系统时间戳替代
        // ==================================================
        // empty_twist_msg.header.stamp = rclcpp::Clock{}.now();
        // ==================================================
        // 已改动成系统时间戳
        empty_twist_msg.header.stamp = this->now();

        empty_twist_msg.header.frame_id = "twist_with_covariance";
        empty_twist_msg.twist.twist.linear.x = 0;
        empty_twist_msg.twist.twist.linear.y = 0;
        empty_twist_msg.twist.twist.linear.z = 0;
        empty_twist_msg.twist.twist.angular.x = 0;
        empty_twist_msg.twist.twist.angular.y = 0;
        empty_twist_msg.twist.twist.angular.z = 0;
        publisher_->publish(empty_twist_msg);
    }
    rclcpp::Publisher<geometry_msgs::msg::TwistWithCovarianceStamped>::SharedPtr publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
    int period_ms = 20; // pubilish period
};


int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    
 
    if (serialopen){
        auto node = std::make_shared<TwistWithCovarianceNode>();
        rclcpp::spin(node);
    } else {
        auto emptynode = std::make_shared<emptytwistNode>();
        rclcpp::spin(emptynode);
    }
    rclcpp::shutdown();
    return 0;
}

from functools import partial
from nmea_msgs.msg import Sentence
from sensor_msgs.msg import NavSatFix
import rclpy
from libnmea_navsat_driver.driver import Ros2NMEADriver

def nmea_sentence_callback(nmea_sentence, driver):
    try:
        # 创建 NavSatFix 消息
        nav_sat_fix = NavSatFix()

        # 填充头信息
        nav_sat_fix.header.stamp = nmea_sentence.header.stamp
        nav_sat_fix.header.frame_id = "gps"

        # 设置基本的 GPS 信息（例如经纬度和海拔）
        nav_sat_fix.latitude = driver.latitude
        nav_sat_fix.longitude = driver.longitude
        nav_sat_fix.altitude = driver.altitude

        # 不设置 position_covariance 和 position_covariance_type
        # 如果有默认值或者未设置，将不会发布这些字段
        # 省略这些字段，确保不包含在消息中
        nav_sat_fix.position_covariance = []
        nav_sat_fix.position_covariance_type = 0
        # 发布消息
        driver.get_publisher().publish(nav_sat_fix)

    except ValueError as e:
        rclpy.get_logger().warn(
            "Value error, likely due to missing fields in the NMEA message. Error was: %s. "
            "Please report this issue." % e)

def main(args=None):
    rclpy.init(args=args)

    # 创建 ROS2 驱动对象
    driver = Ros2NMEADriver()

    # 获取 GPS 话题数据
    driver.create_subscription(
        Sentence, 'nmea_sentence', partial(nmea_sentence_callback, driver=driver), 10)

    rclpy.spin(driver)

    rclpy.shutdown()


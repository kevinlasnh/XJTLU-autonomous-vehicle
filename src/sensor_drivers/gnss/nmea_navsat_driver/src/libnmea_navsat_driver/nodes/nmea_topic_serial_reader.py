import time
import serial

from nmea_msgs.msg import Sentence
import rclpy

from libnmea_navsat_driver.driver import Ros2NMEADriver


def main(args=None):
    rclpy.init(args=args)

    driver = Ros2NMEADriver()

    nmea_pub = driver.create_publisher(Sentence, "nmea_sentence", 10)

    serial_port = driver.declare_parameter('port', '/dev/ttyUSB0').value
    serial_baud = driver.declare_parameter('baud', 4800).value
    
    publish_interval = 1
    last_publish_time = time.time()

    # Get the frame_id
    frame_id = driver.get_frame_id()

    try:
        GPS = serial.Serial(port=serial_port, baudrate=serial_baud, timeout=2)
        try:
            while rclpy.ok():
                data = GPS.readline().strip()

                current_time = time.time()
                
                if current_time - last_publish_time >= publish_interval:
                    sentence = Sentence()
                    sentence.header.stamp = driver.get_clock().now().to_msg()
                    sentence.header.frame_id = frame_id
                    sentence.sentence = data
                    nmea_pub.publish(sentence)

                    last_publish_time = current_time

        except Exception as e:
            driver.get_logger().error("Ros error: {0}".format(e))
            GPS.close()  # Close GPS serial port
    except serial.SerialException as ex:
        driver.get_logger().fatal("Could not open serial port: I/O error({0}): {1}".format(ex.errno, ex.strerror))


if __name__ == '__main__':
    main()


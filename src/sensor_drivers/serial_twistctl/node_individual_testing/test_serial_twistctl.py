#!/usr/bin/env python3
"""
Test script for serial_twistctl node
This script publishes Twist messages to /cmd_vel topic to test the serial_twistctl node
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import time
from enum import Enum

class TestType(Enum):
    """Test types for different scenarios"""
    SINGLE = 1           # Single message
    MULTIPLE = 2         # Multiple messages
    CONTINUOUS = 3       # Continuous messages

class TwistPublisherTest(Node):
    def __init__(self):
        super().__init__('test_twist_publisher')
        
        # Create publisher to /cmd_vel topic
        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.get_logger().info('Test Twist Publisher initialized')
        self.get_logger().info('Publishing to /cmd_vel topic')
        
    def publish_twist(self, linear_x, angular_z):
        """Publish a single Twist message"""
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.linear.y = 0.0
        msg.linear.z = 0.0
        msg.angular.x = 0.0
        msg.angular.y = 0.0
        msg.angular.z = float(angular_z)
        
        self.publisher_.publish(msg)
        self.get_logger().info(
            f'[TWIST_SENT] linear.x={linear_x:.3f}, angular.z={angular_z:.3f}'
        )
        return msg

    def test_single_message(self):
        """Test 1: Send a single Twist message"""
        self.get_logger().info('='*60)
        self.get_logger().info('TEST 1: Single Twist Message')
        self.get_logger().info('='*60)
        
        self.publish_twist(0.5, 0.2)
        
        self.get_logger().info('Waiting 2 seconds for serial transmission...')
        time.sleep(2)

    def test_multiple_messages(self):
        """Test 2: Send multiple Twist messages with different values"""
        self.get_logger().info('='*60)
        self.get_logger().info('TEST 2: Multiple Twist Messages')
        self.get_logger().info('='*60)
        
        test_cases = [
            (0.5, 0.2, "Forward with right turn"),
            (0.3, -0.3, "Forward with left turn"),
            (0.0, 0.5, "Stationary with rotation"),
            (1.0, 0.0, "Maximum forward speed"),
            (0.0, 0.0, "Stop"),
        ]
        
        for linear, angular, description in test_cases:
            self.get_logger().info(f'> Sending: {description}')
            self.publish_twist(linear, angular)
            time.sleep(1)
        
        self.get_logger().info('All messages sent, waiting...')
        time.sleep(2)

    def test_continuous_stream(self, duration=5):
        """Test 3: Send continuous stream of messages"""
        self.get_logger().info('='*60)
        self.get_logger().info(f'TEST 3: Continuous Stream ({duration}s)')
        self.get_logger().info('='*60)
        
        start_time = time.time()
        message_count = 0
        
        while (time.time() - start_time) < duration:
            # Simple circular motion pattern
            elapsed = time.time() - start_time
            linear_x = 0.5 + 0.3 * (elapsed / duration)
            angular_z = 0.3 * (1 + (elapsed / duration))
            
            self.publish_twist(linear_x, angular_z)
            message_count += 1
            time.sleep(0.1)  # ~10Hz publishing rate
        
        self.get_logger().info(f'Sent {message_count} messages in {duration}s')
        time.sleep(1)

def main():
    rclpy.init()
    
    try:
        test_node = TwistPublisherTest()
        
        print("\n" + "="*60)
        print("SERIAL_TWISTCTL NODE TEST PROGRAM")
        print("="*60)
        print("This program tests the serial_twistctl node by publishing")
        print("Twist messages to the /cmd_vel topic.")
        print("")
        print("The serial_twistctl node should:")
        print("  1. Receive the Twist messages")
        print("  2. Convert them to serial commands: vcx=X.XXX,wc=Y.YYY")
        print("  3. Send the commands to the serial port")
        print("")
        print("Commands to verify serial transmission:")
        print("  - Monitor console output of serial_twistctl_node")
        print("  - Check log files in /home/jetson/2025_FYP_ws/sys_log/Sensor_Driver_layer/twist_log/")
        print("  - Use 'cat /dev/serial_twistctl' to see raw serial data (may show garbage)")
        print("="*60 + "\n")
        
        # Run tests
        test_node.test_single_message()
        time.sleep(2)
        
        test_node.test_multiple_messages()
        time.sleep(2)
        
        test_node.test_continuous_stream(duration=5)
        time.sleep(2)
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)
        print("Check the serial_twistctl_node console output to verify:")
        print("  - [TWIST_RX] messages showing received data")
        print("  - [SERIAL_TX] messages showing sent commands")
        print("  - Byte counts for each transmission")
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        test_node.get_logger().info('Test interrupted by user')
    finally:
        test_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

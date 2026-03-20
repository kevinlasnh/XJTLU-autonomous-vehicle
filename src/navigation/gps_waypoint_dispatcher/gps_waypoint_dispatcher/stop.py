#!/usr/bin/env python3

import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Empty


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Node('gps_waypoint_cli_stop')
    publisher = node.create_publisher(Empty, '/gps_waypoint_dispatcher/stop', 10)
    message = Empty()

    for _ in range(5):
        rclpy.spin_once(node, timeout_sec=0.1)
    for _ in range(3):
        publisher.publish(message)
        rclpy.spin_once(node, timeout_sec=0.1)
        time.sleep(0.2)

    print('Published stop request')
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

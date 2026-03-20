#!/usr/bin/env python3

import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


def main(args=None) -> None:
    argv = sys.argv[1:]
    if len(argv) != 1:
        print('Usage: ros2 run gps_waypoint_dispatcher goto_name <destination_name>')
        return

    destination = argv[0]
    rclpy.init(args=args)
    node = Node('gps_waypoint_cli_name')
    publisher = node.create_publisher(String, '/gps_waypoint_dispatcher/goto_name', 10)
    message = String(data=destination)

    for _ in range(5):
        rclpy.spin_once(node, timeout_sec=0.1)
    for _ in range(3):
        publisher.publish(message)
        rclpy.spin_once(node, timeout_sec=0.1)
        time.sleep(0.2)

    print(f"Published goto_name request: {destination}")
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

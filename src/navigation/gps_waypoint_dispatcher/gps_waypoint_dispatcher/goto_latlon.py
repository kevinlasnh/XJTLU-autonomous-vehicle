#!/usr/bin/env python3

import math
import sys
import time

import rclpy
from geographic_msgs.msg import GeoPoint
from rclpy.node import Node


def main(args=None) -> None:
    argv = sys.argv[1:]
    if len(argv) < 2:
        print('Usage: ros2 run gps_waypoint_dispatcher goto_latlon <lat> <lon> [alt]')
        return

    latitude = float(argv[0])
    longitude = float(argv[1])
    altitude = float(argv[2]) if len(argv) >= 3 else math.nan

    rclpy.init(args=args)
    node = Node('gps_waypoint_cli_latlon')
    publisher = node.create_publisher(GeoPoint, '/gps_goal', 10)
    message = GeoPoint(latitude=latitude, longitude=longitude, altitude=altitude)

    for _ in range(5):
        rclpy.spin_once(node, timeout_sec=0.1)
    for _ in range(3):
        publisher.publish(message)
        rclpy.spin_once(node, timeout_sec=0.1)
        time.sleep(0.2)

    print(f'Published /gps_goal lat={latitude:.7f} lon={longitude:.7f} alt={altitude}')
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

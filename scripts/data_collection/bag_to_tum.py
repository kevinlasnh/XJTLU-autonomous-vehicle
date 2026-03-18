#!/usr/bin/env python3
import argparse
from pathlib import Path

import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message


def parse_args():
    parser = argparse.ArgumentParser(description='Export a ROS2 Odometry topic from a bag to TUM format.')
    parser.add_argument('bag_path', help='Path to rosbag2 directory')
    parser.add_argument('topic', help='Odometry topic to export, e.g. /pgo/optimized_odom')
    parser.add_argument('output', help='Output TUM file path')
    return parser.parse_args()


def main():
    args = parse_args()
    bag_path = Path(args.bag_path).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    storage_options = rosbag2_py.StorageOptions(uri=str(bag_path), storage_id='sqlite3')
    converter_options = rosbag2_py.ConverterOptions('', '')
    reader = rosbag2_py.SequentialReader()
    reader.open(storage_options, converter_options)

    topic_types = {topic.name: topic.type for topic in reader.get_all_topics_and_types()}
    if args.topic not in topic_types:
        raise SystemExit(f'Topic not found in bag: {args.topic}')

    msg_type_name = topic_types[args.topic]
    if msg_type_name != 'nav_msgs/msg/Odometry':
        raise SystemExit(f'Only nav_msgs/msg/Odometry is supported in the first version, got: {msg_type_name}')

    msg_type = get_message(msg_type_name)
    count = 0
    with output_path.open('w', encoding='utf-8') as output_file:
        while reader.has_next():
            topic_name, data, _ = reader.read_next()
            if topic_name != args.topic:
                continue

            msg = deserialize_message(data, msg_type)
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            pose = msg.pose.pose
            output_file.write(
                f'{stamp:.9f} '
                f'{pose.position.x:.9f} {pose.position.y:.9f} {pose.position.z:.9f} '
                f'{pose.orientation.x:.9f} {pose.orientation.y:.9f} {pose.orientation.z:.9f} {pose.orientation.w:.9f}\n'
            )
            count += 1

    print(f'Exported {count} poses to {output_path}')


if __name__ == '__main__':
    main()

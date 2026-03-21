#!/usr/bin/env python3
from __future__ import annotations

import math
import time
from collections import deque
from pathlib import Path as FSPath

import rclpy
import yaml
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Path as NavPath
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import NavSatFix
from std_msgs.msg import String
from tf2_ros import Buffer, TransformException, TransformListener


def default_corridor_file() -> FSPath:
    return FSPath.home() / 'fyp_runtime_data' / 'gnss' / 'two_point_corridor.yaml'


def valid_fix(msg: NavSatFix | None) -> bool:
    if msg is None:
        return False
    if msg.status.status < 0:
        return False
    if not math.isfinite(msg.latitude) or not math.isfinite(msg.longitude):
        return False
    return True


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    return radius_m * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def yaw_to_quaternion(yaw: float) -> tuple[float, float, float, float]:
    half = yaw * 0.5
    return 0.0, 0.0, math.sin(half), math.cos(half)


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


class GPSCorridorRunner(Node):
    def __init__(self) -> None:
        super().__init__('gps_corridor_runner_node')
        self.declare_parameter('corridor_file', str(default_corridor_file()))
        self.declare_parameter('route_frame', 'map')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('fix_topic', '/fix')
        self.declare_parameter('startup_wait_timeout_s', 90.0)
        self.declare_parameter('goal_reached_tolerance_m', 1.5)

        self._corridor_file = FSPath(self.get_parameter('corridor_file').value).expanduser()
        self._route_frame = str(self.get_parameter('route_frame').value)
        self._base_frame = str(self.get_parameter('base_frame').value)
        self._fix_topic = str(self.get_parameter('fix_topic').value)
        self._startup_wait_timeout_s = float(self.get_parameter('startup_wait_timeout_s').value)
        self._goal_reached_tolerance_m = float(self.get_parameter('goal_reached_tolerance_m').value)

        self._status_pub = self.create_publisher(String, '/gps_corridor/status', 10)
        self._goal_pub = self.create_publisher(PoseStamped, '/gps_corridor/goal_map', 10)
        self._path_pub = self.create_publisher(NavPath, '/gps_corridor/path_map', 10)
        self._fix_sub = self.create_subscription(NavSatFix, self._fix_topic, self._fix_callback, 10)

        self._latest_fix: NavSatFix | None = None
        self._last_fix_key: tuple | None = None

        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        self._corridor = self._load_corridor(self._corridor_file)

    def _publish_status(self, text: str) -> None:
        self.get_logger().info(text)
        self._status_pub.publish(String(data=text))

    def _fix_callback(self, msg: NavSatFix) -> None:
        self._latest_fix = msg

    def _load_corridor(self, path: FSPath) -> dict:
        if not path.exists():
            raise RuntimeError(f'corridor file not found: {path}')
        with open(path, 'r', encoding='utf-8') as corridor_file:
            data = yaml.safe_load(corridor_file) or {}
        for key in ('start_ref', 'goal_ref', 'body_vector_m'):
            if key not in data:
                raise RuntimeError(f'missing key in corridor file: {key}')
        return data

    def _sample_key(self, msg: NavSatFix) -> tuple:
        return (
            msg.header.stamp.sec,
            msg.header.stamp.nanosec,
            round(msg.latitude, 9),
            round(msg.longitude, 9),
            round(float(msg.altitude), 4),
        )

    def _wait_for_stable_fix(self) -> dict:
        sample_count = int(self._corridor.get('startup_fix_sample_count', 10))
        spread_limit = float(self._corridor.get('startup_fix_spread_max_m', 2.0))
        timeout_s = min(float(self._corridor.get('startup_fix_timeout_s', 30.0)), self._startup_wait_timeout_s)
        deadline = time.time() + timeout_s
        samples: deque[tuple[float, float, float]] = deque(maxlen=sample_count)
        self._publish_status('WAITING_FOR_STABLE_FIX')

        while rclpy.ok() and time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
            msg = self._latest_fix
            if not valid_fix(msg):
                continue
            key = self._sample_key(msg)
            if key == self._last_fix_key:
                continue
            self._last_fix_key = key
            samples.append((msg.latitude, msg.longitude, float(msg.altitude)))
            if len(samples) < sample_count:
                continue
            max_spread = 0.0
            sample_list = list(samples)
            for i in range(len(sample_list)):
                for j in range(i + 1, len(sample_list)):
                    spread = haversine_m(sample_list[i][0], sample_list[i][1], sample_list[j][0], sample_list[j][1])
                    max_spread = max(max_spread, spread)
            if max_spread > spread_limit:
                continue
            return {
                'lat': sum(sample[0] for sample in sample_list) / len(sample_list),
                'lon': sum(sample[1] for sample in sample_list) / len(sample_list),
                'alt': sum(sample[2] for sample in sample_list) / len(sample_list),
                'samples': len(sample_list),
                'spread_m': round(max_spread, 2),
            }
        raise RuntimeError('timed out waiting for stable /fix samples')

    def _wait_for_nav2(self) -> None:
        self._publish_status('WAITING_FOR_NAV2')
        deadline = time.time() + self._startup_wait_timeout_s
        while rclpy.ok() and time.time() < deadline:
            if self._nav_client.wait_for_server(timeout_sec=1.0):
                return
        raise RuntimeError('navigate_to_pose action server not available')

    def _lookup_current_pose(self) -> tuple[float, float, float]:
        deadline = time.time() + self._startup_wait_timeout_s
        self._publish_status('WAITING_FOR_MAP_TF')
        while rclpy.ok() and time.time() < deadline:
            try:
                transform = self._tf_buffer.lookup_transform(
                    self._route_frame,
                    self._base_frame,
                    Time(),
                    timeout=Duration(seconds=0.5),
                )
                translation = transform.transform.translation
                rotation = transform.transform.rotation
                yaw = quaternion_to_yaw(rotation.x, rotation.y, rotation.z, rotation.w)
                return float(translation.x), float(translation.y), yaw
            except TransformException:
                rclpy.spin_once(self, timeout_sec=0.2)
        raise RuntimeError(f'timed out waiting for TF {self._route_frame}->{self._base_frame}')

    def _validate_startup(self, startup_fix: dict) -> float:
        start_ref = self._corridor['start_ref']
        distance_m = haversine_m(
            startup_fix['lat'],
            startup_fix['lon'],
            float(start_ref['lat']),
            float(start_ref['lon']),
        )
        tolerance_m = float(self._corridor.get('startup_gps_tolerance_m', 6.0))
        self.get_logger().info(
            f"Startup fix mean lat={startup_fix['lat']:.7f} lon={startup_fix['lon']:.7f} "
            f"spread={startup_fix['spread_m']:.2f}m distance_to_start_ref={distance_m:.2f}m"
        )
        if distance_m > tolerance_m:
            raise RuntimeError(
                f'startup GPS is {distance_m:.2f}m from start_ref (limit {tolerance_m:.2f}m)'
            )
        return distance_m

    def _build_subgoals(self, x0: float, y0: float, yaw0: float) -> list[PoseStamped]:
        vector = self._corridor['body_vector_m']
        vx = float(vector['x'])
        vy = float(vector.get('y', 0.0))
        goal_x = x0 + (math.cos(yaw0) * vx - math.sin(yaw0) * vy)
        goal_y = y0 + (math.sin(yaw0) * vx + math.cos(yaw0) * vy)
        dx = goal_x - x0
        dy = goal_y - y0
        distance_m = math.hypot(dx, dy)
        segment_length_m = max(0.5, float(self._corridor.get('segment_length_m', 8.0)))
        steps = max(1, int(math.ceil(distance_m / segment_length_m)))
        heading = math.atan2(dy, dx) if distance_m > 1e-6 else yaw0
        qx, qy, qz, qw = yaw_to_quaternion(heading)
        goals: list[PoseStamped] = []
        for step in range(1, steps + 1):
            ratio = step / steps
            pose = PoseStamped()
            pose.header.frame_id = self._route_frame
            pose.pose.position.x = x0 + dx * ratio
            pose.pose.position.y = y0 + dy * ratio
            pose.pose.position.z = 0.0
            pose.pose.orientation.x = qx
            pose.pose.orientation.y = qy
            pose.pose.orientation.z = qz
            pose.pose.orientation.w = qw
            goals.append(pose)
        self.get_logger().info(
            f'Generated {len(goals)} subgoals over {distance_m:.2f}m corridor (segment_length_m={segment_length_m:.2f})'
        )
        return goals

    def _publish_path(self, goals: list[PoseStamped]) -> None:
        path = NavPath()
        path.header.frame_id = self._route_frame
        path.header.stamp = self.get_clock().now().to_msg()
        for goal in goals:
            goal.header = path.header
            path.poses.append(goal)
        self._path_pub.publish(path)
        if goals:
            self._goal_pub.publish(goals[-1])

    def _send_goal(self, pose: PoseStamped) -> int:
        goal = NavigateToPose.Goal()
        pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose = pose
        send_future = self._nav_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return GoalStatus.STATUS_ABORTED
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result()
        if result is None:
            return GoalStatus.STATUS_UNKNOWN
        return int(result.status)

    def run(self) -> bool:
        self._publish_status('INITIALIZING')
        self.get_logger().info(f'Loaded corridor file: {self._corridor_file}')
        self.get_logger().info(
            f"Corridor {self._corridor.get('corridor_name', 'unnamed')} start_ref=({self._corridor['start_ref']['lat']:.7f}, {self._corridor['start_ref']['lon']:.7f}) "
            f"goal_ref=({self._corridor['goal_ref']['lat']:.7f}, {self._corridor['goal_ref']['lon']:.7f})"
        )
        startup_fix = self._wait_for_stable_fix()
        self._validate_startup(startup_fix)
        self._wait_for_nav2()
        x0, y0, yaw0 = self._lookup_current_pose()
        self.get_logger().info(f'Start pose map frame x={x0:.2f} y={y0:.2f} yaw={math.degrees(yaw0):.1f}deg')
        goals = self._build_subgoals(x0, y0, yaw0)
        self._publish_path(goals)
        self._publish_status('RUNNING_CORRIDOR')
        for index, goal in enumerate(goals, start=1):
            self._goal_pub.publish(goal)
            self.get_logger().info(
                f'Sending subgoal {index}/{len(goals)} x={goal.pose.position.x:.2f} y={goal.pose.position.y:.2f}'
            )
            status = self._send_goal(goal)
            if status != GoalStatus.STATUS_SUCCEEDED:
                self._publish_status(f'FAILED_SUBGOAL_{index}_STATUS_{status}')
                return False
        self._publish_status('SUCCEEDED')
        return True


def main(args=None) -> None:
    rclpy.init(args=args)
    node = GPSCorridorRunner()
    ok = False
    try:
        ok = node.run()
    except KeyboardInterrupt:
        node._publish_status('INTERRUPTED')
    except Exception as exc:
        node.get_logger().error(str(exc))
        node._publish_status(f'ABORTED: {exc}')
    finally:
        node.destroy_node()
        rclpy.shutdown()
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
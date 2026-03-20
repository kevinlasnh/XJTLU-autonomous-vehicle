#!/usr/bin/env python3

import heapq
import math
from pathlib import Path
from typing import Any

import rclpy
from geographic_msgs.msg import GeoPoint
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import FollowWaypoints
from nav_msgs.msg import Path as NavPath
from pyproj import Transformer
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix
from std_msgs.msg import Empty, String
import yaml


def yaw_to_quaternion(yaw: float):
    half = yaw * 0.5
    return 0.0, 0.0, math.sin(half), math.cos(half)


def euclidean_xy(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


class GPSWaypointDispatcher(Node):
    def __init__(self) -> None:
        super().__init__('gps_waypoint_dispatcher')

        self.declare_parameter('enu_origin_lat', 31.274927)
        self.declare_parameter('enu_origin_lon', 120.737548)
        self.declare_parameter('enu_origin_alt', 0.0)
        self.declare_parameter('road_network_file', '')
        self.declare_parameter('allow_direct_fallback', False)
        self.declare_parameter('direct_segment_length_m', 20.0)
        self.declare_parameter('max_start_snap_distance_m', 50.0)
        self.declare_parameter('frame_id', 'map')

        self.origin_lat = float(self.get_parameter('enu_origin_lat').value)
        self.origin_lon = float(self.get_parameter('enu_origin_lon').value)
        self.origin_alt = float(self.get_parameter('enu_origin_alt').value)
        self.road_network_file = str(self.get_parameter('road_network_file').value)
        self.allow_direct_fallback = bool(self.get_parameter('allow_direct_fallback').value)
        self.segment_length_m = float(self.get_parameter('direct_segment_length_m').value)
        self.max_start_snap_distance_m = float(self.get_parameter('max_start_snap_distance_m').value)
        self.frame_id = str(self.get_parameter('frame_id').value)

        self.transformer = self._build_transformer()
        self.latest_gnss: NavSatFix | None = None
        self.nodes: dict[int, dict[str, Any]] = {}
        self.edges: list[tuple[int, int]] = []
        self.name_to_id: dict[str, int] = {}
        self._goal_handle = None

        self.goal_pub = self.create_publisher(PoseStamped, '/gps_waypoint_dispatcher/goal_map', 10)
        self.path_pub = self.create_publisher(NavPath, '/gps_waypoint_dispatcher/path_map', 10)

        self.create_subscription(NavSatFix, '/gnss', self._gnss_callback, 10)
        self.create_subscription(GeoPoint, '/gps_goal', self._gps_goal_callback, 10)
        self.create_subscription(String, '/gps_waypoint_dispatcher/goto_name', self._goto_name_callback, 10)
        self.create_subscription(Empty, '/gps_waypoint_dispatcher/stop', self._stop_callback, 10)

        self.nav_client = ActionClient(self, FollowWaypoints, 'follow_waypoints')
        self._load_road_network()

        self.get_logger().info(
            'GPS dispatcher ready: origin=(%.7f, %.7f, %.1f), graph_nodes=%d, graph_edges=%d'
            % (self.origin_lat, self.origin_lon, self.origin_alt, len(self.nodes), len(self.edges))
        )
        destinations = [data['name'] for _, data in sorted(self.nodes.items()) if data.get('dest')]
        if destinations:
            self.get_logger().info('Available destinations: %s' % ', '.join(destinations))

    def _build_transformer(self) -> Transformer:
        pipeline = (
            '+proj=pipeline '
            '+step +proj=cart +ellps=WGS84 '
            f'+step +proj=topocentric +ellps=WGS84 +lat_0={self.origin_lat} '
            f'+lon_0={self.origin_lon} +h_0={self.origin_alt}'
        )
        return Transformer.from_pipeline(pipeline)

    def _latlon_to_enu(self, latitude: float, longitude: float, altitude: float | None) -> tuple[float, float, float]:
        alt = self.origin_alt if altitude is None or not math.isfinite(altitude) else altitude
        x, y, z = self.transformer.transform(longitude, latitude, alt, radians=False)
        return float(x), float(y), float(z)

    def _load_road_network(self) -> None:
        self.nodes.clear()
        self.edges.clear()
        self.name_to_id.clear()

        if not self.road_network_file:
            self.get_logger().warn('road_network_file is empty; goto_name route mode is disabled')
            return

        graph_path = Path(self.road_network_file).expanduser()
        if not graph_path.exists():
            self.get_logger().warn(f'Road network file not found: {graph_path}')
            return

        with open(graph_path, 'r', encoding='utf-8') as graph_file:
            raw = yaml.safe_load(graph_file) or {}

        raw_nodes = raw.get('nodes', {})
        if isinstance(raw_nodes, list):
            iterable = []
            for item in raw_nodes:
                if isinstance(item, dict) and 'id' in item:
                    iterable.append((int(item['id']), item))
        elif isinstance(raw_nodes, dict):
            iterable = [(int(node_id), data) for node_id, data in raw_nodes.items()]
        else:
            raise ValueError('road network nodes must be a dict or list')

        for node_id, data in iterable:
            if not isinstance(data, dict):
                raise ValueError(f'road network node {node_id} must be a map')
            lat = float(data['lat'])
            lon = float(data['lon'])
            alt = float(data.get('alt', self.origin_alt))
            enu = self._latlon_to_enu(lat, lon, alt)
            node = {
                'id': node_id,
                'name': str(data.get('name', f'node_{node_id}')),
                'lat': lat,
                'lon': lon,
                'alt': alt,
                'dest': bool(data.get('dest', False)),
                'enu': enu,
            }
            self.nodes[node_id] = node
            self.name_to_id[node['name']] = node_id

        for raw_edge in raw.get('edges', []):
            if not isinstance(raw_edge, (list, tuple)) or len(raw_edge) != 2:
                raise ValueError(f'invalid edge entry: {raw_edge!r}')
            a, b = int(raw_edge[0]), int(raw_edge[1])
            if a not in self.nodes or b not in self.nodes:
                raise ValueError(f'edge references missing node: {raw_edge!r}')
            self.edges.append((a, b))

    def _gnss_callback(self, msg: NavSatFix) -> None:
        if msg.status.status < 0:
            return
        if not math.isfinite(msg.latitude) or not math.isfinite(msg.longitude):
            return
        self.latest_gnss = msg

    def _gps_goal_callback(self, msg: GeoPoint) -> None:
        self._dispatch_direct_goal(msg.latitude, msg.longitude, msg.altitude, 'topic /gps_goal')

    def _goto_name_callback(self, msg: String) -> None:
        target_name = msg.data.strip()
        if not target_name:
            self.get_logger().warn('Ignoring empty goto_name request')
            return
        self._dispatch_named_goal(target_name)

    def _stop_callback(self, _: Empty) -> None:
        self._cancel_active_goal('stop command')

    def _require_current_fix(self) -> NavSatFix | None:
        if self.latest_gnss is None:
            self.get_logger().error('No valid /gnss fix available yet')
            return None
        return self.latest_gnss

    def _dispatch_direct_goal(self, latitude: float, longitude: float, altitude: float, source: str) -> None:
        current = self._require_current_fix()
        if current is None:
            return

        start = self._latlon_to_enu(current.latitude, current.longitude, current.altitude)
        goal = self._latlon_to_enu(latitude, longitude, altitude)
        points = self._interpolate_line(start, goal)
        poses = self._poses_from_points(points)
        self.get_logger().info(
            'Dispatching direct GPS goal from %s: (%.7f, %.7f) -> ENU(%.2f, %.2f) with %d waypoints'
            % (source, latitude, longitude, goal[0], goal[1], len(poses))
        )
        self._send_waypoints(poses, f'direct:{source}')

    def _dispatch_named_goal(self, target_name: str) -> None:
        if target_name not in self.name_to_id:
            available = ', '.join(sorted(self.name_to_id)) or '(none)'
            self.get_logger().error(f"Unknown destination '{target_name}'. Available: {available}")
            return

        current = self._require_current_fix()
        if current is None:
            return

        if not self.edges:
            self.get_logger().error('Road network has no edges; goto_name route mode is unavailable')
            return

        goal_id = self.name_to_id[target_name]
        current_point = self._latlon_to_enu(current.latitude, current.longitude, current.altitude)
        route_points = self._plan_route_points(current_point, goal_id)
        if route_points is None:
            if self.allow_direct_fallback:
                goal = self.nodes[goal_id]
                self.get_logger().warn(
                    f"Route planning failed for '{target_name}', falling back to direct GPS dispatch"
                )
                self._dispatch_direct_goal(goal['lat'], goal['lon'], goal['alt'], f'fallback:{target_name}')
            return

        poses = self._poses_from_points(route_points)
        self.get_logger().info(
            "Dispatching route goal '%s' with %d poses" % (target_name, len(poses))
        )
        self._send_waypoints(poses, f'route:{target_name}')

    def _plan_route_points(self, current_point: tuple[float, float, float], goal_id: int):
        projection = self._find_best_edge_projection(current_point)
        if projection is None:
            self.get_logger().error('No valid edge projection found for current /gnss point')
            return None

        if projection['distance_to_edge'] > self.max_start_snap_distance_m:
            self.get_logger().error(
                'Current /gnss point is %.1fm away from the nearest road edge, exceeding %.1fm'
                % (projection['distance_to_edge'], self.max_start_snap_distance_m)
            )
            return None

        virtual_start = '__start__'
        adjacency: dict[Any, list[tuple[Any, float]]] = {}
        for node_id in self.nodes:
            adjacency[node_id] = []
        for a, b in self.edges:
            weight = euclidean_xy(self.nodes[a]['enu'], self.nodes[b]['enu'])
            adjacency[a].append((b, weight))
            adjacency[b].append((a, weight))
        adjacency[virtual_start] = [
            (projection['edge'][0], projection['distance_to_a']),
            (projection['edge'][1], projection['distance_to_b']),
        ]

        node_path = self._dijkstra(adjacency, virtual_start, goal_id)
        if node_path is None:
            self.get_logger().error('Dijkstra failed to find a route to the requested destination')
            return None

        route_points = [projection['projection_point']]
        for node_id in node_path[1:]:
            route_points.append(self.nodes[int(node_id)]['enu'])
        return self._dedupe_points(route_points)

    def _find_best_edge_projection(self, current_point: tuple[float, float, float]):
        best = None
        px, py = current_point[0], current_point[1]
        for a, b in self.edges:
            ax, ay, _ = self.nodes[a]['enu']
            bx, by, _ = self.nodes[b]['enu']
            abx = bx - ax
            aby = by - ay
            ab_len_sq = abx * abx + aby * aby
            if ab_len_sq <= 1e-9:
                continue
            t = ((px - ax) * abx + (py - ay) * aby) / ab_len_sq
            t = max(0.0, min(1.0, t))
            proj_x = ax + t * abx
            proj_y = ay + t * aby
            distance_to_edge = math.hypot(px - proj_x, py - proj_y)
            projection_point = (proj_x, proj_y, 0.0)
            candidate = {
                'edge': (a, b),
                'projection_point': projection_point,
                'distance_to_edge': distance_to_edge,
                'distance_to_a': math.hypot(proj_x - ax, proj_y - ay),
                'distance_to_b': math.hypot(bx - proj_x, by - proj_y),
            }
            if best is None or candidate['distance_to_edge'] < best['distance_to_edge']:
                best = candidate
        return best

    def _dijkstra(self, adjacency: dict[Any, list[tuple[Any, float]]], start: Any, goal: Any):
        queue = [(0.0, start)]
        distances = {start: 0.0}
        previous: dict[Any, Any] = {}

        while queue:
            cost, node = heapq.heappop(queue)
            if node == goal:
                break
            if cost > distances.get(node, float('inf')):
                continue
            for neighbor, weight in adjacency.get(node, []):
                next_cost = cost + weight
                if next_cost < distances.get(neighbor, float('inf')):
                    distances[neighbor] = next_cost
                    previous[neighbor] = node
                    heapq.heappush(queue, (next_cost, neighbor))

        if goal not in distances:
            return None

        path = [goal]
        node = goal
        while node != start:
            node = previous[node]
            path.append(node)
        path.reverse()
        return path

    def _interpolate_line(self, start: tuple[float, float, float], goal: tuple[float, float, float]):
        distance = euclidean_xy(start, goal)
        if distance < 1e-3:
            return [goal]
        steps = max(1, int(math.ceil(distance / self.segment_length_m)))
        points = []
        for step in range(1, steps + 1):
            ratio = step / steps
            points.append((
                start[0] + (goal[0] - start[0]) * ratio,
                start[1] + (goal[1] - start[1]) * ratio,
                start[2] + (goal[2] - start[2]) * ratio,
            ))
        return self._dedupe_points(points)

    def _dedupe_points(self, points: list[tuple[float, float, float]]):
        deduped = []
        for point in points:
            if not deduped or euclidean_xy(deduped[-1], point) > 0.05:
                deduped.append(point)
        return deduped

    def _poses_from_points(self, points: list[tuple[float, float, float]]):
        poses: list[PoseStamped] = []
        now = self.get_clock().now().to_msg()
        for idx, point in enumerate(points):
            if idx < len(points) - 1:
                yaw = math.atan2(points[idx + 1][1] - point[1], points[idx + 1][0] - point[0])
            elif len(points) > 1:
                prev = points[idx - 1]
                yaw = math.atan2(point[1] - prev[1], point[0] - prev[0])
            else:
                yaw = 0.0
            qx, qy, qz, qw = yaw_to_quaternion(yaw)
            pose = PoseStamped()
            pose.header.frame_id = self.frame_id
            pose.header.stamp = now
            pose.pose.position.x = float(point[0])
            pose.pose.position.y = float(point[1])
            pose.pose.position.z = 0.0
            pose.pose.orientation.x = qx
            pose.pose.orientation.y = qy
            pose.pose.orientation.z = qz
            pose.pose.orientation.w = qw
            poses.append(pose)
        return poses

    def _publish_debug_topics(self, poses: list[PoseStamped]) -> None:
        if not poses:
            return
        self.goal_pub.publish(poses[-1])

        path_msg = NavPath()
        path_msg.header.frame_id = self.frame_id
        path_msg.header.stamp = self.get_clock().now().to_msg()
        path_msg.poses = poses
        self.path_pub.publish(path_msg)

    def _send_waypoints(self, poses: list[PoseStamped], label: str) -> None:
        if not poses:
            self.get_logger().error(f'Refusing to dispatch empty waypoint list for {label}')
            return
        if not self.nav_client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error('FollowWaypoints action server is not available')
            return

        self._publish_debug_topics(poses)

        def send_goal() -> None:
            goal_msg = FollowWaypoints.Goal()
            goal_msg.poses = poses
            future = self.nav_client.send_goal_async(goal_msg, feedback_callback=self._feedback_callback)
            future.add_done_callback(lambda fut: self._goal_response_callback(fut, label))

        if self._goal_handle is not None:
            self.get_logger().info('Cancelling previous FollowWaypoints goal before dispatching %s' % label)
            cancel_future = self._goal_handle.cancel_goal_async()
            cancel_future.add_done_callback(lambda _: send_goal())
        else:
            send_goal()

    def _cancel_active_goal(self, reason: str) -> None:
        if self._goal_handle is None:
            self.get_logger().warn('No active FollowWaypoints goal to cancel')
            return
        future = self._goal_handle.cancel_goal_async()
        future.add_done_callback(lambda _: self.get_logger().info(f'Cancelled FollowWaypoints goal: {reason}'))
        self._goal_handle = None

    def _goal_response_callback(self, future, label: str) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error(f'FollowWaypoints goal rejected: {label}')
            self._goal_handle = None
            return
        self.get_logger().info(f'FollowWaypoints goal accepted: {label}')
        self._goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(lambda fut: self._result_callback(fut, label))

    def _feedback_callback(self, feedback_msg) -> None:
        current_waypoint = feedback_msg.feedback.current_waypoint
        self.get_logger().info(f'FollowWaypoints feedback: current_waypoint={current_waypoint}')

    def _result_callback(self, future, label: str) -> None:
        result = future.result().result
        missed = list(result.missed_waypoints)
        if missed:
            self.get_logger().warn(f'FollowWaypoints finished for {label} with missed waypoints: {missed}')
        else:
            self.get_logger().info(f'FollowWaypoints finished successfully for {label}')
        self._goal_handle = None


def main(args=None) -> None:
    rclpy.init(args=args)
    node = GPSWaypointDispatcher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('GPS waypoint dispatcher interrupted')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

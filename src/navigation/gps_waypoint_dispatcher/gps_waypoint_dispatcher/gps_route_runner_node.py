#!/usr/bin/env python3
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass
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
from std_msgs.msg import Float64MultiArray, String
from tf2_ros import Buffer, TransformException, TransformListener

from gps_waypoint_dispatcher.scene_runtime import (
    compass_heading_to_enu_yaw_deg,
    FixedENUProjector,
    default_route_file,
    haversine_m,
    normalize_angle,
    quaternion_to_yaw,
    yaw_to_quaternion,
)


def valid_fix(msg: NavSatFix | None) -> bool:
    if msg is None:
        return False
    if msg.status.status < 0:
        return False
    if not math.isfinite(msg.latitude) or not math.isfinite(msg.longitude):
        return False
    return True


@dataclass
class Alignment2D:
    theta: float
    tx: float
    ty: float
    source: str
    revision: int


@dataclass
class RouteWaypoint:
    name: str
    lat: float
    lon: float
    alt: float
    enu_x: float
    enu_y: float


class GPSRouteRunner(Node):
    def __init__(self) -> None:
        super().__init__("gps_route_runner")
        self.declare_parameter("route_file", str(default_route_file()))
        self.declare_parameter("route_frame", "map")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("fix_topic", "/fix")
        self.declare_parameter("alignment_topic", "/gps_corridor/enu_to_map")
        self.declare_parameter("startup_wait_timeout_s", 90.0)
        self.declare_parameter("enu_origin_lat", 0.0)
        self.declare_parameter("enu_origin_lon", 0.0)
        self.declare_parameter("enu_origin_alt", 0.0)
        self.declare_parameter("bootstrap_switch_distance_m", 20.0)
        self.declare_parameter("pgo_switch_min_stable_updates", 8)
        self.declare_parameter("pgo_switch_stable_window_s", 5.0)
        self.declare_parameter("pgo_switch_max_theta_spread_deg", 2.5)
        self.declare_parameter("pgo_switch_max_translation_spread_m", 2.0)
        self.declare_parameter("pgo_switch_max_bootstrap_delta_deg", 3.0)
        self.declare_parameter("pgo_switch_warn_deg", 10.0)

        self._route_file = FSPath(self.get_parameter("route_file").value).expanduser()
        self._route_frame = str(self.get_parameter("route_frame").value)
        self._base_frame = str(self.get_parameter("base_frame").value)
        self._fix_topic = str(self.get_parameter("fix_topic").value)
        self._alignment_topic = str(self.get_parameter("alignment_topic").value)
        self._startup_wait_timeout_s = float(self.get_parameter("startup_wait_timeout_s").value)
        self._enu_origin_lat = float(self.get_parameter("enu_origin_lat").value)
        self._enu_origin_lon = float(self.get_parameter("enu_origin_lon").value)
        self._enu_origin_alt = float(self.get_parameter("enu_origin_alt").value)
        self._bootstrap_switch_distance_m = float(
            self.get_parameter("bootstrap_switch_distance_m").value
        )
        self._pgo_switch_min_stable_updates = int(
            self.get_parameter("pgo_switch_min_stable_updates").value
        )
        self._pgo_switch_stable_window_s = float(
            self.get_parameter("pgo_switch_stable_window_s").value
        )
        self._pgo_switch_max_theta_spread_deg = float(
            self.get_parameter("pgo_switch_max_theta_spread_deg").value
        )
        self._pgo_switch_max_translation_spread_m = float(
            self.get_parameter("pgo_switch_max_translation_spread_m").value
        )
        self._pgo_switch_max_bootstrap_delta_deg = float(
            self.get_parameter("pgo_switch_max_bootstrap_delta_deg").value
        )
        self._pgo_switch_warn_deg = float(self.get_parameter("pgo_switch_warn_deg").value)

        self._status_pub = self.create_publisher(String, "/gps_corridor/status", 10)
        self._goal_pub = self.create_publisher(PoseStamped, "/gps_corridor/goal_map", 10)
        self._path_pub = self.create_publisher(NavPath, "/gps_corridor/path_map", 10)
        self._fix_sub = self.create_subscription(NavSatFix, self._fix_topic, self._fix_callback, 10)
        self._alignment_sub = self.create_subscription(
            Float64MultiArray, self._alignment_topic, self._alignment_callback, 10
        )

        self._latest_fix: NavSatFix | None = None
        self._last_fix_key: tuple | None = None
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._nav_client = ActionClient(self, NavigateToPose, "navigate_to_pose")

        self._projector = FixedENUProjector(
            self._enu_origin_lat, self._enu_origin_lon, self._enu_origin_alt
        )
        self._route = self._load_route(self._route_file)
        self._bootstrap_alignment: Alignment2D | None = None
        self._pgo_alignment: Alignment2D | None = None
        self._alignment_revision = 0
        self._using_pgo_alignment = False
        self._distance_since_start_m = 0.0
        self._last_pose_xy: tuple[float, float] | None = None
        self._pgo_alignment_history: deque[tuple[float, float, float, float]] = deque()
        self._last_pgo_hold_log_time = 0.0
        self._last_pgo_hold_reason = ""

    def _publish_status(self, text: str) -> None:
        self.get_logger().info(text)
        self._status_pub.publish(String(data=text))

    def _fix_callback(self, msg: NavSatFix) -> None:
        self._latest_fix = msg

    def _alignment_callback(self, msg: Float64MultiArray) -> None:
        if len(msg.data) < 4:
            return
        if msg.data[3] < 0.5:
            return

        theta, tx, ty = float(msg.data[0]), float(msg.data[1]), float(msg.data[2])
        current = self._pgo_alignment
        if (
            current is not None
            and abs(current.theta - theta) < 1e-6
            and abs(current.tx - tx) < 1e-4
            and abs(current.ty - ty) < 1e-4
        ):
            return

        self._alignment_revision += 1
        self._pgo_alignment = Alignment2D(
            theta=theta,
            tx=tx,
            ty=ty,
            source="pgo",
            revision=self._alignment_revision,
        )
        now_mono = time.monotonic()
        self._pgo_alignment_history.append((now_mono, theta, tx, ty))
        self._trim_pgo_alignment_history(now_mono)
        self.get_logger().info(
            "Received valid PGO ENU->map transform: theta=%.2fdeg tx=%.2f ty=%.2f"
            % (math.degrees(theta), tx, ty)
        )

    def _load_route(self, path: FSPath) -> dict:
        if not path.exists():
            raise RuntimeError(f"route file not found: {path}")
        with open(path, "r", encoding="utf-8") as route_file:
            data = yaml.safe_load(route_file) or {}

        for key in ("enu_origin", "start_ref", "waypoints", "launch_yaw_deg"):
            if key not in data:
                raise RuntimeError(f"missing key in route file: {key}")
        if not isinstance(data["waypoints"], list) or not data["waypoints"]:
            raise RuntimeError("route file has no waypoints")

        self._validate_origin_match(data["enu_origin"])

        start_ref = data["start_ref"]
        start_ref["lat"] = float(start_ref["lat"])
        start_ref["lon"] = float(start_ref["lon"])
        start_ref["alt"] = float(start_ref.get("alt", 0.0))
        start_ref["enu_x"], start_ref["enu_y"] = self._projector.forward(
            start_ref["lat"], start_ref["lon"]
        )

        waypoints: list[RouteWaypoint] = []
        for index, raw_waypoint in enumerate(data["waypoints"], start=1):
            lat = float(raw_waypoint["lat"])
            lon = float(raw_waypoint["lon"])
            alt = float(raw_waypoint.get("alt", 0.0))
            enu_x, enu_y = self._projector.forward(lat, lon)
            waypoints.append(
                RouteWaypoint(
                    name=str(raw_waypoint.get("name", f"wp{index}")),
                    lat=lat,
                    lon=lon,
                    alt=alt,
                    enu_x=enu_x,
                    enu_y=enu_y,
                )
            )

        data["launch_yaw_deg"] = float(data["launch_yaw_deg"])
        data["start_ref"] = start_ref
        data["waypoints"] = waypoints
        return data

    def _validate_origin_match(self, enu_origin: dict) -> None:
        route_lat = float(enu_origin["lat"])
        route_lon = float(enu_origin["lon"])
        route_alt = float(enu_origin.get("alt", 0.0))
        if abs(route_lat - self._enu_origin_lat) > 1e-7:
            raise RuntimeError(
                f"route enu_origin.lat {route_lat:.7f} != runtime {self._enu_origin_lat:.7f}"
            )
        if abs(route_lon - self._enu_origin_lon) > 1e-7:
            raise RuntimeError(
                f"route enu_origin.lon {route_lon:.7f} != runtime {self._enu_origin_lon:.7f}"
            )
        if abs(route_alt - self._enu_origin_alt) > 0.1:
            raise RuntimeError(
                f"route enu_origin.alt {route_alt:.2f} != runtime {self._enu_origin_alt:.2f}"
            )

    def _sample_key(self, msg: NavSatFix) -> tuple:
        return (
            msg.header.stamp.sec,
            msg.header.stamp.nanosec,
            round(msg.latitude, 9),
            round(msg.longitude, 9),
            round(float(msg.altitude), 4),
        )

    def _wait_for_stable_fix(self) -> dict:
        sample_count = int(self._route.get("startup_fix_sample_count", 10))
        spread_limit = float(self._route.get("startup_fix_spread_max_m", 2.0))
        route_timeout_s = float(
            self._route.get("startup_fix_timeout_s", self._startup_wait_timeout_s)
        )
        timeout_s = max(route_timeout_s, self._startup_wait_timeout_s)
        deadline = time.time() + timeout_s
        samples: deque[tuple[float, float, float]] = deque(maxlen=sample_count)
        self._publish_status("WAITING_FOR_STABLE_FIX")

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
                    spread = haversine_m(
                        sample_list[i][0],
                        sample_list[i][1],
                        sample_list[j][0],
                        sample_list[j][1],
                    )
                    max_spread = max(max_spread, spread)
            if max_spread > spread_limit:
                continue

            return {
                "lat": sum(sample[0] for sample in sample_list) / len(sample_list),
                "lon": sum(sample[1] for sample in sample_list) / len(sample_list),
                "alt": sum(sample[2] for sample in sample_list) / len(sample_list),
                "samples": len(sample_list),
                "spread_m": round(max_spread, 2),
            }

        raise RuntimeError("timed out waiting for stable /fix samples")

    def _validate_startup(self, startup_fix: dict) -> float:
        start_ref = self._route["start_ref"]
        distance_m = haversine_m(
            startup_fix["lat"],
            startup_fix["lon"],
            start_ref["lat"],
            start_ref["lon"],
        )
        tolerance_m = float(self._route.get("startup_gps_tolerance_m", 15.0))
        self.get_logger().info(
            "Startup fix mean lat=%.7f lon=%.7f spread=%.2fm distance_to_start_ref=%.2fm"
            % (
                startup_fix["lat"],
                startup_fix["lon"],
                startup_fix["spread_m"],
                distance_m,
            )
        )
        if distance_m > tolerance_m:
            raise RuntimeError(
                f"startup GPS is {distance_m:.2f}m from start_ref (limit {tolerance_m:.2f}m)"
            )
        return distance_m

    def _wait_for_nav2(self) -> None:
        self._publish_status("WAITING_FOR_NAV2")
        deadline = time.time() + self._startup_wait_timeout_s
        while rclpy.ok() and time.time() < deadline:
            if self._nav_client.wait_for_server(timeout_sec=1.0):
                return
        raise RuntimeError("navigate_to_pose action server not available")

    def _lookup_current_pose(self) -> tuple[float, float, float]:
        deadline = time.time() + self._startup_wait_timeout_s
        self._publish_status("WAITING_FOR_MAP_TF")
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
        raise RuntimeError(f"timed out waiting for TF {self._route_frame}->{self._base_frame}")

    def _build_bootstrap_alignment(self, x0: float, y0: float, yaw0: float) -> Alignment2D:
        launch_yaw_rad = math.radians(
            compass_heading_to_enu_yaw_deg(float(self._route["launch_yaw_deg"]))
        )
        theta = normalize_angle(yaw0 - launch_yaw_rad)
        start_ref = self._route["start_ref"]
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        tx = x0 - (cos_theta * start_ref["enu_x"] - sin_theta * start_ref["enu_y"])
        ty = y0 - (sin_theta * start_ref["enu_x"] + cos_theta * start_ref["enu_y"])
        self._alignment_revision += 1
        return Alignment2D(theta=theta, tx=tx, ty=ty, source="bootstrap", revision=self._alignment_revision)

    def _trim_pgo_alignment_history(self, now_mono: float | None = None) -> None:
        if now_mono is None:
            now_mono = time.monotonic()
        while (
            self._pgo_alignment_history
            and now_mono - self._pgo_alignment_history[0][0] > self._pgo_switch_stable_window_s
        ):
            self._pgo_alignment_history.popleft()

    def _maybe_log_pgo_hold(self, reason: str) -> None:
        now_mono = time.monotonic()
        if (
            reason != self._last_pgo_hold_reason
            or now_mono - self._last_pgo_hold_log_time >= 5.0
        ):
            self.get_logger().info("Holding bootstrap alignment: %s" % reason)
            self._last_pgo_hold_reason = reason
            self._last_pgo_hold_log_time = now_mono

    def _pgo_switch_ready(self) -> tuple[bool, str]:
        if self._pgo_alignment is None:
            return False, "PGO alignment not ready yet"
        if self._distance_since_start_m < self._bootstrap_switch_distance_m:
            return (
                False,
                "distance %.1fm < switch threshold %.1fm"
                % (self._distance_since_start_m, self._bootstrap_switch_distance_m),
            )

        self._trim_pgo_alignment_history()
        history = list(self._pgo_alignment_history)
        if len(history) < self._pgo_switch_min_stable_updates:
            return (
                False,
                "have %d/%d recent PGO updates"
                % (len(history), self._pgo_switch_min_stable_updates),
            )

        latest_theta = history[-1][1]
        theta_offsets_deg = [
            math.degrees(normalize_angle(theta_i - latest_theta))
            for _, theta_i, _, _ in history
        ]
        theta_spread_deg = max(theta_offsets_deg) - min(theta_offsets_deg)
        tx_values = [tx_i for _, _, tx_i, _ in history]
        ty_values = [ty_i for _, _, _, ty_i in history]
        translation_spread_m = math.hypot(
            max(tx_values) - min(tx_values),
            max(ty_values) - min(ty_values),
        )
        bootstrap_delta_deg = abs(
            math.degrees(
                normalize_angle(self._pgo_alignment.theta - self._bootstrap_alignment.theta)
            )
        )

        if theta_spread_deg > self._pgo_switch_max_theta_spread_deg:
            return (
                False,
                "theta spread %.2fdeg > %.2fdeg"
                % (theta_spread_deg, self._pgo_switch_max_theta_spread_deg),
            )
        if translation_spread_m > self._pgo_switch_max_translation_spread_m:
            return (
                False,
                "translation spread %.2fm > %.2fm"
                % (translation_spread_m, self._pgo_switch_max_translation_spread_m),
            )
        if bootstrap_delta_deg > self._pgo_switch_max_bootstrap_delta_deg:
            return (
                False,
                "bootstrap delta %.2fdeg > %.2fdeg"
                % (bootstrap_delta_deg, self._pgo_switch_max_bootstrap_delta_deg),
            )

        return (
            True,
            "stable over %d updates: theta spread %.2fdeg translation spread %.2fm bootstrap delta %.2fdeg"
            % (
                len(history),
                theta_spread_deg,
                translation_spread_m,
                bootstrap_delta_deg,
            ),
        )

    def _best_alignment(self, allow_switch: bool = True) -> Alignment2D:
        if self._bootstrap_alignment is None:
            raise RuntimeError("bootstrap alignment not initialized")

        if self._using_pgo_alignment:
            if self._pgo_alignment is not None:
                return self._pgo_alignment
            return self._bootstrap_alignment

        if allow_switch:
            ready, reason = self._pgo_switch_ready()
            if ready and self._pgo_alignment is not None:
                delta_deg = abs(
                    math.degrees(
                        normalize_angle(self._pgo_alignment.theta - self._bootstrap_alignment.theta)
                    )
                )
                if delta_deg > self._pgo_switch_warn_deg:
                    self.get_logger().warn(
                        "PGO/bootstrap rotation delta is %.1fdeg; launch heading may be wrong" % delta_deg
                    )
                self.get_logger().info("Switching to PGO alignment: %s" % reason)
                self._using_pgo_alignment = True
                self._publish_status("SWITCHED_TO_PGO_ALIGNMENT")
                return self._pgo_alignment
            if not self._using_pgo_alignment:
                self._maybe_log_pgo_hold(reason)

        return self._bootstrap_alignment

    def _enu_to_map(self, enu_x: float, enu_y: float, alignment: Alignment2D) -> tuple[float, float]:
        cos_theta = math.cos(alignment.theta)
        sin_theta = math.sin(alignment.theta)
        map_x = cos_theta * enu_x - sin_theta * enu_y + alignment.tx
        map_y = sin_theta * enu_x + cos_theta * enu_y + alignment.ty
        return map_x, map_y

    def _route_waypoint_to_map(self, waypoint: RouteWaypoint, alignment: Alignment2D) -> tuple[float, float]:
        return self._enu_to_map(waypoint.enu_x, waypoint.enu_y, alignment)

    def _build_subgoals(
        self,
        start_xy: tuple[float, float],
        target_xy: tuple[float, float],
        segment_length_m: float,
    ) -> list[PoseStamped]:
        x0, y0 = start_xy
        x1, y1 = target_xy
        dx = x1 - x0
        dy = y1 - y0
        distance_m = math.hypot(dx, dy)
        if distance_m < 1e-3:
            return []

        steps = max(1, int(math.ceil(distance_m / max(0.5, segment_length_m))))
        heading = math.atan2(dy, dx)
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
        return goals

    def _append_segment(self, path: NavPath, start_xy: tuple[float, float], target_xy: tuple[float, float], segment_length_m: float) -> None:
        subgoals = self._build_subgoals(start_xy, target_xy, segment_length_m)
        if not subgoals:
            return
        stamp = path.header.stamp
        for goal in subgoals:
            goal.header.stamp = stamp
            path.poses.append(goal)

    def _publish_remaining_path(self, current_xy: tuple[float, float], waypoint_index: int, alignment: Alignment2D) -> None:
        path = NavPath()
        path.header.frame_id = self._route_frame
        path.header.stamp = self.get_clock().now().to_msg()
        segment_length_m = float(self._route.get("segment_length_m", 8.0))

        current_start = current_xy
        for index in range(waypoint_index, len(self._route["waypoints"])):
            waypoint = self._route["waypoints"][index]
            target_xy = self._route_waypoint_to_map(waypoint, alignment)
            self._append_segment(path, current_start, target_xy, segment_length_m)
            current_start = target_xy

        self._path_pub.publish(path)
        if path.poses:
            self._goal_pub.publish(path.poses[0])

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

    def _current_xy(self) -> tuple[float, float]:
        x, y, _ = self._lookup_current_pose()
        return x, y

    def _update_distance_since_start(self, xy: tuple[float, float]) -> None:
        if self._last_pose_xy is None:
            self._last_pose_xy = xy
            return
        self._distance_since_start_m += math.hypot(
            xy[0] - self._last_pose_xy[0], xy[1] - self._last_pose_xy[1]
        )
        self._last_pose_xy = xy

    def _run_waypoint(self, waypoint_index: int) -> tuple[bool, tuple[float, float]]:
        waypoint = self._route["waypoints"][waypoint_index]
        current_xy = self._current_xy()
        self._update_distance_since_start(current_xy)

        while rclpy.ok():
            # Freeze the alignment for the entire waypoint so Nav2 does not chase a moving target.
            alignment = self._best_alignment(allow_switch=True)
            target_xy = self._route_waypoint_to_map(waypoint, alignment)
            subgoals = self._build_subgoals(
                current_xy,
                target_xy,
                float(self._route.get("segment_length_m", 8.0)),
            )
            self._publish_remaining_path(current_xy, waypoint_index, alignment)

            if not subgoals:
                return True, current_xy

            for subgoal_index, subgoal in enumerate(subgoals, start=1):
                self._publish_status(
                    "NAVIGATING_SUBGOAL|%s|%d|%d|%.2f|%.2f|%s"
                    % (
                        waypoint.name,
                        subgoal_index,
                        len(subgoals),
                        subgoal.pose.position.x,
                        subgoal.pose.position.y,
                        alignment.source,
                    )
                )
                self._goal_pub.publish(subgoal)
                self.get_logger().info(
                    "Sending %s subgoal %d/%d x=%.2f y=%.2f source=%s"
                    % (
                        waypoint.name,
                        subgoal_index,
                        len(subgoals),
                        subgoal.pose.position.x,
                        subgoal.pose.position.y,
                        alignment.source,
                    )
                )
                status = self._send_goal(subgoal)
                if status != GoalStatus.STATUS_SUCCEEDED:
                    self._publish_status(
                        f"FAILED_WAYPOINT_{waypoint.name}_SUBGOAL_{subgoal_index}_STATUS_{status}"
                    )
                    return False, current_xy

                current_xy = self._current_xy()
                self._update_distance_since_start(current_xy)

            return True, current_xy

        return False, current_xy

    def run(self) -> bool:
        self._publish_status("INITIALIZING")
        self.get_logger().info(f"Loaded route file: {self._route_file}")
        self.get_logger().info(
            "Route %s with %d waypoints"
            % (self._route.get("route_name", "unnamed_route"), len(self._route["waypoints"]))
        )

        startup_fix = self._wait_for_stable_fix()
        self._validate_startup(startup_fix)
        self._wait_for_nav2()
        x0, y0, yaw0 = self._lookup_current_pose()
        self._bootstrap_alignment = self._build_bootstrap_alignment(x0, y0, yaw0)
        self._last_pose_xy = (x0, y0)

        self.get_logger().info(
            "Bootstrap ENU->map ready: yaw0=%.2fdeg launch_yaw=%.2fdeg theta=%.2fdeg"
            % (
                math.degrees(yaw0),
                float(self._route["launch_yaw_deg"]),
                math.degrees(self._bootstrap_alignment.theta),
            )
        )
        self._publish_status("BOOTSTRAP_READY")
        self._publish_status("RUNNING_ROUTE")

        current_xy = (x0, y0)
        for waypoint_index, waypoint in enumerate(self._route["waypoints"]):
            self._publish_status(
                "WAYPOINT_TARGET|%d|%d|%s"
                % (waypoint_index + 1, len(self._route["waypoints"]), waypoint.name)
            )
            self.get_logger().info(
                "Navigating to waypoint %d/%d: %s"
                % (waypoint_index + 1, len(self._route["waypoints"]), waypoint.name)
            )
            ok, current_xy = self._run_waypoint(waypoint_index)
            if not ok:
                return False
            self._publish_status(
                "WAYPOINT_REACHED|%d|%d|%s"
                % (waypoint_index + 1, len(self._route["waypoints"]), waypoint.name)
            )

        self._publish_status("SUCCEEDED")
        return True


def main(args=None) -> None:
    rclpy.init(args=args)
    node = GPSRouteRunner()
    ok = False
    try:
        ok = node.run()
    except KeyboardInterrupt:
        node._publish_status("INTERRUPTED")
    except Exception as exc:
        node.get_logger().error(str(exc))
        node._publish_status(f"ABORTED: {exc}")
    finally:
        node.destroy_node()
        rclpy.shutdown()
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()

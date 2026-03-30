#!/usr/bin/env python3

import math
import os
from collections import deque
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix
import yaml


def get_runtime_root() -> Path:
    runtime_root = os.environ.get("FYP_RUNTIME_ROOT")
    if runtime_root:
        return Path(runtime_root).expanduser()
    return Path.home() / "XJTLU-autonomous-vehicle/runtime-data"


def get_runtime_path(*parts: str) -> Path:
    return get_runtime_root().joinpath(*parts)


def get_session_log_path(filename: str, fallback_subdir: str) -> str:
    session_dir = os.environ.get("FYP_LOG_SESSION_DIR")
    if session_dir:
        os.makedirs(session_dir, exist_ok=True)
        return str(Path(session_dir) / filename)

    log_dir = get_runtime_path(fallback_subdir)
    os.makedirs(log_dir, exist_ok=True)
    now = datetime.now()
    return str(Path(log_dir) / f"log_{now.strftime('%Y%m%d_%H%M%S')}.txt")


LOG_SWITCH_PATH = get_runtime_path("config", "log_switch.yaml")
OFFSET_FILE_PATH = get_runtime_path("gnss", "gnss_offset.txt")
START_ID_FILE_PATH = get_runtime_path("gnss", "startid.txt")

CALIBRATION_TIMES = 5
STABILITY_THRESHOLD_M = 1.0


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


def load_calibration_points(config_path: Path) -> dict[int, tuple[float, float, str]]:
    if not config_path.exists():
        raise FileNotFoundError(f"Calibration points file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file) or {}

    raw_points = config.get("points")
    if not isinstance(raw_points, dict) or not raw_points:
        raise ValueError(f"Calibration points file has no valid 'points' map: {config_path}")

    parsed_points: dict[int, tuple[float, float, str]] = {}
    for raw_id, raw_point in raw_points.items():
        point_id = int(raw_id)
        if not isinstance(raw_point, dict):
            raise ValueError(f"Calibration point {raw_id} must be a map")

        lat = float(raw_point["lat"])
        lon = float(raw_point["lon"])
        name = str(raw_point.get("name", f"point_{point_id}"))
        if not math.isfinite(lat) or not math.isfinite(lon):
            raise ValueError(f"Calibration point {raw_id} contains non-finite coordinates")

        parsed_points[point_id] = (lat, lon, name)

    return parsed_points


class GnssCalibrationNode(Node):
    def __init__(self) -> None:
        super().__init__("gnss_calibration_node")

        self.declare_parameter("calibration_points_file", "")
        config_path_str = self.get_parameter("calibration_points_file").get_parameter_value().string_value
        if not config_path_str:
            raise RuntimeError("Parameter 'calibration_points_file' is required")

        self.calibration_points = load_calibration_points(Path(config_path_str).expanduser())
        self.selected_point = self._read_selected_point()
        self.ref_lat, self.ref_lon, location_name = self.calibration_points[self.selected_point]

        self.subscription = self.create_subscription(NavSatFix, "/fix", self.listener_callback, 10)
        self.publisher_ = self.create_publisher(NavSatFix, "gnss", 10)
        self.latest_valid_data: NavSatFix | None = None
        self.lat_offset = float("nan")
        self.lon_offset = float("nan")
        self.calibration_done = False
        self.gnss_data_queue: deque[tuple[float, float]] = deque(maxlen=CALIBRATION_TIMES)
        self.calibration_attempts = 0
        self._missing_offset_logged = False

        enable_log = self.should_enable_logging("gnss_calibration_node")
        if enable_log:
            self.log_path = get_session_log_path("gnss_calibration.log", "logs/gnss_calibration")
            self.get_logger().info(f"Logging enabled: {self.log_path}")
        else:
            self.log_path = None
            self.get_logger().info("Logging disabled by config")

        self.get_logger().info(
            f"Loaded {len(self.calibration_points)} calibration points from {config_path_str}"
        )
        self.get_logger().info(
            f"Start point {self.selected_point}: {location_name} "
            f"({self.ref_lat:.7f}, {self.ref_lon:.7f})"
        )

        loaded_offsets = self.load_offsets(log_missing=False)
        if loaded_offsets is None:
            self.get_logger().warn(
                f"No valid GNSS offset at {OFFSET_FILE_PATH}. /gnss will remain unavailable "
                "until live calibration succeeds."
            )
        else:
            self.get_logger().info(
                f"Found existing GNSS offset at {OFFSET_FILE_PATH}; it will be refreshed after calibration."
            )

    def should_enable_logging(self, node_key: str) -> bool:
        try:
            with open(LOG_SWITCH_PATH, "r", encoding="utf-8") as config_file:
                config = yaml.safe_load(config_file) or {}
            if node_key in config:
                return config[node_key].get("enable_logging", True)
            self.get_logger().warn(f"No logging config found for '{node_key}', enabling by default")
            return True
        except Exception as exc:
            self.get_logger().error(f"Failed to read log config: {exc}")
            return True

    def _read_selected_point(self) -> int:
        if not START_ID_FILE_PATH.exists():
            raise FileNotFoundError(f"Missing startid file: {START_ID_FILE_PATH}")

        raw_value = START_ID_FILE_PATH.read_text(encoding="utf-8").strip()
        try:
            point_id = int(raw_value)
        except ValueError as exc:
            raise ValueError(f"Invalid startid '{raw_value}' in {START_ID_FILE_PATH}") from exc

        if point_id not in self.calibration_points:
            valid_ids = ", ".join(str(pid) for pid in sorted(self.calibration_points))
            raise ValueError(
                f"startid {point_id} is not defined in calibration_points_file; valid ids: {valid_ids}"
            )
        return point_id

    def listener_callback(self, msg: NavSatFix) -> None:
        if msg.status.status < 0:
            self.get_logger().warn("GNSS status indicates no fix, skipping sample")
            return

        if not all(math.isfinite(value) for value in (msg.latitude, msg.longitude, msg.altitude)):
            self.get_logger().warn("Invalid GNSS sample (non-finite lat/lon/alt), skipping sample")
            return

        if msg.latitude == 0.0 and msg.longitude == 0.0:
            self.get_logger().warn("Invalid GNSS data (zero lat/lon), skipping sample")
            return

        if msg.position_covariance_type == NavSatFix.COVARIANCE_TYPE_UNKNOWN:
            self.get_logger().warn("GNSS covariance type unknown, skipping sample")
            return

        if not self.calibration_done:
            self.gnss_data_queue.append((msg.latitude, msg.longitude))
            progress = len(self.gnss_data_queue)
            self.get_logger().info(f"Calibrating... freeze! {progress}/{CALIBRATION_TIMES}")

            if len(self.gnss_data_queue) < CALIBRATION_TIMES:
                return

            if self.is_data_stable():
                avg_lat = sum(lat for lat, _ in self.gnss_data_queue) / CALIBRATION_TIMES
                avg_lon = sum(lon for _, lon in self.gnss_data_queue) / CALIBRATION_TIMES
                self.lat_offset = self.ref_lat - avg_lat
                self.lon_offset = self.ref_lon - avg_lon
                self.calibration_done = True
                self.save_offsets()
                self.get_logger().info(
                    f"Calibrated: lat_offset={self.lat_offset:.10f}, lon_offset={self.lon_offset:.10f}"
                )
            else:
                self.gnss_data_queue.clear()
                self.calibration_attempts += 1
                self.get_logger().warn(
                    "Calibration attempt %d failed: GNSS samples spread exceeds %.1fm, restarting calibration"
                    % (self.calibration_attempts, STABILITY_THRESHOLD_M)
                )
                return

        self.latest_valid_data = msg
        self.publish_calibrated_data()

    def save_offsets(self) -> None:
        if not math.isfinite(self.lat_offset) or not math.isfinite(self.lon_offset):
            self.get_logger().error("Refusing to save non-finite GNSS offsets")
            return

        OFFSET_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OFFSET_FILE_PATH, "w", encoding="utf-8") as offset_file:
            offset_file.write(f"{self.lat_offset}\n{self.lon_offset}\n")
        self.get_logger().info(f"Offset saved at {OFFSET_FILE_PATH}")
        self._missing_offset_logged = False

    def load_offsets(self, log_missing: bool = True):
        if not OFFSET_FILE_PATH.exists():
            if log_missing and not self._missing_offset_logged:
                self.get_logger().error(
                    f"Missing valid GNSS offset file: {OFFSET_FILE_PATH}. /gnss publication is blocked until calibration succeeds."
                )
                self._missing_offset_logged = True
            return None

        try:
            lines = OFFSET_FILE_PATH.read_text(encoding="utf-8").splitlines()
            if len(lines) != 2:
                raise ValueError("offset file must contain exactly two lines")
            lat_offset = float(lines[0].strip())
            lon_offset = float(lines[1].strip())
        except Exception as exc:
            if log_missing and not self._missing_offset_logged:
                self.get_logger().error(f"Failed to load GNSS offsets from {OFFSET_FILE_PATH}: {exc}")
                self._missing_offset_logged = True
            return None

        if not math.isfinite(lat_offset) or not math.isfinite(lon_offset):
            if log_missing and not self._missing_offset_logged:
                self.get_logger().error(
                    f"GNSS offset file contains non-finite values: {OFFSET_FILE_PATH}. /gnss publication is blocked."
                )
                self._missing_offset_logged = True
            return None

        return lat_offset, lon_offset

    def is_data_stable(self) -> bool:
        if len(self.gnss_data_queue) < CALIBRATION_TIMES:
            return False

        center_lat, center_lon = self.gnss_data_queue[0]
        for lat, lon in self.gnss_data_queue:
            if haversine_m(center_lat, center_lon, lat, lon) > STABILITY_THRESHOLD_M:
                return False
        return True

    def publish_calibrated_data(self) -> None:
        if self.latest_valid_data is None:
            return

        loaded_offsets = self.load_offsets(log_missing=True)
        if loaded_offsets is None:
            if math.isfinite(self.lat_offset) and math.isfinite(self.lon_offset):
                loaded_lat_offset, loaded_lon_offset = self.lat_offset, self.lon_offset
            else:
                return
        else:
            loaded_lat_offset, loaded_lon_offset = loaded_offsets

        calibrated_msg = NavSatFix()
        calibrated_msg.header = self.latest_valid_data.header
        calibrated_msg.status = self.latest_valid_data.status
        calibrated_msg.latitude = self.latest_valid_data.latitude + loaded_lat_offset
        calibrated_msg.longitude = self.latest_valid_data.longitude + loaded_lon_offset
        calibrated_msg.altitude = self.latest_valid_data.altitude
        calibrated_msg.position_covariance = self.latest_valid_data.position_covariance
        calibrated_msg.position_covariance_type = self.latest_valid_data.position_covariance_type
        self.publisher_.publish(calibrated_msg)

        ros_timestamp = self.get_clock().now().nanoseconds
        readable_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = (
            f"ROS_timestamp: {ros_timestamp}, Readable_time: [{readable_time}], "
            f"Lat_calibrated: {calibrated_msg.latitude:.10f}, "
            f"Lon_calibrated: {calibrated_msg.longitude:.10f}\n"
        )
        if self.log_path:
            try:
                with open(self.log_path, "a", encoding="utf-8") as log_file:
                    log_file.write(log_entry)
            except Exception as exc:
                self.get_logger().error(f"Failed to write GNSS log file: {exc}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = GnssCalibrationNode()
        rclpy.spin(node)
    except Exception as exc:
        print(f"GNSS calibration startup failed: {exc}")
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

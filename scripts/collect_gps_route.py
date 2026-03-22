#!/usr/bin/env python3
from __future__ import annotations

import math
import os
import shutil
import signal
import subprocess
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import TextIO

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix
import yaml

OUTPUT_DIR = Path.home() / "fyp_runtime_data" / "gnss"
OUTPUT_FILE = OUTPUT_DIR / "current_route.yaml"
REPO_ROOT = Path.home() / "fyp_autonomous_vehicle"
MASTER_PARAMS_FILE = REPO_ROOT / "src" / "bringup" / "config" / "master_params.yaml"
GNSS_DRIVER_LOG = OUTPUT_DIR / "collect_gps_route_nmea.log"
SAMPLE_COUNT = 10
STABILITY_THRESHOLD_M = 2.0
SAMPLE_TIMEOUT_S = 30.0
SEGMENT_LENGTH_M = 8.0
STARTUP_GPS_TOLERANCE_M = 6.0
FIX_TOPIC_DETECT_TIMEOUT_S = 3.0
DRIVER_STARTUP_TIMEOUT_S = 10.0
SHORT_BASELINE_WARN_M = 5.0


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(
        math.radians(lat1)
    ) * math.cos(math.radians(lat2)) * math.cos(math.radians(lon2 - lon1))
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


class FixCollector(Node):
    def __init__(self) -> None:
        super().__init__("gps_route_collector")
        self.latest_fix: NavSatFix | None = None
        self.last_fix_key: tuple | None = None
        self.create_subscription(NavSatFix, "/fix", self._callback, 10)
        self.get_logger().info("Waiting for /fix ...")

    def _callback(self, msg: NavSatFix) -> None:
        self.latest_fix = msg


def wait_for_fix_stream(node: FixCollector, timeout_s: float) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        rclpy.spin_once(node, timeout_sec=0.2)
        if node.latest_fix is not None:
            return True
    return False


def start_gnss_driver() -> tuple[subprocess.Popen[str], TextIO]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = open(GNSS_DRIVER_LOG, "w", encoding="utf-8")
    process = subprocess.Popen(
        [
            "ros2",
            "launch",
            "nmea_navsat_driver",
            "nmea_serial_driver.launch.py",
            f"params_file:={MASTER_PARAMS_FILE}",
        ],
        cwd=str(REPO_ROOT),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid,
        text=True,
    )
    return process, log_handle


def stop_gnss_driver(process: subprocess.Popen[str] | None, log_handle: TextIO | None) -> None:
    if process is not None and process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5.0)
    if log_handle is not None:
        log_handle.close()


def ensure_fix_stream(node: FixCollector) -> tuple[subprocess.Popen[str] | None, TextIO | None]:
    print("\nChecking /fix stream ...")
    if wait_for_fix_stream(node, FIX_TOPIC_DETECT_TIMEOUT_S):
        print("Using existing /fix publisher.")
        return None, None

    print("No /fix detected. Starting GNSS driver in background ...")
    process, log_handle = start_gnss_driver()
    if wait_for_fix_stream(node, DRIVER_STARTUP_TIMEOUT_S):
        print(f"/fix detected after starting GNSS driver. Driver log: {GNSS_DRIVER_LOG}")
        return process, log_handle

    stop_gnss_driver(process, log_handle)
    raise RuntimeError(
        "failed to start GNSS driver or detect /fix stream; "
        f"check {GNSS_DRIVER_LOG}"
    )


def collect_fix_samples(node: FixCollector, label: str) -> dict:
    deadline = time.time() + SAMPLE_TIMEOUT_S
    samples: deque[tuple[float, float, float]] = deque(maxlen=SAMPLE_COUNT)
    print(f"\n[{label}] collecting {SAMPLE_COUNT} stable /fix samples ... keep the vehicle still.")
    while time.time() < deadline:
        rclpy.spin_once(node, timeout_sec=0.2)
        msg = node.latest_fix
        if not valid_fix(msg):
            continue
        key = (
            msg.header.stamp.sec,
            msg.header.stamp.nanosec,
            round(msg.latitude, 9),
            round(msg.longitude, 9),
            round(float(msg.altitude), 4),
        )
        if key == node.last_fix_key:
            continue
        node.last_fix_key = key
        samples.append((msg.latitude, msg.longitude, float(msg.altitude)))
        if len(samples) < SAMPLE_COUNT:
            continue

        max_spread = 0.0
        sample_list = list(samples)
        for i in range(len(sample_list)):
            for j in range(i + 1, len(sample_list)):
                max_spread = max(
                    max_spread,
                    haversine_m(
                        sample_list[i][0],
                        sample_list[i][1],
                        sample_list[j][0],
                        sample_list[j][1],
                    ),
                )
        if max_spread > STABILITY_THRESHOLD_M:
            continue

        result = {
            "lat": sum(sample[0] for sample in sample_list) / len(sample_list),
            "lon": sum(sample[1] for sample in sample_list) / len(sample_list),
            "alt": sum(sample[2] for sample in sample_list) / len(sample_list),
            "samples": len(sample_list),
            "spread_m": round(max_spread, 2),
            "source": "/fix",
            "collected_at": now_str(),
        }
        print(
            f"[{label}] lat={result['lat']:.7f} lon={result['lon']:.7f} alt={result['alt']:.2f} spread={result['spread_m']:.2f}m"
        )
        return result

    raise RuntimeError(f"timed out collecting stable /fix for {label}")


def load_fixed_origin() -> dict:
    with open(MASTER_PARAMS_FILE, "r", encoding="utf-8") as params_file:
        data = yaml.safe_load(params_file) or {}

    pgo_params = data.get("/pgo", {}).get("pgo_node", {}).get("ros__parameters", {})
    if "gps.origin_lat" in pgo_params and "gps.origin_lon" in pgo_params:
        return {
            "lat": float(pgo_params["gps.origin_lat"]),
            "lon": float(pgo_params["gps.origin_lon"]),
            "alt": float(pgo_params.get("gps.origin_alt", 0.0)),
        }

    dispatcher_params = data.get("/gps_waypoint_dispatcher", {}).get("ros__parameters", {})
    if "enu_origin_lat" in dispatcher_params and "enu_origin_lon" in dispatcher_params:
        return {
            "lat": float(dispatcher_params["enu_origin_lat"]),
            "lon": float(dispatcher_params["enu_origin_lon"]),
            "alt": float(dispatcher_params.get("enu_origin_alt", 0.0)),
        }

    raise RuntimeError(f"failed to find fixed ENU origin in {MASTER_PARAMS_FILE}")


def backup_existing_file() -> None:
    if not OUTPUT_FILE.exists():
        return
    backup = OUTPUT_FILE.with_name(f"route_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
    shutil.move(str(OUTPUT_FILE), str(backup))
    print(f"Backed up existing route file to: {backup}")


def confirm_launch_yaw(start_ref: dict, first_waypoint: dict) -> float:
    baseline_m = haversine_m(
        start_ref["lat"],
        start_ref["lon"],
        first_waypoint["lat"],
        first_waypoint["lon"],
    )
    suggestion = bearing_deg(
        start_ref["lat"],
        start_ref["lon"],
        first_waypoint["lat"],
        first_waypoint["lon"],
    )

    if baseline_m < SHORT_BASELINE_WARN_M:
        print(
            f"\nFirst segment is only {baseline_m:.2f}m. "
            "GPS bearing is too noisy for silent launch_yaw inference."
        )
        while True:
            raw = input("Enter launch_yaw_deg manually (ENU heading, degrees): ").strip()
            try:
                return float(raw) % 360.0
            except ValueError:
                print("Please enter a valid number.")

    print(f"\nSuggested launch_yaw_deg from START -> first waypoint: {suggestion:.2f} deg")
    print("Press Enter to accept, or type a custom value if the measured launch heading is different.")
    while True:
        raw = input("launch_yaw_deg: ").strip()
        if not raw:
            return suggestion
        try:
            return float(raw) % 360.0
        except ValueError:
            print("Please enter a valid number.")


def maybe_override_launch_yaw(current_value: float) -> float:
    raw = input(
        f"Final launch_yaw_deg [{current_value:.2f}] (Enter to keep, or type a new value): "
    ).strip()
    if not raw:
        return current_value
    try:
        return float(raw) % 360.0
    except ValueError:
        print("Invalid value, keeping previous launch_yaw_deg.")
        return current_value


def main(args=None) -> None:
    route_name = input("Route name [gps_route]: ").strip() or "gps_route"
    print("\nThis collector assumes:")
    print("- launch pose is physically fixed")
    print("- launch heading is physically fixed")
    print("- you will provide or confirm launch_yaw_deg explicitly")
    input("\nPlace vehicle at the fixed launch pose, then press Enter to sample START_REF ...")

    fixed_origin = load_fixed_origin()

    rclpy.init(args=args)
    node = FixCollector()
    gnss_process: subprocess.Popen[str] | None = None
    gnss_log_handle: TextIO | None = None
    try:
        gnss_process, gnss_log_handle = ensure_fix_stream(node)
        start_ref = collect_fix_samples(node, "START_REF")

        waypoints: list[dict] = []
        launch_yaw_deg: float | None = None
        waypoint_index = 1

        while True:
            default_name = "goal" if waypoint_index == 1 else f"wp{waypoint_index}"
            name = input(f"\nWaypoint name [{default_name}]: ").strip() or default_name
            input(f"Move vehicle to {name}, then press Enter to sample ...")
            waypoint = collect_fix_samples(node, name)
            waypoint["name"] = name
            waypoints.append(waypoint)

            if launch_yaw_deg is None:
                launch_yaw_deg = confirm_launch_yaw(start_ref, waypoint)

            waypoint_index += 1
            raw = input("Add another waypoint? [Y/n]: ").strip().lower()
            if raw in ("n", "no", "q", "quit"):
                break
    finally:
        stop_gnss_driver(gnss_process, gnss_log_handle)
        node.destroy_node()
        rclpy.shutdown()

    if launch_yaw_deg is None:
        raise RuntimeError("at least one waypoint is required")

    launch_yaw_deg = maybe_override_launch_yaw(launch_yaw_deg)

    route = {
        "route_name": route_name,
        "created_at": now_str(),
        "coordinate_source": "/fix",
        "enu_origin": fixed_origin,
        "start_ref": start_ref,
        "launch_yaw_deg": round(launch_yaw_deg, 2),
        "waypoints": [
            {
                "name": waypoint["name"],
                "lat": round(waypoint["lat"], 7),
                "lon": round(waypoint["lon"], 7),
                "alt": round(waypoint["alt"], 1),
            }
            for waypoint in waypoints
        ],
        "startup_fix_sample_count": SAMPLE_COUNT,
        "startup_fix_spread_max_m": STABILITY_THRESHOLD_M,
        "startup_fix_timeout_s": SAMPLE_TIMEOUT_S,
        "startup_gps_tolerance_m": STARTUP_GPS_TOLERANCE_M,
        "segment_length_m": SEGMENT_LENGTH_M,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    backup_existing_file()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as output_file:
        yaml.safe_dump(route, output_file, allow_unicode=True, sort_keys=False)

    print("\nSaved route file:")
    print(f"  {OUTPUT_FILE}")
    print(f"Waypoints: {len(waypoints)}")
    print(f"launch_yaw_deg: {route['launch_yaw_deg']:.2f}")
    print("Launch command:")
    print("  ros2 launch bringup system_gps_corridor.launch.py")


if __name__ == "__main__":
    main()

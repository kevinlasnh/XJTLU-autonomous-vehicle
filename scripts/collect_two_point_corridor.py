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

OUTPUT_DIR = Path.home() / 'XJTLU-autonomous-vehicle/runtime-data' / 'gnss'
OUTPUT_FILE = OUTPUT_DIR / 'two_point_corridor.yaml'
REPO_ROOT = Path.home() / 'XJTLU-autonomous-vehicle'
MASTER_PARAMS_FILE = REPO_ROOT / 'src' / 'bringup' / 'config' / 'master_params.yaml'
GNSS_DRIVER_LOG = OUTPUT_DIR / 'collect_two_point_corridor_nmea.log'
SAMPLE_COUNT = 10
STABILITY_THRESHOLD_M = 2.0
SAMPLE_TIMEOUT_S = 30.0
SEGMENT_LENGTH_M = 8.0
STARTUP_GPS_TOLERANCE_M = 6.0
FIX_TOPIC_DETECT_TIMEOUT_S = 3.0
DRIVER_STARTUP_TIMEOUT_S = 10.0


def now_str() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


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
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(lon2 - lon1))
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


class FixCollector(Node):
    def __init__(self) -> None:
        super().__init__('two_point_corridor_collector')
        self.latest_fix: NavSatFix | None = None
        self.last_fix_key: tuple | None = None
        self.create_subscription(NavSatFix, '/fix', self._callback, 10)
        self.get_logger().info('Waiting for /fix ...')

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
    log_handle = open(GNSS_DRIVER_LOG, 'w', encoding='utf-8')
    process = subprocess.Popen(
        [
            'ros2',
            'launch',
            'nmea_navsat_driver',
            'nmea_serial_driver.launch.py',
            f'params_file:={MASTER_PARAMS_FILE}',
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
    print('\nChecking /fix stream ...')
    if wait_for_fix_stream(node, FIX_TOPIC_DETECT_TIMEOUT_S):
        print('Using existing /fix publisher.')
        return None, None

    print('No /fix detected. Starting GNSS driver in background ...')
    process, log_handle = start_gnss_driver()
    if wait_for_fix_stream(node, DRIVER_STARTUP_TIMEOUT_S):
        print(f'/fix detected after starting GNSS driver. Driver log: {GNSS_DRIVER_LOG}')
        return process, log_handle

    stop_gnss_driver(process, log_handle)
    raise RuntimeError(
        'failed to start GNSS driver or detect /fix stream; '
        f'check {GNSS_DRIVER_LOG}'
    )


def collect_fix_samples(node: FixCollector, label: str) -> dict:
    deadline = time.time() + SAMPLE_TIMEOUT_S
    samples: deque[tuple[float, float, float]] = deque(maxlen=SAMPLE_COUNT)
    print(f'\n[{label}] collecting {SAMPLE_COUNT} stable /fix samples ... keep the vehicle still.')
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
            'lat': sum(sample[0] for sample in sample_list) / len(sample_list),
            'lon': sum(sample[1] for sample in sample_list) / len(sample_list),
            'alt': sum(sample[2] for sample in sample_list) / len(sample_list),
            'samples': len(sample_list),
            'spread_m': round(max_spread, 2),
            'source': '/fix',
            'collected_at': now_str(),
        }
        print(
            f"[{label}] lat={result['lat']:.7f} lon={result['lon']:.7f} alt={result['alt']:.2f} spread={result['spread_m']:.2f}m"
        )
        return result
    raise RuntimeError(f'timed out collecting stable /fix for {label}')


def backup_existing_file() -> None:
    if not OUTPUT_FILE.exists():
        return
    backup = OUTPUT_FILE.with_name(f"two_point_corridor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
    shutil.move(str(OUTPUT_FILE), str(backup))
    print(f'Backed up existing corridor file to: {backup}')


def main(args=None) -> None:
    corridor_name = input('Corridor name [fixed_launch_corridor]: ').strip() or 'fixed_launch_corridor'
    print('\nThis collector assumes:')
    print('- launch pose is physically fixed')
    print('- launch heading is physically fixed')
    print('- goal corridor lies along the vehicle forward axis at launch')
    input('\nPlace vehicle at the fixed launch pose, then press Enter to sample START ...')

    rclpy.init(args=args)
    node = FixCollector()
    gnss_process: subprocess.Popen[str] | None = None
    gnss_log_handle: TextIO | None = None
    try:
        gnss_process, gnss_log_handle = ensure_fix_stream(node)
        start_ref = collect_fix_samples(node, 'START')
        input('\nMove vehicle to the goal point, then press Enter to sample GOAL ...')
        goal_ref = collect_fix_samples(node, 'GOAL')
    finally:
        stop_gnss_driver(gnss_process, gnss_log_handle)
        node.destroy_node()
        rclpy.shutdown()

    distance_m = haversine_m(start_ref['lat'], start_ref['lon'], goal_ref['lat'], goal_ref['lon'])
    bearing = bearing_deg(start_ref['lat'], start_ref['lon'], goal_ref['lat'], goal_ref['lon'])
    corridor = {
        'corridor_name': corridor_name,
        'created_at': now_str(),
        'coordinate_source': '/fix',
        'start_ref': start_ref,
        'goal_ref': goal_ref,
        'distance_m': round(distance_m, 2),
        'bearing_deg': round(bearing, 2),
        'body_vector_m': {
            'x': round(distance_m, 2),
            'y': 0.0,
        },
        'segment_length_m': SEGMENT_LENGTH_M,
        'startup_fix_sample_count': SAMPLE_COUNT,
        'startup_fix_spread_max_m': STABILITY_THRESHOLD_M,
        'startup_fix_timeout_s': SAMPLE_TIMEOUT_S,
        'startup_gps_tolerance_m': STARTUP_GPS_TOLERANCE_M,
        'notes': 'v1 corridor assumes fixed launch pose and fixed launch heading; goal lies on the forward body axis.',
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    backup_existing_file()
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as output_file:
        yaml.safe_dump(corridor, output_file, allow_unicode=True, sort_keys=False)

    print('\nSaved corridor file:')
    print(f'  {OUTPUT_FILE}')
    print(f"Distance: {distance_m:.2f} m")
    print(f"Bearing:  {bearing:.2f} deg")
    print('Launch command:')
    print('  ros2 launch bringup system_gps_corridor.launch.py')


if __name__ == '__main__':
    main()

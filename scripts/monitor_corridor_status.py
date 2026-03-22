#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _terminate_process(pid: int) -> None:
    if pid <= 0 or not _process_alive(pid):
        return
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            os.kill(pid, sig)
        except OSError:
            return
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if not _process_alive(pid):
                return
            time.sleep(0.1)


def _format_status(text: str) -> tuple[str, bool, int | None]:
    if text == "INITIALIZING":
        return "[Corridor] 初始化导航链路...", False, None
    if text == "WAITING_FOR_STABLE_FIX":
        return "[Corridor] 等待稳定 GPS...", False, None
    if text == "WAITING_FOR_NAV2":
        return "[Corridor] GPS 已稳定，等待 Nav2 就绪...", False, None
    if text == "WAITING_FOR_MAP_TF":
        return "[Corridor] 等待 map->base_link TF...", False, None
    if text == "BOOTSTRAP_READY":
        return "[Corridor] 启动对齐完成。", False, None
    if text == "RUNNING_ROUTE":
        return "[Corridor] 已进入 GPS 路线，开始导航。", True, None
    if text == "SWITCHED_TO_PGO_ALIGNMENT":
        return "[Corridor] 已切换到 PGO 对齐。", True, None
    if text == "SUCCEEDED":
        return "[Corridor] 路线完成，系统将退出。", True, 0
    if text == "INTERRUPTED":
        return "[Corridor] 导航被中断，系统将退出。", True, 130
    if text.startswith("ABORTED:"):
        return f"[Corridor] 启动失败: {text.split(':', 1)[1].strip()}", False, 1
    if text.startswith("FAILED_WAYPOINT_"):
        return f"[Corridor] 导航失败: {text}", True, 1
    if text.startswith("WAYPOINT_TARGET|"):
        _, idx, total, name = text.split("|", 3)
        return f"[Corridor] 目标 {idx}/{total}: {name}", True, None
    if text.startswith("WAYPOINT_REACHED|"):
        _, idx, total, name = text.split("|", 3)
        return f"[Corridor] 已到达目标 {idx}/{total}: {name}", True, None
    if text.startswith("NAVIGATING_SUBGOAL|"):
        _, name, idx, total, x, y, source = text.split("|", 6)
        return (
            "[Corridor] 正在前往 %s 子目标 %s/%s (x=%s, y=%s, %s)"
            % (name, idx, total, x, y, source),
            True,
            None,
        )
    return f"[Corridor] {text}", False, None


class CorridorStatusMonitor(Node):
    def __init__(self) -> None:
        super().__init__("corridor_status_monitor")
        self._last_raw = ""
        self._last_line = ""
        self._running_route = False
        self._terminal_code: int | None = None
        self._terminal_seen = False
        self.create_subscription(String, "/gps_corridor/status", self._status_callback, 10)

    @property
    def running_route(self) -> bool:
        return self._running_route

    @property
    def terminal_seen(self) -> bool:
        return self._terminal_seen

    @property
    def terminal_code(self) -> int | None:
        return self._terminal_code

    def _status_callback(self, msg: String) -> None:
        raw = msg.data.strip()
        if not raw or raw == self._last_raw:
            return
        self._last_raw = raw
        line, running, terminal_code = _format_status(raw)
        if line != self._last_line:
            print(line, flush=True)
            self._last_line = line
        if running:
            self._running_route = True
        if terminal_code is not None:
            self._terminal_seen = True
            self._terminal_code = terminal_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--startup-timeout-s", type=float, default=45.0)
    parser.add_argument("--launch-pid", type=int, default=0)
    parser.add_argument("--launch-log", default="")
    args = parser.parse_args()

    rclpy.init()
    monitor = CorridorStatusMonitor()
    start_mono = time.monotonic()
    try:
        while rclpy.ok():
            rclpy.spin_once(monitor, timeout_sec=0.2)
            if monitor.terminal_seen:
                return int(monitor.terminal_code or 0)
            if args.launch_pid > 0 and not _process_alive(args.launch_pid):
                if args.launch_log:
                    print(
                        f"[Corridor] launch 已退出。完整日志见: {args.launch_log}",
                        flush=True,
                    )
                else:
                    print("[Corridor] launch 已退出。", flush=True)
                return 1
            if (
                not monitor.running_route
                and time.monotonic() - start_mono > args.startup_timeout_s
            ):
                if args.launch_log:
                    print(
                        "[Corridor] 启动超时：%.0f 秒内未进入 GPS 路线，系统将退出。完整日志见: %s"
                        % (args.startup_timeout_s, args.launch_log),
                        flush=True,
                    )
                else:
                    print(
                        "[Corridor] 启动超时：%.0f 秒内未进入 GPS 路线，系统将退出。"
                        % args.startup_timeout_s,
                        flush=True,
                    )
                if args.launch_pid > 0:
                    _terminate_process(args.launch_pid)
                return 1
    except KeyboardInterrupt:
        print("[Corridor] 控制台监控被中断，系统将退出。", flush=True)
        if args.launch_pid > 0:
            _terminate_process(args.launch_pid)
        return 130
    finally:
        monitor.destroy_node()
        rclpy.shutdown()

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

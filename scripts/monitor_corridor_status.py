#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import signal
import time
from pathlib import Path


STATUS_RE = re.compile(r"\[gps_route_runner\]:\s+(.*)$")


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
    return "", False, None


def _iter_new_statuses(log_path: Path, offset: int) -> tuple[list[str], int]:
    if not log_path.exists():
        return [], offset

    statuses: list[str] = []
    with log_path.open("r", encoding="utf-8", errors="ignore") as log_file:
        log_file.seek(offset)
        while True:
            line = log_file.readline()
            if not line:
                break
            match = STATUS_RE.search(line)
            if match:
                statuses.append(match.group(1).strip())
        offset = log_file.tell()
    return statuses, offset


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--startup-timeout-s", type=float, default=45.0)
    parser.add_argument("--launch-pid", type=int, default=0)
    parser.add_argument("--launch-log", required=True)
    args = parser.parse_args()

    log_path = Path(args.launch_log).expanduser()
    start_mono = time.monotonic()
    last_raw = ""
    last_line = ""
    running_route = False
    offset = 0

    print("[Corridor] 已发送启动命令，等待导航状态...", flush=True)

    try:
        while True:
            statuses, offset = _iter_new_statuses(log_path, offset)
            for raw in statuses:
                if not raw or raw == last_raw:
                    continue
                last_raw = raw
                line, running, terminal_code = _format_status(raw)
                if line and line != last_line:
                    print(line, flush=True)
                    last_line = line
                if running:
                    running_route = True
                if terminal_code is not None:
                    return terminal_code

            if args.launch_pid > 0 and not _process_alive(args.launch_pid):
                print(
                    f"[Corridor] launch 已退出。完整日志见: {args.launch_log}",
                    flush=True,
                )
                return 1

            if not running_route and time.monotonic() - start_mono > args.startup_timeout_s:
                print(
                    "[Corridor] 启动超时：%.0f 秒内未进入 GPS 路线，系统将退出。完整日志见: %s"
                    % (args.startup_timeout_s, args.launch_log),
                    flush=True,
                )
                if args.launch_pid > 0:
                    _terminate_process(args.launch_pid)
                return 1

            time.sleep(0.2)
    except KeyboardInterrupt:
        print("[Corridor] 控制台监控被中断，系统将退出。", flush=True)
        if args.launch_pid > 0:
            _terminate_process(args.launch_pid)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

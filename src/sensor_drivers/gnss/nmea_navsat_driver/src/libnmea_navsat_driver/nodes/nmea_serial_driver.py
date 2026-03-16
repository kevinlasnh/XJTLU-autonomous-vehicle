# Software License Agreement (BSD License)
#
# Copyright (c) 2013, Eric Perko
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the names of the authors nor the names of their
#    affiliated organizations may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import serial
import rclpy
from libnmea_navsat_driver.driver import Ros2NMEADriver
import os
from datetime import datetime
import yaml
from pathlib import Path


def get_runtime_root():
    runtime_root = os.environ.get("FYP_RUNTIME_ROOT")
    if runtime_root:
        return Path(runtime_root).expanduser()
    return Path.home() / "fyp_runtime_data"


def get_runtime_path(*parts):
    return get_runtime_root().joinpath(*parts)


def should_enable_logging(node_key):
    """检查是否应该启用日志"""
    try:
        config_path = get_runtime_path("config", "log_switch.yaml")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # 直接读取节点配置
        if node_key in config:
            return config[node_key].get('enable_logging', True)
        
        # 如果找不到配置，默认启用日志
        return True
        
    except Exception as e:
        print(f"Failed to read log config: {e}")
        return True  # 配置文件读取失败，默认启用日志


def main(args=None):
    rclpy.init(args=args)

    driver = Ros2NMEADriver()
    frame_id = driver.get_frame_id()

    serial_port = driver.declare_parameter('port', '/dev/ttyUSB0').value
    serial_baud = driver.declare_parameter('baud', 4800).value

    # 检查是否启用日志
    enable_log = should_enable_logging("nmea_serial_driver")
    
    log_file = None
    if enable_log:
        # 这里由 grok 进行了改动
        # Create log directory if it doesn't exist
        log_dir = get_runtime_path("logs", "nmea_navsat")
        os.makedirs(log_dir, exist_ok=True)

        # Generate log filename based on current time
        now = datetime.now()
        log_filename = f"log_{now.year}{now.month:02d}{now.day:02d}_{now.hour:02d}{now.minute:02d}{now.second:02d}.txt"
        log_filepath = os.path.join(log_dir, log_filename)

        # Open log file
        try:
            log_file = open(log_filepath, 'a')
            driver.get_logger().info(f"Logging enabled: {log_filepath}")
        except Exception as e:
            driver.get_logger().error(f"Failed to open log file: {e}")
            log_file = None
    else:
        driver.get_logger().info("Logging disabled by config")

    try:
        GPS = serial.Serial(port=serial_port, baudrate=serial_baud, timeout=2)
        driver.get_logger().info("Successfully connected to {0} at {1}.".format(serial_port, serial_baud))
        try:
            while rclpy.ok():
                data = GPS.readline().strip()
                try:
                    if isinstance(data, bytes):
                        # 这里由 grok 进行了改动
                        data = data.decode("utf-8", errors='ignore')
                    

                    # 这里由 grok 进行了改动
                    driver.get_logger().info(f"Received data: {repr(data)}")

                    # 这里原本使用的是标准时间格式，现更改成 ROS 时间戳格式
                    # ======================================================
                    # # 这里由 grok 进行了改动
                    # # Log the raw NMEA sentence
                    # timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    # log_file.write(f"[{timestamp}] {data}\n")
                    # log_file.flush()
                    # driver.add_sentence(data, frame_id)
                    # ======================================================

                    # 新代码块
                    # 获取ROS时间戳
                    ros_time = driver.get_clock().now()
                    ros_timestamp = ros_time.nanoseconds  # 19位纳秒时间戳
                    # 记录文件时间和ROS时间戳
                    file_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    # 只有当日志功能启用时才写入
                    if log_file:
                        log_file.write(f"[{file_timestamp}] ROS_timestamp: {ros_timestamp} | {data}\n")
                        log_file.flush()
                    driver.add_sentence(data, frame_id)

                except ValueError as e:
                    driver.get_logger().warn(
                        "Value error, likely due to missing fields in the NMEA message. Error was: %s. "
                        "Please report this issue at github.com/ros-drivers/nmea_navsat_driver, including a bag file "
                        "with the NMEA sentences that caused it." % e)

        except Exception as e:
            driver.get_logger().error("Ros error: {0}".format(e))
            GPS.close()  # Close GPS serial port
            # 这里由 grok 进行了改动
            if log_file:
                log_file.close()  # Close log file
    except serial.SerialException as ex:
        driver.get_logger().fatal("Could not open serial port: I/O error({0}): {1}".format(ex.errno, ex.strerror))
        # 这里由 grok 进行了改动
        if log_file:
            log_file.close()  # Close log file

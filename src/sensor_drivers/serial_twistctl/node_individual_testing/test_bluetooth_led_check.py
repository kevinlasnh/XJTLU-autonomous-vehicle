#!/usr/bin/env python3
"""
蓝牙模块连通性测试脚本 (LED观察专用)
功能: 持续向串口发送安全的心跳数据包，用于观察蓝牙模块的 TX/RX 指示灯状态。
"""

import serial
import time
import sys
import serial.tools.list_ports
import signal

# 全局变量
running = True
SERIAL_PORT = "/dev/serial_twistctl"
FALLBACK_PORT = "/dev/ttyACM0"
BAUDRATE = 115200

# 颜色代码
GREEN = "\033[92m"
msg_color = "\033[94m" # Blue
err_color = "\033[91m" # Red
RESET = "\033[0m"

def signal_handler(sig, frame):
    global running
    print(f"\n{GREEN}测试已停止。{RESET}")
    running = False

def find_port():
    """查找可用端口"""
    # 1. 优先检查符号链接
    try:
        if len(serial.tools.list_ports.grep(SERIAL_PORT.replace("/dev/", ""))) > 0:
            return SERIAL_PORT
    except:
        pass
    
    # 2. 检查实际设备
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if "ttyACM" in p.device:
            return p.device
    
    return None

def main():
    global running
    signal.signal(signal.SIGINT, signal_handler)

    print(f"{GREEN}=========================================={RESET}")
    print(f"{GREEN}    蓝牙模块连通性测试 (LED观察模式)      {RESET}")
    print(f"{GREEN}=========================================={RESET}")
    print("功能: 每秒发送 10 次 safe stop 数据包")
    print("目标: 让上层蓝牙模块的 TX 灯和下层蓝牙模块的 RX 灯闪烁")
    print(f"{msg_color}请在运行期间观察蓝牙模块上的 LED 指示灯!{RESET}")
    print("按 Ctrl+C 停止测试\n")

    port_name = SERIAL_PORT
    
    # 尝试打开串口
    try:
        ser = serial.Serial(port_name, BAUDRATE, timeout=0.1, write_timeout=0.1)
    except serial.SerialException:
        print(f"{err_color}无法打开默认端口 {port_name}，尝试搜索其他端口...{RESET}")
        found = find_port()
        if found:
            port_name = found
            try:
                ser = serial.Serial(port_name, BAUDRATE, timeout=0.1, write_timeout=0.1)
            except:
                print(f"{err_color}错误: 无法打开端口 {port_name}{RESET}")
                return
        else:
            print(f"{err_color}错误: 未找到可用的 ttyACM 端口! 请检查物理连接。{RESET}")
            return

    print(f"成功打开端口: {GREEN}{port_name}{RESET}")
    print(f"正在发送数据... (频率: 10Hz)\n")

    packet_count = 0
    error_count = 0
    disconnect_detected = False

    while running:
        try:
            # 发送安全心跳包 (速度为0)
            # 格式: vcx=0.000,wc=0.000
            data = "vcx=0.000,wc=0.000\n"
            ser.write(data.encode('utf-8'))
            ser.flush()
            
            packet_count += 1
            if packet_count % 10 == 0:
                sys.stdout.write(f"\r已发送数据包: {packet_count} | 状态: {GREEN}正常传输中...{RESET} (观察 LED 闪烁)")
                sys.stdout.flush()
            
            # 读取是否有回传数据 (如果下位机有回复的话)
            if ser.in_waiting:
                recv = ser.read(ser.in_waiting)
                # print(f"收到: {recv}") # 暂时不打印接收内容，专注于发送测试
            
            # 短暂休眠控制频率
            time.sleep(0.1) # 10Hz
            
        except serial.SerialException as e:
            disconnect_detected = True
            print(f"\n\n{err_color}严重错误: 串口连接断开!{RESET}")
            print(f"详细信息: {e}")
            print(f"{msg_color}诊断建议:{RESET}")
            print("1. 检查 USB 线是否松动")
            print("2. 检查拓展坞是否供电不足")
            print("3. 蓝牙模块可能意外复位")
            break
        except Exception as e:
            error_count += 1
            print(f"\n{err_color}发送错误: {e}{RESET}")
            if error_count > 5:
                print("错误次数过多，停止测试。")
                break
            time.sleep(1)

    if ser.is_open:
        ser.close()
    
    print("\n测试结束。")

if __name__ == "__main__":
    main()

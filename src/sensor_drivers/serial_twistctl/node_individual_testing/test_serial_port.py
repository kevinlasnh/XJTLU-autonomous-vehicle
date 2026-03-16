#!/usr/bin/env python3
"""
串口通信测试脚本 - 用于测试上层板蓝牙发送端口
测试项目:
1. 设备存在性检查
2. 符号链接检查
3. 串口打开测试
4. 数据发送测试
5. 回环测试（如果支持）
"""

import os
import sys
import time
import serial
import subprocess

# 配置参数
SERIAL_PORT = "/dev/serial_twistctl"
FALLBACK_PORT = "/dev/ttyACM0"
BAUDRATE = 115200
TIMEOUT = 1.0

# ANSI颜色代码
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header(text):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}  {text}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

def print_pass(text):
    print(f"  {GREEN}✓ PASS{RESET}: {text}")

def print_fail(text):
    print(f"  {RED}✗ FAIL{RESET}: {text}")

def print_warn(text):
    print(f"  {YELLOW}⚠ WARN{RESET}: {text}")

def print_info(text):
    print(f"  {BLUE}ℹ INFO{RESET}: {text}")

def test_device_exists():
    """测试1: 检查设备文件是否存在"""
    print(f"{BOLD}测试 1: 设备存在性检查{RESET}")
    
    results = {}
    
    # 检查符号链接
    if os.path.exists(SERIAL_PORT):
        print_pass(f"符号链接 {SERIAL_PORT} 存在")
        results['symlink'] = True
        
        # 检查符号链接指向
        if os.path.islink(SERIAL_PORT):
            target = os.readlink(SERIAL_PORT)
            print_info(f"符号链接指向: {target}")
            results['target'] = target
    else:
        print_fail(f"符号链接 {SERIAL_PORT} 不存在")
        results['symlink'] = False
    
    # 检查实际设备
    if os.path.exists(FALLBACK_PORT):
        print_pass(f"设备 {FALLBACK_PORT} 存在")
        results['device'] = True
    else:
        print_fail(f"设备 {FALLBACK_PORT} 不存在")
        results['device'] = False
    
    return results

def test_device_permissions():
    """测试2: 检查设备权限"""
    print(f"\n{BOLD}测试 2: 设备权限检查{RESET}")
    
    port = SERIAL_PORT if os.path.exists(SERIAL_PORT) else FALLBACK_PORT
    
    if not os.path.exists(port):
        print_fail("设备不存在，跳过权限检查")
        return False
    
    # 获取权限信息
    stat_info = os.stat(port)
    mode = oct(stat_info.st_mode)[-3:]
    print_info(f"设备权限: {mode}")
    
    # 检查是否可读写
    if os.access(port, os.R_OK):
        print_pass("设备可读")
    else:
        print_fail("设备不可读")
        return False
    
    if os.access(port, os.W_OK):
        print_pass("设备可写")
    else:
        print_fail("设备不可写 - 可能需要将用户添加到 dialout 组")
        return False
    
    return True

def test_usb_device_info():
    """测试3: 获取USB设备信息"""
    print(f"\n{BOLD}测试 3: USB设备信息{RESET}")
    
    try:
        result = subprocess.run(
            ['udevadm', 'info', '--name=/dev/ttyACM0', '--attribute-walk'],
            capture_output=True, text=True, timeout=5
        )
        
        output = result.stdout
        
        # 提取关键信息
        vendor = None
        product = None
        serial_num = None
        
        for line in output.split('\n'):
            if 'idVendor' in line and '==' in line:
                vendor = line.split('==')[1].strip().strip('"')
                if vendor and vendor != '':
                    print_info(f"Vendor ID: {vendor}")
                    break
        
        for line in output.split('\n'):
            if 'idProduct' in line and '==' in line:
                product = line.split('==')[1].strip().strip('"')
                if product and product != '':
                    print_info(f"Product ID: {product}")
                    break
        
        for line in output.split('\n'):
            if 'ATTRS{serial}' in line and '==' in line:
                serial_num = line.split('==')[1].strip().strip('"')
                if serial_num and serial_num != '':
                    print_info(f"Serial: {serial_num}")
                    break
        
        if vendor == "2e3c" and product == "5740":
            print_pass("设备 Vendor/Product ID 匹配预期 (2e3c:5740)")
            return True
        else:
            print_warn(f"设备 ID 可能不匹配预期 (期望 2e3c:5740)")
            return True  # 仍然继续测试
            
    except Exception as e:
        print_warn(f"无法获取USB信息: {e}")
        return True

def test_serial_open():
    """测试4: 尝试打开串口"""
    print(f"\n{BOLD}测试 4: 串口打开测试{RESET}")
    
    port = SERIAL_PORT if os.path.exists(SERIAL_PORT) else FALLBACK_PORT
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=BAUDRATE,
            timeout=TIMEOUT,
            write_timeout=TIMEOUT
        )
        
        if ser.is_open:
            print_pass(f"成功打开串口 {port}")
            print_info(f"波特率: {ser.baudrate}")
            print_info(f"数据位: {ser.bytesize}")
            print_info(f"停止位: {ser.stopbits}")
            print_info(f"校验位: {ser.parity}")
            ser.close()
            return True
        else:
            print_fail("串口打开后状态异常")
            return False
            
    except serial.SerialException as e:
        print_fail(f"串口打开失败: {e}")
        return False
    except Exception as e:
        print_fail(f"未知错误: {e}")
        return False

def test_serial_write():
    """测试5: 串口写入测试"""
    print(f"\n{BOLD}测试 5: 串口写入测试{RESET}")
    
    port = SERIAL_PORT if os.path.exists(SERIAL_PORT) else FALLBACK_PORT
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=BAUDRATE,
            timeout=TIMEOUT,
            write_timeout=TIMEOUT
        )
        
        # 测试发送命令 (格式与 serial_twistctl_node 相同)
        test_commands = [
            "vcx=0.000,wc=0.000\n",  # 停止命令
            "vcx=0.100,wc=0.000\n",  # 前进命令
            "vcx=0.000,wc=0.000\n",  # 停止命令
        ]
        
        print_info("发送测试命令...")
        
        for i, cmd in enumerate(test_commands):
            try:
                bytes_written = ser.write(cmd.encode('utf-8'))
                ser.flush()  # 确保数据发送完成
                print_pass(f"命令 {i+1}: '{cmd.strip()}' - 写入 {bytes_written} 字节")
                time.sleep(0.1)  # 短暂延迟
            except serial.SerialTimeoutException:
                print_fail(f"命令 {i+1}: 写入超时!")
                ser.close()
                return False
            except Exception as e:
                print_fail(f"命令 {i+1}: 写入失败 - {e}")
                ser.close()
                return False
        
        ser.close()
        print_pass("所有测试命令发送成功")
        return True
        
    except serial.SerialException as e:
        print_fail(f"串口操作失败: {e}")
        return False
    except Exception as e:
        print_fail(f"未知错误: {e}")
        return False

def test_serial_continuous():
    """测试6: 连续发送测试"""
    print(f"\n{BOLD}测试 6: 连续发送测试 (5秒){RESET}")
    
    port = SERIAL_PORT if os.path.exists(SERIAL_PORT) else FALLBACK_PORT
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=BAUDRATE,
            timeout=TIMEOUT,
            write_timeout=TIMEOUT
        )
        
        print_info("连续发送停止命令 5 秒...")
        
        start_time = time.time()
        count = 0
        errors = 0
        
        while time.time() - start_time < 5.0:
            try:
                cmd = "vcx=0.000,wc=0.000\n"
                ser.write(cmd.encode('utf-8'))
                ser.flush()
                count += 1
                time.sleep(0.05)  # 20Hz
            except Exception as e:
                errors += 1
                if errors >= 3:
                    print_fail(f"连续发送出错过多: {e}")
                    ser.close()
                    return False
        
        ser.close()
        
        rate = count / 5.0
        print_pass(f"成功发送 {count} 条命令 (平均 {rate:.1f} Hz)")
        
        if errors > 0:
            print_warn(f"发送过程中有 {errors} 次错误")
        
        return True
        
    except Exception as e:
        print_fail(f"连续发送测试失败: {e}")
        return False

def main():
    print_header("串口通信测试 - 上层板蓝牙发送端口")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标端口: {SERIAL_PORT}")
    print(f"备用端口: {FALLBACK_PORT}")
    print(f"波特率: {BAUDRATE}")
    
    results = {}
    
    # 执行所有测试
    results['device_exists'] = test_device_exists()
    results['permissions'] = test_device_permissions()
    results['usb_info'] = test_usb_device_info()
    results['serial_open'] = test_serial_open()
    results['serial_write'] = test_serial_write()
    results['continuous'] = test_serial_continuous()
    
    # 汇总结果
    print_header("测试结果汇总")
    
    all_passed = True
    
    if results['device_exists'].get('symlink') and results['device_exists'].get('device'):
        print_pass("设备存在性检查")
    else:
        print_fail("设备存在性检查")
        all_passed = False
    
    if results['permissions']:
        print_pass("设备权限检查")
    else:
        print_fail("设备权限检查")
        all_passed = False
    
    if results['usb_info']:
        print_pass("USB设备信息")
    else:
        print_warn("USB设备信息 (非关键)")
    
    if results['serial_open']:
        print_pass("串口打开测试")
    else:
        print_fail("串口打开测试")
        all_passed = False
    
    if results['serial_write']:
        print_pass("串口写入测试")
    else:
        print_fail("串口写入测试")
        all_passed = False
    
    if results['continuous']:
        print_pass("连续发送测试")
    else:
        print_fail("连续发送测试")
        all_passed = False
    
    print()
    if all_passed:
        print(f"{GREEN}{BOLD}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{GREEN}{BOLD}║         ✓ 所有测试通过 - 串口工作正常!                  ║{RESET}")
        print(f"{GREEN}{BOLD}╚══════════════════════════════════════════════════════════╝{RESET}")
        return 0
    else:
        print(f"{RED}{BOLD}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{RED}{BOLD}║         ✗ 部分测试失败 - 请检查硬件连接!                ║{RESET}")
        print(f"{RED}{BOLD}╚══════════════════════════════════════════════════════════╝{RESET}")
        print()
        print(f"{YELLOW}可能的解决方案:{RESET}")
        print("  1. 检查蓝牙模块与拓展坞的连接是否牢固")
        print("  2. 检查拓展坞USB端口是否正常工作")
        print("  3. 尝试更换USB端口")
        print("  4. 运行: sudo udevadm control --reload-rules && sudo udevadm trigger")
        print("  5. 检查蓝牙模块电源是否正常")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}测试被用户中断{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}测试脚本发生错误: {e}{RESET}")
        sys.exit(1)

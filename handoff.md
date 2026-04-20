# 交接文档 / Handoff Document

## 2026.04.20

### STM32 RM C Board 固件优化（分支: `stm32f4_fix`）

根据 `docs-CN/firmware_optimization_plan.md` 方案完成 5 阶段代码修改，待烧录验证。

#### Phase 1: 基础 Bug 修复

- **文件**: `Core/Src/Motor_Speed_pid.c`
  - `Set_free;` → `Set_free()` (3 处，原为无效语句)
  - `led_white_start;` → `led_white_start()` (同类 bug)
- **文件**: `Core/Src/CAN_receive.c`
  - `speed_rpm` 解析从 `(uint16_t)` 改为 `(int16_t)`，修正负转速解析
- **文件**: `Core/Src/pid.c`
  - 取消 `last_err = pid->err` 注释，使微分项 future-proof

#### Phase 2: 急停 — 两阶段受控制动

- **文件**: `Core/Src/Joystick.c`
  - B 键急停重写: 清零 Vcx/Wc、清零 4 个 PID 积分器、去掉 `led_pink_blink()` 阻塞
  - 新增 `#include "pid.h"` 和 `extern PID_TypeDef motor_pid[4]`
- **文件**: `Core/Src/Motor_Speed_pid.c`
  - `motor_ready==0` 分支增加防御性 iout 清零
  - `Speed_set()` 增加近零速释放判据 (ESTOP_RELEASE_RPM=20, ESTOP_RELEASE_COUNT=3)

#### Phase 3: PID 积分限幅恢复

- **文件**: `Core/Src/pid.c`
  - 取消 `iout > IntegralLimit` 限幅代码的注释 (IntegralLimit=1000)

#### Phase 4: 串口通信健壮性

- **文件**: `Core/Src/usart.c`
  - IDLE 中断中 memcpy 后补 `\0` 终止符，条件改为 `<= UART_RX_BUF_SIZE - 1`
- **文件**: `Core/Src/user_usart.c`
  - `vsprintf` → `vsnprintf` (防越界)
  - 增加 `huart1.gState != HAL_UART_STATE_READY` DMA busy 守卫
- **文件**: `Core/Src/main.c`
  - 新增 `last_serial_cmd_tick` 全局变量，`Serial_Input()` 解析成功时更新
  - 移除 sscanf format 中多余的 `\n`
- **文件**: `Core/Src/Motor_Speed_pid.c`
  - `Motor_Speed_Calc()` 开头增加 500ms 超时检查

#### Phase 5: 里程计精度改善

- **文件**: `Core/Src/Motor_Speed_pid.c`
  - `MOTORrpm2vw()` 中轮距从 `0.5` 统一为 `0.46`
- **文件**: `Core/Src/main.c`
  - `Serial_Output()` 使用 `HAL_GetTick()` 计算实际 DeltaTime
  - 里程计使用 4 电机均值替代仅用 motor[0]/motor[2]

#### 验证计划

每个 Phase 独立烧录验证:
1. Phase 1: 编译通过 → 手柄基础运动 → X 键释放电机 → 串口观察 speed_rpm 符号
2. Phase 2: 中速前进 → B 键急停 → 观察无反转、LED 无延迟、近零速释放
3. Phase 3: 目标速度 0 静置 30s → 无自转 → 串口监控 iout ≤ ±1000
4. Phase 4: 串口发送正常/畸形数据 → 断开串口 → 500ms 后停车
5. Phase 5: 直线 5m 对比 → 原地 360° 对比 → 与 FAST-LIO2 对比

#### 风险

- Phase 1-3: 极低风险，纯 bug 修复 + 限幅恢复
- Phase 4: 低风险，DMA busy 跳过可能丢帧（丢帧 < 乱帧）
- Phase 5: 低风险，需确认 motor 0,1 为左侧、2,3 为右侧

#### 回滚

所有修改通过 git 管理，任何 Phase 出问题可 `git checkout` 回滚旧固件烧录。

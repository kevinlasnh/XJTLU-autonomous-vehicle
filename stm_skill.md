---
name: stm32-development-workflow
description: |
  STM32通用程序开发完整流程，基于STM32CubeCLT命令行工具链。涵盖工具链安装、
  HAL库配置、项目构建、固件编译和ST-Link烧录。适用于STM32F1/F4/H7等系列，
  解决编译错误、链接错误、烧录失败等常见问题。
author: EricSun
version: 1.0.0
date: 2025-02-27
---

# STM32 通用程序开发流程

## 概述
基于STM32CubeCLT命令行工具链的完整STM32开发流程，无需依赖Keil或STM32CubeIDE。

## 开发环境准备

### 1. 安装STM32CubeCLT
从ST官网下载并安装STM32CubeCLT，包含：
- arm-none-eabi-gcc 编译器
- STM32CubeProgrammer (烧录工具)
- ST-Link驱动

典型安装路径：`C:\ST\STM32CubeCLT_1.21.0`

### 2. 获取HAL库
从GitHub下载STM32Cube固件包：
```bash
# STM32CubeF4示例
git clone https://github.com/STMicroelectronics/STM32CubeF4.git

# 或从ST官网下载完整固件包
```

固件包目录结构：
```
STM32Cube_FW_F4_V1.28.0/
├── Drivers/
│   ├── STM32F4xx_HAL_Driver/    # HAL库源文件
│   ├── CMSIS/                    # CMSIS核心文件
│   └── BSP/                      # 板级支持包
├── Projects/                     # 示例项目
└── Utilities/                    # 工具
```

## 项目目录结构

```
my-stm32-project/
├── Core/
│   ├── Inc/                      # 核心头文件
│   │   └── main.h
│   └── Src/                      # 核心源文件
│       └── main.c
├── Drivers/
│   ├── STM32F4xx_HAL_Driver/     # HAL库
│   │   ├── Inc/                  # HAL头文件
│   │   │   └── stm32f4xx_hal_conf.h  # 关键配置文件
│   │   └── Src/                  # HAL源文件
│   ├── CMSIS/                    # CMSIS
│   │   ├── Core/                 # CMSIS核心
│   │   └── Device/ST/STM32F4xx/  # 设备特定文件
│   │       ├── Include/          # 启动文件
│   │       └── Source/Templates/
│   │           ├── gcc/          # GCC启动文件
│   │           │   └── startup_stm32f429xx.s
│   │           └── system_stm32f4xx.c
│   └── BSP/                      # 板级支持包(可选)
├── build/                        # 构建输出
└── build.sh                      # 构建脚本
```

## HAL库配置

### 关键配置文件 stm32f4xx_hal_conf.h

启用需要的HAL模块：
```c
#define HAL_MODULE_ENABLED
#define HAL_GPIO_MODULE_ENABLED
#define HAL_RCC_MODULE_ENABLED
#define HAL_FLASH_MODULE_ENABLED
#define HAL_PWR_MODULE_ENABLED
#define HAL_CORTEX_MODULE_ENABLED

// 根据外设需求启用
#define HAL_DMA_MODULE_ENABLED
#define HAL_UART_MODULE_ENABLED
#define HAL_TIM_MODULE_ENABLED
#define HAL_I2C_MODULE_ENABLED
#define HAL_SPI_MODULE_ENABLED
#define HAL_ADC_MODULE_ENABLED
// ... etc
```

时钟配置（HSE_VALUE必须与硬件匹配）：
```c
#if !defined (HSE_VALUE)
  #define HSE_VALUE  8000000U  // 8MHz for STM32F429I-DISCO
#endif
```

## 构建脚本 build.sh

```bash
#!/bin/bash

TOOLCHAIN="/c/ST/STM32CubeCLT_1.21.0/GNU-tools-for-STM32/bin"
CC="${TOOLCHAIN}/arm-none-eabi-gcc"
AS="${TOOLCHAIN}/arm-none-eabi-gcc -x assembler-with-cpp"
LD="${TOOLCHAIN}/arm-none-eabi-gcc"
CP="${TOOLCHAIN}/arm-none-eabi-objcopy"
SZ="${TOOLCHAIN}/arm-none-eabi-size"

PROJECT_DIR="/path/to/project"
BUILD_DIR="${PROJECT_DIR}/build"

# MCU配置
MCU="-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard"
DEFS="-DUSE_HAL_DRIVER -DSTM32F429xx"
INCLUDES="-I${PROJECT_DIR}/Core/Inc \
          -I${PROJECT_DIR}/Drivers/STM32F4xx_HAL_Driver/Inc \
          -I${PROJECT_DIR}/Drivers/CMSIS/Device/ST/STM32F4xx/Include \
          -I${PROJECT_DIR}/Drivers/CMSIS/Include"

CFLAGS="${MCU} ${DEFS} ${INCLUDES} -O2 -Wall -fdata-sections -ffunction-sections"
ASFLAGS="${MCU} ${DEFS} ${INCLUDES} -Wall"

# 链接器脚本路径
LDSCRIPT="${PROJECT_DIR}/Drivers/CMSIS/Device/ST/STM32F4xx/Source/Templates/gcc/linker/STM32F429ZITx_FLASH.ld"
LDFLAGS="${MCU} -specs=nano.specs -T${LDSCRIPT} -lc -lm -lnosys -Wl,--gc-sections"

# 源文件列表
HAL_SRCS=(
    "${PROJECT_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal.c"
    "${PROJECT_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_cortex.c"
    "${PROJECT_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_gpio.c"
    "${PROJECT_DIR}/Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rcc.c"
    # ... 添加需要的HAL模块
)

CORE_SRCS=(
    "${PROJECT_DIR}/Core/Src/main.c"
    "${PROJECT_DIR}/Drivers/CMSIS/Device/ST/STM32F4xx/Source/Templates/system_stm32f4xx.c"
)

ASM_SRCS=(
    "${PROJECT_DIR}/Drivers/CMSIS/Device/ST/STM32F4xx/Source/Templates/gcc/startup_stm32f429xx.s"
)

# 编译函数
compile_c() {
    local src=$1
    local obj="${BUILD_DIR}/$(basename ${src%.c}.o)"
    echo "  CC ${src}"
    ${CC} -c ${CFLAGS} -o ${obj} ${src}
    echo "${obj}"
}

compile_asm() {
    local src=$1
    local obj="${BUILD_DIR}/$(basename ${src%.s}.o)"
    echo "  AS ${src}"
    ${AS} -c ${ASFLAGS} -o ${obj} ${src}
    echo "${obj}"
}

# 主构建流程
echo "Building project..."
mkdir -p ${BUILD_DIR}

OBJECTS=""

# 编译HAL文件
for src in "${HAL_SRCS[@]}"; do
    obj=$(compile_c "${src}")
    OBJECTS="${OBJECTS} ${obj}"
done

# 编译核心文件
for src in "${CORE_SRCS[@]}"; do
    obj=$(compile_c "${src}")
    OBJECTS="${OBJECTS} ${obj}"
done

# 编译启动文件
for src in "${ASM_SRCS[@]}"; do
    obj=$(compile_asm "${src}")
    OBJECTS="${OBJECTS} ${obj}"
done

# 链接
echo "Linking..."
${LD} ${OBJECTS} ${LDFLAGS} -o ${BUILD_DIR}/project.elf

# 生成HEX/BIN
${CP} -O ihex ${BUILD_DIR}/project.elf ${BUILD_DIR}/project.hex
${CP} -O binary -S ${BUILD_DIR}/project.elf ${BUILD_DIR}/project.bin

# 显示大小
${SZ} ${BUILD_DIR}/project.elf

echo "Build complete!"
```

## 烧录流程

### 1. 检查ST-Link连接
```bash
STM32_Programmer_CLI.exe -l stlink
```

### 2. 升级ST-Link固件（如需要）
```bash
# 如果提示"Old ST-Link firmware version"
cd C:\ST\STM32CubeCLT_1.21.0
java -jar STLink-gdb-server/bin/STLinkUpgrade.jar -sn [序列号]
```

### 3. 烧录固件
```bash
# 烧录HEX文件
STM32_Programmer_CLI.exe \
    -c port=SWD sn=[序列号] \
    -w build/project.hex 0x08000000 \
    -v -rst
```

参数说明：
- `-c port=SWD`: 使用SWD接口
- `-w`: 写入文件
- `-v`: 验证
- `-rst`: 复位运行

## 常见编译错误及解决

| 错误 | 原因 | 解决 |
|-----|------|------|
| `unknown type name 'DMA2D_HandleTypeDef'` | HAL模块未启用 | 在hal_conf.h中定义`#define HAL_DMA2D_MODULE_ENABLED` |
| `undefined reference to 'SystemCoreClock'` | 缺少system文件 | 添加`system_stm32f4xx.c`到编译 |
| `undefined reference to 'FMC_SDRAM_Init'` | 缺少LL库 | 添加`stm32f4xx_ll_fmc.c`到编译 |
| `multiple definition of 'Font8'` | 字体重复定义 | 检查是否重复包含字体源文件 |
| `cannot open linker script file` | 链接器脚本路径错误 | 检查LDSCRIPT路径 |

## 调试技巧

### 1. 验证HAL配置
```c
// 在main()中添加检查
#if !defined(HSE_VALUE)
  #error "HSE_VALUE not defined!"
#endif
```

### 2. 使用LED指示程序状态
```c
// 初始化LED
BSP_LED_Init(LED3);

// 在关键位置闪烁
while (1) {
    BSP_LED_Toggle(LED3);
    HAL_Delay(500);
}
```

### 3. 检查时钟配置
```c
// 打印系统时钟频率（需要串口）
printf("System Clock: %lu Hz\n", HAL_RCC_GetSysClockFreq());
```

## 参考资源

- [STM32CubeF4 GitHub](https://github.com/STMicroelectronics/STM32CubeF4)
- [STM32CubeCLT用户手册](https://www.st.com/resource/en/user_manual/um2739-stm32cubeclt-stmicroelectronics.pdf)
- [GCC ARM选项参考](https://gcc.gnu.org/onlinedocs/gcc/ARM-Options.html)

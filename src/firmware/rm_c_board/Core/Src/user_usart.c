//user_usart.c
//2023.10.20
//by gjx

#include "user_usart.h"
#include <stdio.h>


void usart_printf(const char *fmt,...)
{
    static uint8_t tx_buf[256] = {0};
    static va_list ap;
    static uint16_t len;

    // DMA busy 守卫: 如果上一次发送未完成，跳过本次
    if (huart1.gState != HAL_UART_STATE_READY) {
        return;
    }

    va_start(ap, fmt);
    len = vsnprintf((char *)tx_buf, sizeof(tx_buf), fmt, ap);
    va_end(ap);

    if (len > sizeof(tx_buf)) {
        len = sizeof(tx_buf);  // 截断保护
    }

    HAL_UART_Transmit_DMA(&huart1, tx_buf, len);
}



//led.c
//2023.10.17
//by gjx

#include "led.h"

//���Ƶ���
void led_blue_start(void)
{
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
}

//�̵Ƶ���
void led_green_start(void)
{
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,60000);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
}

//��Ƶ���
void led_red_start(void)
{
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
}

//�׵Ƶ���
void led_white_start(void)
{
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,60000);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
}

void led_pink_start(void)
{
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,56400);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,9400);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,34800);
}

//����Ϩ��
void led_blue_stop(void)
{
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
}

//�̵�Ϩ��
void led_green_stop(void)
{
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
}

//���Ϩ��
void led_red_stop(void)
{
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
}

//�׵�Ϩ��
void led_white_stop(void)
{
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
}

void led_pink_stop(void)
{
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
}


//������˸
void led_blue_blink(void)
{
	// while(1)
	// {
	// 	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
	// 	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
	// 	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
	// 	HAL_Delay(500);
	// 	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
	// 	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
	// 	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
	// 	HAL_Delay(500);
	// }

	
	
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		HAL_Delay(100);
	
}

//�̵���˸
void led_green_blink(void)
{
	while(1)
	{
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		HAL_Delay(500);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		HAL_Delay(500);
	}
	
}

//�����˸
void led_red_blink(void)
{
	// while(1)
	// {
	// 	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
	// 	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
	// 	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
	// 	HAL_Delay(500);
	// 	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
	// 	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
	// 	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
	// 	HAL_Delay(500);
	// }
	
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		HAL_Delay(100);
	
	
}

//�׵���˸
void led_white_blink(void)
{
	while(1)
	{
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,60000);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
		// HAL_Delay(500);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		// HAL_Delay(500);

		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		HAL_Delay(100);

	}
	
}

void led_pink_blink(void)
{
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,56400);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,9400);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,34800);
	HAL_Delay(100);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
	HAL_Delay(100);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,56400);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,9400);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,34800);
	HAL_Delay(100);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
	__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
	HAL_Delay(100);
}


void led_white_red_blink(void)
{

		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,60000);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
		// HAL_Delay(500);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		// HAL_Delay(500);

		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
		HAL_Delay(100);
	
}

void led_white_blue_blink(void)
{
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,60000);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
		// HAL_Delay(500);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,0);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		// __HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		// HAL_Delay(500);

		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,60000);
		HAL_Delay(100);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_1,60000);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_2,0);
		__HAL_TIM_SetCompare(&htim5,TIM_CHANNEL_3,0);
		HAL_Delay(100);
}

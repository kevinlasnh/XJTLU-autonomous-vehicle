#include "Motor_Speed_pid.h"

#define MAX_SPEED_RPM 20000  // 最大转速

PID_TypeDef motor_pid[4];
float set_spdL;// rpm  ���ֽ��ٶȣ�ת�٣�        1 rpm = pi/30 = 0.1047 ��rad/s��    1(rad/s) = 9.55(rpm)            //Pi rad = 180��    1 rad = 180/Pi ��    1 �� = Pi/180 rad
float set_spdR;// rpm  ���ֽ��ٶȣ�ת�٣�

float set_spdL1;
float set_spdR1;

extern float Vcx;   //   m/s
extern float Wc;    //   rad/s
float C = 0.46;     //   m
float r = 0.1;     //   m
int flaggg = 0;

int motor_ready = 0; //电机被控制
int motor_shutdown = 0; //电机使能
int free_flag = 0; // 0不允许自由滑动

extern int control_mode;  // 0: 手柄控制, 1: 串口控制

// 急停近零速释放参数
#define ESTOP_RELEASE_RPM 20.0f
#define ESTOP_RELEASE_COUNT 3
static uint8_t estop_release_counter = 0;




float low_pass_filter(float value, float fc, float Ts)
{
	
	
  float b = fc * Ts;
  float alpha = b / (b + 1);
  static float out_last = 0; //��һ���˲�ֵ
  float out;

  static char fisrt_flag = 1;
  if (fisrt_flag == 1)
  {
    fisrt_flag = 0;
    out_last = value;
  }

  out = out_last + alpha * (value - out_last);
  out_last = out;

  return out;
}


// C = 0.46;     //   m
// r = 0.1;     //   m

#define SERIAL_CMD_TIMEOUT_MS 500

void Motor_Speed_Calc()
{
    // 串口模式超时保护
    extern uint32_t last_serial_cmd_tick;
    if (control_mode == 1 &&
        (HAL_GetTick() - last_serial_cmd_tick > SERIAL_CMD_TIMEOUT_MS)) {
        Vcx = 0;
        Wc = 0;
    }

    if (motor_shutdown == 1)
    {
        led_white_start();
        Set_free();
    }
    else if (motor_shutdown == 0 && motor_ready == 1) 
    {
        set_spdL = (2 * Vcx - Wc * C) / (2 * r) * 9.55 * 19.2;
        set_spdR = (2 * Vcx + Wc * C) / (2 * r) * 9.55 * 19.2;

        if (set_spdL > MAX_SPEED_RPM) set_spdL = MAX_SPEED_RPM;
        if (set_spdL < -MAX_SPEED_RPM) set_spdL = -MAX_SPEED_RPM; // limiting speed

        if (set_spdR > MAX_SPEED_RPM) set_spdR = MAX_SPEED_RPM;
        if (set_spdR < -MAX_SPEED_RPM) set_spdR = -MAX_SPEED_RPM; 
    }
    else if (motor_shutdown == 0 && motor_ready == 0)
    {
        set_spdL = 0;
        set_spdR = 0;
        // 防御性清零：确保任何进入此状态的路径都不会有积分残留
        for (int i = 0; i < 4; i++) {
            motor_pid[i].iout = 0;
        }
    }
    else
    {
        Set_free();
    }
}



// void Motor_Speed_pid_init()  //static void pid_param_init(PID_TypeDef * pid, PID_ID   id,uint16_t maxout,uint16_t intergral_limit,float deadband,uint16_t period,int16_t  max_err,int16_t  target,float 	kp, float 	ki, float 	kd)
// {
//   for(int i=0; i<4; i++)
//   {	
//     pid_init(&motor_pid[i]);
//     motor_pid[i].f_param_init(&motor_pid[i],PID_Speed,10000,10000,0,0,8000,0,10,3.2832,0);  
//   }
// }

void Motor_Speed_pid_init()
{
    for (int i = 0; i < 4; i++)
    {
        pid_init(&motor_pid[i]);
        
        // Adjust PID parameters
    //     motor_pid[i].f_param_init(&motor_pid[i], PID_Speed, 
    //                               5000,     // Kp: Proportional gain
    //                               5000,     // Ki: Integral gain, moderate adjustment
    //                               0,        // Ki limit set to 0 or a small value
    //                               0,        // Derivative saturation limit
    //                               4000,     // Limit for the integral value
    //                               0,        // Set target to 0
    //                               10,       // Sampling time
    //                               2,        // Kd: Derivative gain, increased derivative gain
    //                               0);       // Additional gain for fine-tuning
    // }

        motor_pid[i].f_param_init(&motor_pid[i], PID_Speed, 
            15000,     // Kp: Proportional gain
            1000,     // Ki: Integral gain, moderate adjustment
            0,        // Ki limit set to 0 or a small value
            0,        // Derivative saturation limit
            1000,     // Limit for the integral value
            0,        // Set target to 0
            10,       // Sampling time
            100,        // Kd: Derivative gain, increased derivative gain
            0);       // Additional gain for fine-tuning
    }

}


void Set_free()
{
	CAN_cmd_chassis(0,0,0,0);
	for(int i=0; i<4; i++)
	{
		motor_pid[i].iout = 0;
		motor_pid[i].output = 0;
		motor_pid[i].calculate_output = 0;
	}
	
}

void Speed_set()
{
    if(free_flag == 0)
    {
        Motor_Speed_Calc();
        motor_pid[0].target = set_spdL;
        motor_pid[1].target = set_spdL;
        motor_pid[2].target = -set_spdR;
        motor_pid[3].target = -set_spdR;
        for(int i=0; i<4; i++)
        {
            motor_pid[i].f_cal_pid(&motor_pid[i],motor_chassis[i].speed_rpm);
        }

        // 急停近零速释放判据：motor_ready==0 时检测是否所有轮速都已接近零
        if (motor_ready == 0 && motor_shutdown == 0)
        {
            int all_below = 1;
            for (int i = 0; i < 4; i++) {
                float spd = motor_chassis[i].speed_rpm;
                if (spd < 0) spd = -spd;
                if (spd > ESTOP_RELEASE_RPM) {
                    all_below = 0;
                    break;
                }
            }
            if (all_below) {
                estop_release_counter++;
                if (estop_release_counter >= ESTOP_RELEASE_COUNT) {
                    // 进入零电流释放阶段
                    Set_free();
                    estop_release_counter = 0;
                    return;
                }
            } else {
                estop_release_counter = 0;
            }
        }
        else
        {
            estop_release_counter = 0;
        }

        CAN_cmd_chassis(motor_pid[0].output,
                        motor_pid[1].output,
                        motor_pid[2].output,
                        motor_pid[3].output);
    }

    if(free_flag == 1)
    {
        Set_free();
    }

    

    // if((motor_ready == 1) || (control_mode == 1))
    // {
    //     // usart_printf("motor ready or control_mode == 1\n");

    //     if(motor_shutdown == 0)//电机活动
    //     {
    //         if(control_mode == 0) // 手柄控制模式
    //         {
    //             if((PS2_LY < 133) && (PS2_LY > 123) && (PS2_RX < 130) && (PS2_RX > 124))
    //             {
    //                 // Set_free(); //自由滑动
    //                 // free_flag = 0;// 不允许自由滑动
    //             }
    //             else
    //             {
    //                 // free_flag = 0;
    //             }
    //         }

    //         else if(control_mode == 1) // 串口控制模式
    //         {
    //             // Motor_Speed_Calc(); // 使用Vcx和Wc的串口输入
    //             free_flag = 0; // 不允许自由滑动
    //         }

    //         if(free_flag == 0)
    //         {
	// 			Motor_Speed_Calc();
    //             motor_pid[0].target = set_spdL;
    //             motor_pid[1].target = set_spdL;
    //             motor_pid[2].target = -set_spdR;
    //             motor_pid[3].target = -set_spdR;
    //             for(int i=0; i<4; i++)
    //             {
    //                 motor_pid[i].f_cal_pid(&motor_pid[i],motor_chassis[i].speed_rpm);
    //             }

    //             CAN_cmd_chassis(motor_pid[0].output,
    //                             motor_pid[1].output,
    //                             motor_pid[2].output,
    //                             motor_pid[3].output);
    //         }

    //         else if(free_flag == 1)//允许自由滑动
    //         {
    //             Set_free;
    //         }
    //     }
    //     else
    //     {
    //         Set_free;
    //     }
    // }

    // if(motor_ready == 0)
    // {
    //     if(free_flag == 0)
    //     {
    //         Motor_Speed_Calc();
    //         motor_pid[0].target = set_spdL;
    //         motor_pid[1].target = set_spdL;
    //         motor_pid[2].target = -set_spdR;
    //         motor_pid[3].target = -set_spdR;
    //         for(int i=0; i<4; i++)
    //         {
    //             motor_pid[i].f_cal_pid(&motor_pid[i],motor_chassis[i].speed_rpm);
    //         }

    //         CAN_cmd_chassis(motor_pid[0].output,
    //                         motor_pid[1].output,
    //                         motor_pid[2].output,
    //                         motor_pid[3].output);
    //     }
    //     else
    //     {
    //         Set_free;
    //     }
    // }
}



//Using motor_speed(rpm) to calculate the velocity(m/s) and angular velocity(rad/s) of the car
void MOTORrpm2vw(float left_motor_speed,float right_motor_speed,float *vcx,float*w)
{
	const float c = 0.46f;	 //m (与正运动学一致)
	const float r = 0.1f;   //m
	float left_wheel_w = left_motor_speed/19.0f/9.55f;  //motor_speed(rpm)->wheel_speed(rad/s)
	float right_wheel_w = right_motor_speed/19.0f/9.55f;
	float vL = left_wheel_w * r;
	float vR = right_wheel_w * r;
	*vcx = 0.5f*vL + 0.5f*vR;   //  m/s
	*w = -vL/c + vR/c;           //  rad/s
}
void speed_print()
{
	//usart_printf("%d,%f,%f,%d,%d,%f,%d,%d,%d\n",motor_chassis[0].speed_rpm,       set_spdL,   motor_pid[0].output,   PS2_LY,PS2_RX,MAX_Speed,motor_shutdown,motor_ready,free_flag);		
}
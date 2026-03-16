这段代码的功能：

初始化校准经纬度：
在 start_calibration() 方法里，用户手动选择启动的校准点，程序记录该点的校准经纬度。
持续订阅 /fix：
通过 create_subscription 订阅 /fix 话题，持续接收传感器的 GNSS 数据，保存在 self.latest_valid_data 中。
持续校准并发布：
创建了一个定时器，每 0.5 秒执行一次 publish_calibrated_data()，用选定的校准点经纬度替换传感器数据中的经纬度，其他字段保持不变，然后把校准后的数据发布到 /gnss 话题。
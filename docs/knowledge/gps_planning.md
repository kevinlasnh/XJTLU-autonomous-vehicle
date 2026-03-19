# GPS 全局路径规划设计

## 1. 当前已落地能力（2026-03）

当前仓库已经具备下面这些 GPS 相关能力：

1. `make launch-explore-gps`
   - 启动 Livox、FAST-LIO2、PGO、Nav2
   - 同时拉起 `nmea_navsat_driver` 与 `gnss_calibration`
   - 把校准后的 `/gnss` 注入 PGO GPS 因子
2. `master_params.yaml`
   - 统一管理 GNSS 串口、PGO GPS 因子、FAST-LIO2 等参数
3. `gnss_calibration` no-fix 保护
   - 室内无卫星时不会写出假的有效偏移
4. 数据采集脚本
   - `record_bag.sh`
   - `record_perf.sh`
   - `bag_to_tum.py`

## 2. 当前没有落地的部分

下面这些还不是生产可用状态：

1. GPS 航点直接转 Nav2 目标点
2. 长距离 GPS 全局路线自动执行
3. 基于高质量室外 fix 的整套论文采样流程

也就是说，当前已经完成的是“GNSS -> PGO GPS 因子 -> 全局位姿约束”这条链，而不是“GPS 地图 -> Nav2 全自动远距离路线执行”这条链。

## 3. 当前运行事实

### 3.1 GNSS 数据链

```text
GNSS serial -> /fix -> gnss_calibration -> /gnss -> PGO GPS factor
```

### 3.2 室内行为

- `status=-1`
- 坐标为 `NaN`
- `gnss_calibration` 跳过 no-fix 样本

这些在室内都是预期现象，不应被误判为软件异常。

### 3.3 当前 Jetson 运行时痕迹

截至 2026-03-19，Jetson 上 `~/fyp_runtime_data/gnss/` 现状为：

- `startid.txt` 存在
- 有 `gnss_offset.invalid_*.txt`
- 还没有新的有效 `gnss_offset.txt`

这说明室外有效 fix 验证尚未完成。

## 4. 仍保留的设计方向

仓库内仍有这些 GPS 规划相关包，供后续继续开发：

- `gnss_global_path_planner`
- `global2local_tf`
- `gnss_calibration`

其中：

- `gnss_global_path_planner` 已有 GeoJSON + A* 规划框架
- `global2local_tf` 负责全局坐标到本地坐标映射相关试验
- 当前生产 bringup 仍以 `system_explore_gps.launch.py` 为主，不把上述规划链接入主导航流程

## 5. 当前主要阻塞

1. GPS 天线馈线更换前，无法做有效室外 fix 验证
2. 天气条件会直接影响户外采样窗口
3. GPS -> Nav2 目标点转换逻辑尚未定型

## 6. 推荐的下一步实车序列

1. 更换馈线并确认 GNSS 硬件链恢复
2. 启动 `make launch-explore-gps`
3. 确认 `/fix` 与 `/gnss` 都进入有效状态
4. 录制 rosbag 与 tegrastats
5. 导出 `/pgo/optimized_odom` 到 TUM
6. 做 GPS on/off A/B 对比

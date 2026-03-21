# FYP Autonomous Vehicle - Findings

**最后更新**: 2026-03-21

---

## Corridor v1 首次室外实车结论

- 车辆已能从固定 Launch Pose 自动出发，沿 corridor 到达目标附近
- 主要矛盾已从"能不能跑"转为"终点精度够不够"
- 末端几米级偏差，与普通单点 GNSS 会话级偏移一致
- corridor v1 适合作为稳定 baseline，后续增量改进

---

## 关键技术发现

### 为什么用 body_vector 而非 GPS 绝对坐标

- 普通 GNSS（2.5m 精度、无 RTK）跨会话存在：整体平移偏差 + 角度偏差 + 局部多路径扭曲
- **不能**假设历史 GPS 值跨会话精确对应同一物理点
- 正确做法：保存起终点**相对几何关系**（body_vector_m），运行时基于当前 map 位姿重建目标
- Nav2 消费 map frame 下的 `PoseStamped`，无需绕回绝对 GPS

### ENU → map 旋转问题（未解决 — 可能是误差来源）

- corridor v1 用 `body_vector_m`（车体坐标系）绕过了显式 ENU→map 旋转
- 假设：启动朝向固定 → map frame yaw0 近似确定 → body_vector 叠加即可
- 但 BMI088 IMU 无磁力计，FAST-LIO 初始 yaw 有不确定性
- **这可能是终点几米级误差的原因之一**
- 潜在解法：开走 5-8m 后用 GPS 位移 vs map 位移求旋转角（极简 yaw 校准）

### 官方资料佐证

- `robot_localization` 官方：带 GPS 的位置估计有离散跳变，不适合做局部导航唯一真值
- Nav2 GPS waypoint：能力存在，但前提是全局定位链可靠
- "顺序跑多个小目标"模式本身没问题，难点在于 GPS→导航坐标的稳定投影

---

## 已归档发现（v7 scene graph）

v7 方案调研结论已随方案废弃，核心结论：

- v7 主链（scene graph + route_server + Kabsch yaw）对单 corridor 需求过重
- v7 部署到 Jetson 后软件可启动，但被 GPS NO_FIX 阻塞实车验证
- GPS 蘑菇头硬件连接正常（ANTENNA OK），定位失败是室内环境/信号问题

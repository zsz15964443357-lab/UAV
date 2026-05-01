# UAV

本仓库用于推进硕士阶段研究工作：**基于多模态感知不确定性的无人机动态障碍物安全避障方法研究**。

当前目标不是单纯复现一个无人机避障项目，而是在 Intent-MPC / NavRL 等基础上，围绕“多模态感知结果不可靠时，无人机局部规划如何仍然安全”开展可发论文的实验对比。

## 研究主线

```text
Camera / RGB-D / LiDAR
        ↓
多模态动态障碍物状态估计
        ↓
不确定性建模：位置误差、速度误差、延迟、漏检、模态冲突
        ↓
安全局部规划：Intent-MPC / NavRL + safety shield
        ↓
实验评估：成功率、碰撞率、最小安全距离、规划耗时、鲁棒性曲线
```


## 多模态部分：具体采用的模态与融合方式

本课题采用**障碍物级多模态融合**，不是以端到端多模态大模型作为主线。多模态的作用是为动态障碍物提供更可靠的状态估计和不确定性表达，最终服务于安全局部规划。

主要模态：

- **LiDAR**：提供动态障碍物的三维位置、距离、几何尺寸、点云数量和空间置信度。优势是几何定位更可靠，缺点是点云稀疏、语义信息弱。
- **RGB-D / Camera**：提供 2D bbox、深度图距离、视觉检测置信度、语义类别和近距离跟踪信息。优势是语义信息强、近距离观测密集，缺点是受光照、遮挡、深度缺失和视野限制影响明显。

融合后的统一障碍物状态，输入来自伪多模态观测或 LV-DOT / onboard_detector：

```text
Obstacle {
  position          # 3D position from LiDAR/RGB-D fusion
  velocity          # estimated dynamic obstacle velocity
  radius            # physical obstacle radius or bbox-derived radius
  confidence        # fused detection/tracking confidence
  covariance        # position/velocity uncertainty
  source_modalities # lidar / rgbd / camera / fused
  effective_radius  # planning safety radius after uncertainty inflation
}
```

最小可行实现分两步：

1. **伪多模态阶段**：先从仿真 ground truth 生成两个受控观测源。
   - `pseudo_lidar_observation`：位置噪声较小，但点云稀疏时可能漏检，语义信息弱。
   - `pseudo_rgbd_observation`：近距离较准，远距离噪声更大，有 FOV 限制、检测置信度和漏检概率。
2. **真实感知接入阶段**：后续接入 LV-DOT / onboard_detector，将真实 LiDAR、RGB-D 或 Camera 的动态障碍物检测与跟踪结果转成上述统一状态。

多模态融合结果不直接作为论文终点，而是进入不确定性建模：

```text
LiDAR observation + RGB-D / Camera observation
        ↓
obstacle-level fusion
        ↓
position + velocity + confidence + covariance
        ↓
effective_radius / obstacle prediction tube
        ↓
uncertainty-aware safe local planning
```

因此，本课题的核心问题是：**当 LiDAR 与 RGB-D / Camera 的观测存在噪声、延迟、漏检或模态冲突时，规划器如何根据融合置信度和不确定性仍然保持安全避障。**

## 阶段 0：复现主线平台

目标：跑通 Intent-MPC 官方 demo，建立可复现实验环境。

任务：

- 确认 Ubuntu、ROS、Python、Gazebo、RViz、MAVROS 等环境版本。
- 克隆并编译 Intent-MPC。
- 启动官方 demo：
  - `roslaunch uav_simulator start.launch`
  - `roslaunch autonomous_flight intent_mpc_demo.launch`
- 记录 `rosnode list`、`rostopic list`、关键 launch 文件和参数文件。
- 确认 UAV、动态障碍物、规划轨迹和可视化是否正常。

验收标准：

- Intent-MPC 能编译通过。
- 官方 demo 能启动并看到无人机动态避障。
- 拿到关键 topic / launch / yaml / 模块列表。

## 阶段 1：梳理 Intent-MPC 数据流

目标：找到后续算法插入点。

重点定位：

- 动态障碍物状态在哪里生成。
- `dynamic_predictor` 的输入和输出。
- `trajectory_planner` / `time_optimizer` 中与动态障碍物避障相关的代价或约束。
- planner 接收的障碍物消息格式。
- 适合插入不确定性建模的位置。

阶段产出：

- 数据流说明文档。
- 关键文件清单。
- 初步修改方案：`obstacle_state -> uncertainty_obstacle_state -> planner`。

## 阶段 2：建立实验记录系统

目标：先记录论文指标，再修改算法。

需要记录的指标：

- `success`
- `collision`
- `min_distance`
- `path_length`
- `travel_time`
- `average_speed`
- `planning_time`
- 场景名、方法名、噪声、延迟、漏检率、随机种子

阶段产出：

- 实验 CSV 日志。
- 批量统计脚本。
- 成功率、碰撞率、最小安全距离等图表生成脚本。

## 阶段 3：实现感知退化模块

目标：模拟多模态感知在真实系统中的不可靠性。

设计一个 ROS 节点：

```text
原始/仿真 obstacle state
        ↓
perception_degradation_node
        ↓
degraded obstacle state
        ↓
planner
```

支持参数：

- `position_noise_std`
- `velocity_noise_std`
- `delay_ms`
- `dropout_prob`
- `false_positive_prob`
- `confidence_noise`
- `random_seed`

阶段产出：

- 可配置的感知退化节点。
- 不同延迟、噪声、漏检条件下的 baseline 实验结果。

## 阶段 4：加入多模态不确定性表示

目标：把 LiDAR 与 RGB-D / Camera 的障碍物级融合结果转化为可供规划使用的风险表达。

统一障碍物状态，输入来自伪多模态观测或 LV-DOT / onboard_detector：

```text
Obstacle {
  position
  velocity
  radius
  confidence
  covariance
  source_modalities
  effective_radius
}
```

有效安全半径：

```text
r_eff = r_obstacle
      + alpha * position_uncertainty
      + beta * velocity_uncertainty
      + gamma * perception_delay
      + delta * (1 - confidence)
```

阶段产出：

- `confidence / covariance / effective_radius` 计算逻辑。
- RViz 中原始障碍物半径和膨胀风险半径可视化。
- CSV 中记录每个障碍物的不确定性与风险半径。

## 阶段 5：改进安全局部规划器

目标：让规划器真正利用不确定性信息。

优先实现两种方式：

1. 约束膨胀：将动态障碍物半径从 `r` 改为 `r_eff`。
2. 风险代价：距离高不确定性障碍物越近，代价越高。

保留可切换模式：

- 原始 Intent-MPC。
- Intent-MPC + fixed safety margin。
- Uncertainty-aware Intent-MPC。

阶段产出：

- 不确定性感知安全规划模块。
- 原始方法与改进方法的同场景对比。
- 退化条件下的鲁棒性结果。

## 阶段 6：论文实验矩阵

对比方法：

- Intent-MPC。
- Intent-MPC + fixed safety margin。
- Ours: uncertainty-aware Intent-MPC。
- NavRL。
- 可选：NavRL + safety shield。

场景：

- 单个动态障碍物横穿。
- 正面相向动态障碍物。
- 多动态障碍物交叉运动。
- 遮挡后突然出现。
- 窄通道动态会车。

退化维度：

- 位置噪声：`0 / 0.1 / 0.2 / 0.3 m`
- 延迟：`0 / 100 / 200 / 300 ms`
- 漏检：`0 / 10% / 30% / 50%`
- 速度误差：`0 / 0.2 / 0.5 / 1.0 m/s`

阶段产出：

- `summary.csv`
- 成功率表。
- 碰撞率表。
- 最小安全距离曲线。
- 噪声、延迟、漏检对性能影响的折线图。

## 阶段 7：论文材料整理

目标：形成可写论文的完整材料。

需要整理：

- 系统框图。
- 方法流程图。
- 不确定性建模公式。
- 实验场景图。
- 对比实验表格。
- 消融实验。
- 失败案例分析。

暂定中文题目：

**基于多模态感知不确定性的无人机动态障碍物安全避障方法研究**

暂定英文题目：

**Uncertainty-Aware Safe Local Planning for UAV Dynamic Obstacle Avoidance with Multimodal Perception**

## 当前优先级

1. 完成阶段 0：Intent-MPC 环境复现。
2. 完成阶段 1：梳理动态障碍物数据流与规划插入点。
3. 在不改算法的前提下完成阶段 2：实验指标记录系统。

只有当日志系统稳定后，再进入感知退化和规划器修改。
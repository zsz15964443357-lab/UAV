# Stage 3 Execution Prompt

你现在要完成阶段 3：实现感知退化模块。

研究背景：本仓库用于硕士研究“基于多模态感知不确定性的无人机动态障碍物安全避障方法研究”。阶段 0 已复现 Intent-MPC 官方 demo，阶段 1 已梳理数据流，阶段 2 已完成实验指标记录系统。阶段 3 要在不改规划器算法的前提下，先构造可配置的感知退化输出，为阶段 4 的不确定性表示和阶段 5 的安全规划接入做准备。

约束：

- 不修改 Intent-MPC 的 MPC、控制器、动态预测器或原 fake detector 算法逻辑。
- 允许新增 ROS package、msg、launch、config、脚本和文档。
- 输出应能被后续阶段作为统一 obstacle state 的输入。
- 需要保持 ROS Noetic / Python 3 / catkin 可构建。
- 每次新阶段开始时，根据最新进度更新阶段内容、范围边界和 GitHub 跟踪状态。

任务：

1. 读取 GitHub `main` 最新 README，确认阶段 3 与多模态研究主线。
2. 从 `stage2-experiment-logging` 创建 `stage3-perception-degradation` 分支。
3. 新增 ROS 包 `perception_degradation`。
4. 定义消息：
   - `DegradedObstacle.msg`
   - `DegradedObstacleArray.msg`
5. 实现 `perception_degradation_node.py`：
   - 订阅 `/gazebo/model_states`。
   - 筛选 `person`、`dynamic_box`、`dynamic_cylinder`。
   - 解析障碍物位置、速度、尺寸和半径。
   - 支持 `position_noise_std`。
   - 支持 `velocity_noise_std`。
   - 支持 `delay_ms`。
   - 支持 `dropout_prob`。
   - 支持 `false_positive_prob`。
   - 支持 `confidence_noise`。
   - 支持 `random_seed` 以保证可复现实验。
   - 发布退化后的障碍物数组 topic。
   - 发布 RViz marker。
   - 可选写入逐障碍物 CSV。
6. 增加 launch/config：
   - `stage3_default.yaml`
   - `run_degradation.launch`
   - `run_degradation_with_recorder.launch`
7. 写阶段 3 文档：
   - 使用方式。
   - 参数说明。
   - 输出 topic / CSV。
   - 当前阶段边界：只生成退化感知，不接入 MPC。
   - 后续阶段如何接入 Stage 4 和 Stage 5。
8. 验证：
   - `python3 -m py_compile perception_degradation/scripts/perception_degradation_node.py`
   - Docker / ROS Noetic 内 `catkin_make`
   - `roslaunch perception_degradation run_degradation.launch --nodes`
   - ROS smoke test：发布合成 `/gazebo/model_states`，确认输出 degraded topic、marker、CSV。
9. 提交并推送到 GitHub，创建 PR，更新 Stage 3 issues/milestone。

验收标准：

- 新包能被 catkin 发现并构建。
- 退化节点能发布 `/perception_degradation/degraded_obstacles`。
- 参数对输出有实际影响。
- 能生成 RViz marker 和 CSV。
- 不改变官方 demo 的规划行为。

# Stage 4 Execution Prompt

你现在要完成阶段 4：加入多模态不确定性表示。

研究背景：本仓库用于硕士研究“基于多模态感知不确定性的无人机动态障碍物安全避障方法研究”。阶段 0 已复现平台，阶段 1 已梳理 Intent-MPC 数据流，阶段 2 已建立实验日志系统，阶段 3 已实现感知退化模块。阶段 4 要把退化后的障碍物观测转成统一的不确定性障碍物状态，为阶段 5 的安全规划器接入做准备。

约束：

- 不修改 Intent-MPC 的 planner/controller/detector/predictor 算法逻辑。
- 只新增不确定性表示 package、msg、launch、config、脚本和文档。
- 不在阶段 4 中让 MPC 使用 `effective_radius`；这属于阶段 5。
- 每次新阶段开始时，根据当前完成度更新阶段内容、边界和项目管理文档。

任务：

1. 读取 GitHub `main` 最新 README，确认阶段 4 多模态不确定性要求。
2. 从 `stage3-perception-degradation` 创建 `stage4-multimodal-uncertainty` 分支。
3. 新增 ROS 包 `multimodal_uncertainty`。
4. 定义统一不确定性障碍物消息：
   - `position`
   - `velocity`
   - `radius`
   - `confidence`
   - `position_covariance`
   - `velocity_covariance`
   - `position_uncertainty`
   - `velocity_uncertainty`
   - `perception_delay`
   - `source_modalities`
   - `effective_radius`
5. 实现 `uncertainty_obstacle_node.py`：
   - 订阅 `/perception_degradation/degraded_obstacles`。
   - 读取每个障碍物的半径、置信度、位置噪声、速度噪声和延迟。
   - 生成协方差矩阵。
   - 计算有效安全半径：

```text
r_eff = r_obstacle
      + alpha * position_uncertainty
      + beta * velocity_uncertainty
      + gamma * perception_delay_ms
      + delta * (1 - confidence)
```

6. 发布：
   - `/multimodal_uncertainty/uncertainty_obstacles`
   - `/multimodal_uncertainty/uncertainty_markers`
7. RViz marker 要同时显示：
   - 原始半径。
   - 膨胀后的风险半径。
   - 简短文字：`r / r_eff / confidence`。
8. 记录 CSV：
   - 每个障碍物的置信度、协方差、位置/速度不确定性、延迟、`risk_margin`、`effective_radius`。
9. 增加 launch/config：
   - `stage4_default.yaml`
   - `run_uncertainty.launch`
   - `run_stage4_pipeline.launch`
10. 写阶段 4 文档：
   - prompt。
   - 设计说明。
   - 使用方式。
   - 验证结果。
   - 当前阶段边界：只输出不确定性表达，不接入 MPC。
11. 验证：
   - Python 语法检查。
   - Docker / ROS Noetic 内 `catkin_make`。
   - `roslaunch multimodal_uncertainty run_uncertainty.launch --nodes`。
   - ROS smoke test：发布合成 degraded obstacles，确认 uncertainty topic、marker、CSV。
12. 提交、推送分支，创建 PR，更新 Stage 4 issues/milestone。

验收标准：

- `multimodal_uncertainty` 能被 catkin 构建。
- `UncertaintyObstacle` 消息包含置信度、协方差和有效半径。
- `effective_radius` 计算符合阶段 4 公式。
- RViz marker 可显示原始半径和膨胀风险半径。
- CSV 记录每个障碍物的不确定性与风险半径。
- 不改变官方 demo 的规划行为。

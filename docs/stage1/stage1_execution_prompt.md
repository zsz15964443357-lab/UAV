# Stage 1 Execution Prompt

Use this prompt when asking an AI coding/research agent to reproduce or extend the Stage 1 code-reading work.

```text
你是一个严谨的软件工程和机器人研究助手。当前仓库是 Intent-MPC 的复现分支，用于论文方向：

“基于多模态感知不确定性的无人机动态障碍物安全避障方法研究”。

当前任务是完成 Stage 1：梳理 Intent-MPC 数据流，目标是找到后续接入多模态感知不确定性和安全规划改进的最小插入点。

约束：
- 不修改算法代码。
- 不修改 planner 行为。
- 只做代码阅读、运行接口梳理和文档输出。
- 所有结论都要绑定到具体文件、函数和必要的行号。
- 若发现阶段 0 稳定性修复，只记录其影响，不把它描述成算法创新。

仓库路径：
`/home/ubuntu2204/catkin_ws/src/Intent-MPC`

已知阶段 0 状态：
- Docker ROS Noetic 环境可运行。
- 官方 demo 可启动：
  - `roslaunch uav_simulator start.launch`
  - `roslaunch autonomous_flight intent_mpc_demo.launch`
- 轻量可视化入口：
  - `roslaunch autonomous_flight intent_mpc_demo_fast_visual.launch`
- 阶段 0 报告：
  - `docs/stage0/Intent_MPC_stage0_report.md`

Stage 1 需要完成的问题：

1. launch 和运行时模块图
   - 阅读：
     - `uav_simulator/launch/start.launch`
     - `autonomous_flight/launch/intent_mpc_demo.launch`
     - `autonomous_flight/launch/intent_mpc_demo_fast_visual.launch`
     - `tracking_controller/launch/tracking_controller.launch`
   - 输出：
     - Gazebo/UAV/TF/RViz 如何启动。
     - `mpc_navigation_node`、`tracking_controller_node`、Gazebo plugin 的关系。
     - 关键 ROS topic：UAV odom、target state、cmd_acc、MPC trajectory、dynamic obstacle visualization。

2. 动态障碍物来源
   - 阅读：
     - `onboard_detector/include/onboard_detector/fakeDetector.cpp`
     - `onboard_detector/include/onboard_detector/fakeDetector.h`
     - `onboard_detector/include/onboard_detector/utils.h`
     - `map_manager/include/map_manager/dynamicMap.cpp`
     - `map_manager/include/map_manager/dynamicMap.h`
   - 输出：
     - 官方 demo 的动态障碍物来自 `/gazebo/model_states`。
     - fake detector 如何筛选 `person` / `dynamic_box` / `dynamic_cylinder`。
     - `box3D` 字段含义。
     - fake detector 如何计算位置、速度、加速度、尺寸和历史轨迹。

3. `dynamic_predictor` 输入输出
   - 阅读：
     - `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.cpp`
     - `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.h`
     - `dynamic_predictor/include/dynamic_predictor/utils.h`
     - `autonomous_flight/cfg/mpc_navigation/predictor_param.yaml`
   - 输出：
     - 输入历史：`posHist_`、`velHist_`、`accHist_`、`sizeHist_`。
     - 输出格式：`predPos[obstacle][intent][time_step]`、`predSize[...]`、`intentProb[obstacle]`。
     - 意图类型：`FORWARD`、`LEFT`、`RIGHT`、`STOP`。
     - 预测结果如何通过 `getPrediction()` 给 MPC。

4. MPC 动态障碍物处理
   - 阅读：
     - `autonomous_flight/include/autonomous_flight/mpcNavigation.cpp`
     - `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp`
     - `trajectory_planner/include/trajectory_planner/mpcPlanner.h`
     - `autonomous_flight/cfg/mpc_navigation/planner_param.yaml`
   - 输出：
     - `use_predictor=true` 时的数据链：
       `predictor_->getPrediction -> mpc_->updatePredObstacles -> mpc_->makePlanWithPred`
     - `use_predictor=false` 时的数据链：
       `getDynamicObstacles -> mpc_->updateDynamicObstacles -> mpc_->makePlan`
     - `updatePredObstacles` 如何整理预测障碍物。
     - `getIntentComb` 如何构造候选 intent 组合。
     - `solveTraj` 如何把障碍物转成 QP 约束。
     - `updateObstacleParam` 中动态障碍物安全半径如何由尺寸和 `dynamicSafetyDist_` 构造。

5. 插入点设计
   - 给出至少 3 个候选：
     - detector/map 和 predictor 之间。
     - predictor 和 MPC 之间。
     - MPC obstacle constraint construction 内部。
   - 对每个候选写明：
     - 适合哪个阶段。
     - 优点。
     - 风险。
     - 需要改哪些文件。
   - 最后给出推荐路线：
     - Stage 2 先做日志系统。
     - Stage 3 做感知退化节点。
     - Stage 4 定义 uncertainty obstacle schema。
     - Stage 5 先接入 effective radius / fixed margin，再考虑风险代价。

输出文件：
- `docs/stage1/stage1_final_report.md`
- `docs/stage1/insertion_point_design.md`
- 必要时更新 `docs/stage1/README.md`

验收标准：
- launch tree 和 runtime node graph 已记录。
- UAV pose/velocity/control/planning topics 已记录。
- 动态障碍物生成路径已记录。
- `dynamic_predictor` 输入输出格式已记录。
- MPC 动态障碍物约束路径已记录。
- 候选插入点已排序。
- 阶段 1 最终报告完成。
```


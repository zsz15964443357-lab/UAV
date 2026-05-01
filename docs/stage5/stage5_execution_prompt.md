# Stage 5 Execution Prompt

你现在要完成阶段 5：改进安全局部规划器。

研究背景：阶段 0 已复现 Intent-MPC，阶段 1 已梳理数据流，阶段 2 已建立实验日志系统，阶段 3 已实现感知退化模块，阶段 4 已实现多模态不确定性障碍物表示。阶段 5 要让局部规划器真正利用安全裕度或不确定性半径，但必须保留原始 Intent-MPC 可切换模式。

约束：

- 默认行为必须保持原始 Intent-MPC。
- 不删除原仓库文件。
- 尽量只在 `autonomous_flight/mpcNavigation` 入口层接入，不重写 MPC 求解器。
- 至少实现：
  - `original`
  - `fixed_margin`
  - `uncertainty_aware`
- 风险代价项可以先作为后续增强；本阶段优先完成可验证的半径/尺寸膨胀路径。
- 每次新阶段开始时，根据当前实现程度更新阶段内容、边界和项目管理文档。

任务：

1. 读取 GitHub `main` 最新 README，确认阶段 5 要求。
2. 从 `stage4-multimodal-uncertainty` 创建 `stage5-safety-local-planner` 分支。
3. 找到动态障碍物进入 MPC 的路径：
   - `mpcNavigation::mpcCB`
   - `mpc_->updateDynamicObstacles`
   - `mpc_->updatePredObstacles`
   - `mpcNavigation::hasDynamicCollision`
4. 在 `autonomous_flight` 增加参数：
   - `dynamic_obstacle_mode`
   - `fixed_safety_margin`
   - `uncertainty_obstacles_topic`
   - `uncertainty_size_mode`
   - `uncertainty_max_age`
   - `uncertainty_association_distance`
   - `uncertainty_fallback_to_original`
5. 实现 `fixed_margin`：
   - 对当前动态障碍物尺寸加 `2 * fixed_safety_margin`。
   - 对 predictor 输出的预测尺寸同样加 `2 * fixed_safety_margin`。
6. 实现 `uncertainty_aware`：
   - 订阅 `/multimodal_uncertainty/uncertainty_obstacles`。
   - 非 predictor 路径直接使用 uncertainty obstacle position/velocity/size。
   - predictor 路径通过最近邻匹配，把 `effective_radius` 映射到预测障碍物尺寸。
   - 如果 uncertainty 消息过期且允许 fallback，则回退原始路径。
7. 增加 launch：
   - `intent_mpc_demo_fixed_margin.launch`
   - `intent_mpc_demo_uncertainty.launch`
8. 写阶段 5 文档：
   - prompt。
   - 设计说明。
   - 使用方式。
   - 验证结果。
   - 当前阶段边界：完成半径/尺寸膨胀，风险代价项后续再做。
9. 验证：
   - Docker / ROS Noetic 内 `catkin_make`。
   - `roslaunch autonomous_flight intent_mpc_demo_fixed_margin.launch --nodes`。
   - `roslaunch autonomous_flight intent_mpc_demo_uncertainty.launch --nodes`。
   - 必要时做 ROS 参数/订阅 smoke test。
10. 提交、推送分支，创建 PR，更新 Stage 5 issues/milestone。

验收标准：

- 原始 demo 默认仍是 `original` 模式。
- fixed-margin launch 可解析并加载参数。
- uncertainty-aware launch 可解析并启动 Stage 3/4 管线。
- catkin 构建通过。
- 代码路径覆盖 predictor 和 non-predictor 两种动态障碍物更新方式。

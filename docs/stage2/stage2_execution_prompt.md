# Stage 2 Execution Prompt

你现在要完成阶段 2：建立实验记录系统。

研究背景：本仓库用于硕士研究“基于多模态感知不确定性的无人机动态障碍物安全避障方法研究”。阶段 0 已复现 Intent-MPC 官方 demo，阶段 1 已梳理动态障碍物数据流和后续不确定性建模插入点。阶段 2 的目标是在修改算法前，先建立稳定、可复现、可批量统计的实验指标记录系统。

约束：

- 不修改 Intent-MPC、MPC、控制器、动态预测器或检测器的算法逻辑。
- 只新增日志、统计、绘图、文档和 launch/config 辅助文件。
- 记录字段要服务于后续多模态不确定性实验，至少预留位置噪声、速度噪声、延迟、漏检率、误检率、置信度噪声和随机种子。
- 所有工具应能在 ROS Noetic / Python 3 下运行。
- 操作完成后需要本地验证：Python 语法检查、catkin 构建检查、CSV 汇总脚本基本功能检查。

任务：

1. 从 GitHub 最新 `main` 的 README 读取阶段计划，确认阶段 2 要求和多模态字段。
2. 从 `stage1-code-reading-baseline` 创建 `stage2-experiment-logging` 分支。
3. 新增独立 ROS 包 `experiment_tools`。
4. 实现 `experiment_metric_recorder.py`：
   - 订阅 `/CERLAB/quadcopter/odom` 记录 UAV 位姿和轨迹长度。
   - 订阅 `/gazebo/model_states` 读取 Gazebo 动态障碍物真值。
   - 根据动态障碍物模型名筛选 `person`、`dynamic_box`、`dynamic_cylinder`。
   - 计算 `min_distance`、`collision`、`path_length`、`travel_time`、`average_speed`。
   - 保留 `planning_time` 字段；如果没有规划耗时 topic，则写入 `nan` 并标明来源不可用。
   - 在节点退出时追加一行 run-level CSV。
   - 可选写入 sample-level CSV。
5. 实现 `summarize_runs.py`：
   - 按场景、方法、噪声、延迟、漏检率、随机种子等字段聚合。
   - 输出成功率、碰撞率、平均/最小安全距离、平均路径长度、平均耗时、平均速度、规划耗时统计。
6. 实现 `plot_metrics.py`：
   - 从 summary CSV 生成成功率、碰撞率、最小安全距离图，优先使用标准库生成 SVG，避免 matplotlib/NumPy 版本不兼容影响复现。
7. 增加 `record_baseline.launch` 和默认 YAML 参数。
8. 写阶段 2 文档：
   - 使用方式。
   - 指标定义。
   - 当前无法准确测量 `planning_time` 的原因。
   - 后续阶段如何扩展到伪多模态感知退化实验。
9. 运行验证：
   - `python3 -m py_compile ...`
   - 构造小 CSV 测试 `summarize_runs.py`
   - 若 ROS/Docker 环境可用，运行 `catkin_make`
10. 提交并推送到 GitHub，更新对应 Stage 2 issues/milestone。

验收标准：

- `experiment_tools` 可被 catkin 发现并构建。
- `roslaunch experiment_tools record_baseline.launch` 可在 demo 运行时记录 CSV。
- 至少能生成 run CSV、summary CSV 和三类 SVG 图脚本。
- Stage 2 不改变官方 demo 的避障行为。

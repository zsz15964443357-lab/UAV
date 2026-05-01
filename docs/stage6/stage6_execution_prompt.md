# Stage 6 Execution Prompt

你现在要完成阶段 6：论文实验矩阵与批量统计工具。

研究背景：阶段 0 已复现 Intent-MPC，阶段 1 已梳理数据流，阶段 2 已建立实验记录系统，阶段 3 已实现感知退化，阶段 4 已实现不确定性障碍物表示，阶段 5 已接入 `original`、`fixed_margin`、`uncertainty_aware` 三种局部规划模式。阶段 6 的目标不是继续改规划算法，而是把论文实验所需的“方法 × 场景 × 退化维度 × 随机种子”批量实验流程落地。

约束：

- 不修改 Stage 5 的避障算法逻辑。
- 不删除原仓库文件。
- 默认保留官方 Intent-MPC 行为。
- 批量实验应支持 headless Gazebo，避免不必要的 RViz/Gazebo GUI 负担。
- NavRL 尚未接入本仓库时，只保留 disabled 占位，不生成可执行 NavRL run。
- 每次新阶段开始时，根据当前实现程度更新阶段内容、边界和项目管理文档。

任务：

1. 读取 `uav/main` README 中阶段 6 要求。
2. 从 `stage5-safety-local-planner` 创建 `stage6-paper-experiment-matrix` 分支。
3. 定义实验矩阵配置：
   - 方法：Intent-MPC、Intent-MPC + fixed safety margin、uncertainty-aware Intent-MPC。
   - 预留方法：NavRL、NavRL + safety shield，默认 disabled。
   - 场景：单动态障碍物横穿、正面/走廊、多个障碍物交叉、遮挡/复杂平面、窄通道会车。
   - 退化维度：位置噪声、速度噪声、延迟、漏检率。
   - 随机种子。
4. 增加 headless 仿真 launch：
   - 可传 `world_name`。
   - 默认不启动 Gazebo GUI。
   - 默认不启动 keyboard control。
5. 增加 Stage 6 planner launch：
   - 可传 `dynamic_obstacle_mode`。
   - 可开关 Stage 3/4 uncertainty pipeline。
   - 可开关 RViz。
6. 扩展 recorder 元数据字段：
   - `world_name`
   - `planner_mode`
   - `fixed_safety_margin`
   - `degradation_axis`
   - `degradation_value`
7. 实现工具脚本：
   - `generate_stage6_manifest.py`
   - `run_stage6_batch.py`
   - `analyze_stage6_results.py`
8. 生成文档：
   - 使用方式。
   - 实验矩阵设计。
   - 验证结果。
   - 当前阶段边界。
9. 验证：
   - Python 语法检查。
   - manifest 生成。
   - dry-run 命令生成。
   - synthetic CSV 分析输出 summary/table/SVG。
   - Docker ROS Noetic 内 `catkin_make`。
   - 关键 launch `--nodes`。
   - 1 条短时 headless pilot run 写出 CSV。
10. 提交、推送分支，创建 PR，更新 Stage 6 issues/milestone。

验收标准：

- 能生成 Stage 6 manifest CSV。
- 能打印或执行批量实验命令。
- 能从 Stage 6 run CSV 生成 summary CSV、method comparison table、robustness table、SVG 曲线。
- Headless launch 可解析。
- `catkin_make` 通过。
- 至少 1 条 pilot run 能写出 `stage6_runs.csv`。

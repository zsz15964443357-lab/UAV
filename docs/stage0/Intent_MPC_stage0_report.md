# Intent-MPC 阶段 0 复现报告

时间：2026-04-30
工作空间：`/home/ubuntu2204/catkin_ws`
仓库：`/home/ubuntu2204/catkin_ws/src/Intent-MPC`
commit：`f9d050c981a3b7b0ef8dc34f83fc4ede194c0fd0`
详细日志目录：`/home/ubuntu2204/catkin_ws/intent_mpc_stage0_logs`

## 1. 环境信息

### 宿主机

检查日志：`intent_mpc_stage0_logs/39_host_environment_check.log`、`40_host_dependency_packages.log`

- Ubuntu：22.04.5 LTS `jammy`
- Kernel：`6.8.0-107-generic`
- Python：3.10.12
- ROS：ROS2 Humble，`ROS_DISTRO=humble`，`ROS_VERSION=2`
- `catkin_make`：宿主机未安装
- Gazebo：宿主机有 `gz` / Gazebo Harmonic，不是 ROS1 Gazebo Classic
- RViz：宿主机有 `rviz2`，无 RViz1
- ROS1 MAVROS / octomap ROS / vision_msgs：宿主机不满足 Intent-MPC 官方 ROS1 依赖
- catkin 工作空间：`/home/ubuntu2204/catkin_ws`

结论：宿主机是 Ubuntu 22.04 + ROS2，不满足 README 推荐的 Ubuntu 18.04/20.04 + ROS Melodic/Noetic。按用户授权，使用 Docker 提供 ROS1 Noetic 环境。

### Docker ROS1 运行环境

镜像：`intent-mpc:noetic-stage0`
Dockerfile：`/home/ubuntu2204/catkin_ws/intent_mpc_stage0_docker/Dockerfile`
检查日志：`intent_mpc_stage0_logs/06_container_env_check.log`、`11_container_runtime_env_x11.log`

- Ubuntu：20.04.6 LTS `focal`
- ROS：Noetic
- Python：3.8.10
- Gazebo Classic：11.15.1
- RViz1：已安装
- `catkin_make` / `roslaunch`：已安装
- 依赖已验证：
  - `gazebo_ros`
  - `mavros`
  - `mavros_extras`
  - `octomap_ros`
  - `octomap_server`
  - `vision_msgs`

图形环境：

- 使用宿主机 X11：`DISPLAY=:0`
- 使用宿主机 Xauthority：`/run/user/1000/.mutter-Xwaylandauth.3JIKO3`
- OpenGL：容器内 `llvmpipe` 软件渲染，`glxinfo -B` 成功
- 必要运行环境变量：
  - `LIBGL_ALWAYS_SOFTWARE=1`
  - `QT_X11_NO_MITSHM=1`
  - `XDG_RUNTIME_DIR=/tmp/runtime-intent`
  - `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus`

## 2. 安装与编译步骤

### 工作空间和仓库

```bash
mkdir -p /home/ubuntu2204/catkin_ws/src
cd /home/ubuntu2204/catkin_ws/src
git clone https://github.com/Zhefan-Xu/Intent-MPC.git
```

实际仓库 commit：

```bash
git -C /home/ubuntu2204/catkin_ws/src/Intent-MPC rev-parse HEAD
# f9d050c981a3b7b0ef8dc34f83fc4ede194c0fd0
```

### Docker 环境

宿主机直接编译失败，因为没有 ROS1/catkin：

```bash
catkin_make
# catkin_make: command not found
```

随后安装 Docker，并构建 ROS Noetic 镜像：

```bash
sudo apt install docker.io
sudo docker build -t intent-mpc:noetic-stage0 /home/ubuntu2204/catkin_ws/intent_mpc_stage0_docker
```

构建中遇到的问题：

- 第一次 Dockerfile 使用 HTTPS Ubuntu 源时，基础镜像缺 CA 证书，apt 证书校验失败。
- `rosdep init || true` 的 shell 运算符优先级曾掩盖前面的失败，修正为 `(rosdep init || true)`。
- USTC ROS key URL `http://mirrors.ustc.edu.cn/ros/ros.key` 返回 404，改用 `https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc`。

最终镜像构建成功：

```bash
sudo docker image ls
# intent-mpc:noetic-stage0 e9796da330db 6.18GB
```

### catkin 编译

容器内编译命令：

```bash
cd /home/intent/catkin_ws
source /opt/ros/noetic/setup.bash
catkin_make
```

第一次编译失败：

```text
fatal error: uav_simulator/LivoxCustomMsg.h: No such file or directory
```

判断：并行编译时 `livox_laser` 先于自定义 message header 生成，是构建顺序问题。未修改算法代码，直接重跑 `catkin_make`。

第二次编译成功：

```text
[100%] Built target mpc_navigation_node
```

编译日志：

- 首次失败：`intent_mpc_stage0_logs/07_catkin_make.log`
- 重跑成功：`intent_mpc_stage0_logs/08_catkin_make_rerun.log`

非致命 warning：

- PCL/VTK imported target warning
- PCL I/O 部分可选功能缺少 `pcap/png/libusb`
- `catkin_package() DEPENDS system_lib` 未定义提示

以上 warning 未阻止编译。

## 3. Demo 启动命令

官方 README 命令：

```bash
roslaunch uav_simulator start.launch
roslaunch autonomous_flight intent_mpc_demo.launch
```

本机 Docker 运行时实际使用：

```bash
sudo docker run -dit --name intent_mpc_stage0 --network host --ipc=host \
  -e DISPLAY=$DISPLAY \
  -e XAUTHORITY=$XAUTHORITY \
  -e QT_X11_NO_MITSHM=1 \
  -e LIBGL_ALWAYS_SOFTWARE=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v /run/user/1000:/run/user/1000:ro \
  -v /home/ubuntu2204/catkin_ws:/home/intent/catkin_ws \
  intent-mpc:noetic-stage0 bash
```

容器内启动环境：

```bash
source /opt/ros/noetic/setup.bash
source /home/intent/catkin_ws/devel/setup.bash
source /home/intent/catkin_ws/src/Intent-MPC/uav_simulator/gazeboSetup.bash
export GAZEBO_MODEL_DATABASE_URI=""
export XDG_RUNTIME_DIR=/tmp/runtime-intent
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
```

启动命令：

```bash
roslaunch uav_simulator start.launch
roslaunch autonomous_flight intent_mpc_demo.launch
```

## 4. Demo 验证结果

### GUI 与模型

- Gazebo：正常打开。`wmctrl` 记录到 `Gazebo` 窗口。
- RViz：正常打开。`wmctrl` 记录到 `mpc_navigation.rviz - RViz` 窗口。
- UAV：`spawn_model` 返回 `SpawnModel: Successfully spawned entity`。
- 动态障碍物：`/gazebo/model_states` 中有 122 个模型，包括 `dynamic_cylinder_0...39` 和 `dynamic_box_0...39`。
- 运动障碍物：采样中 81 个模型发生移动，动态障碍物中心位移可达 5m 以上。

证据日志：

- GUI：`21_wmctrl_windows_after_demo.log`
- 截图：`26_demo_gui_screenshot.png`
- Gazebo 模型与动态障碍物：`22_runtime_motion_sampler.log`

### UAV 运动

第一次完整运行中，UAV 在 20 秒采样窗口内发生明显运动：

```text
UAV_ODOM_START (-4.513, -5.233, 0.503)
UAV_ODOM_END   (2.296, -5.987, 0.797)
UAV_ODOM_TOTAL_DIST 8.361
```

说明：UAV 能起飞并沿参考路径运动，且期间动态障碍物持续移动。

### 关键问题

官方 demo 未稳定完成。第一次运行约 3 分钟后出现：

```text
[AutoFlight]: Collision detected. MPC replan.
[AutoFlight]: Goal reached. 9 rounds left.
[AutoFlight]: MPC collision detected!
[mpc_navigation_node-2] process has died [pid 1290, exit code -11]
```

随后：

- `/mpc_navigation_node` 在 `rosnode list` 中仍有残留，但 `rosnode ping` 返回 `connection refused`
- `/CERLAB/quadcopter/odom` 的位置变为 `(0,0,0)`，速度为 `nan`
- `tf_echo map base_link` 后续只得到零位姿

关键日志：

- demo 输出：`18_intent_mpc_demo_runtime.log`
- 节点退出：容器 ROS log 中 `roslaunch-ubuntu2204-virtual-machine-1272.log`
- 节点 ping：`25_rosnode_ping_after_mpc_exit.log`
- odom/TF/hz：`27_tf_echo_map_base_link.log`、`28_rostopic_hz_basic.log`

复跑验证中也出现 `MPC collision detected!` 后 `/mpc_navigation_node` 不可 ping，说明该问题可复现，不是一次性 GUI 问题。

### Topic 频率

崩溃后基础仿真 topic 仍在发布：

```text
/CERLAB/quadcopter/odom   ~22 Hz
/gazebo/model_states      ~1000 Hz
/tf                       ~29 Hz
```

日志：`28_rostopic_hz_basic.log`

## 5. ROS 节点与 Topic

### rosnode list

demo 正常启动阶段记录：

```text
/baselink_cameralink
/gazebo
/gazebo_gui
/gt_acc_throttle
/gt_odom_throttle
/gt_pose_throttle
/gt_vel_throttle
/keyboard_control
/mpc_navigation_node
/quadcopterTF
/rosout
/rviz1
/tracking_controller_node
```

日志：`19_rosnode_list_after_demo.log`

注意：`mpc_navigation_node` 崩溃后会在 master 中短暂残留，必须用 `rosnode ping /mpc_navigation_node` 判断真实存活状态。

### 关键 topic

UAV 状态与控制：

- `/CERLAB/quadcopter/pose`：`geometry_msgs/PoseStamped`
- `/CERLAB/quadcopter/odom`：`nav_msgs/Odometry`
- `/CERLAB/quadcopter/vel`：`geometry_msgs/TwistStamped`
- `/CERLAB/quadcopter/cmd_acc`：`mavros_msgs/PositionTarget`
- `/CERLAB/quadcopter/cmd_vel`
- `/CERLAB/quadcopter/setpoint_pose`
- `/CERLAB/quadcopter/takeoff`
- `/CERLAB/quadcopter/land`

规划与轨迹：

- `/autonomous_flight/target_state`：`tracking_controller/Target`
- `/mpcNavigation/mpc_trajectory`：`nav_msgs/Path`
- `/mpcNavigation/input_trajectory`：`nav_msgs/Path`
- `/mpcNavigation/pwl_trajectory`：`nav_msgs/Path`
- `/mpcNavigation/rrt_path`
- `/mpcNavigation/poly_traj`
- `/mpc_planner/mpc_trajectory`：`nav_msgs/Path`
- `/mpc_planner/traj_history`：`nav_msgs/Path`
- `/mpc_planner/candidate_trajectories`
- `/mpc_planner/local_cloud`：`sensor_msgs/PointCloud2`
- `/mpc_planner/static_obstacles`：`visualization_msgs/MarkerArray`
- `/mpc_planner/dynamic_obstacles`：`visualization_msgs/MarkerArray`

动态障碍物感知与预测：

- `/onboard_detector/GT_obstacle_bbox`
- `/onboard_detector/dynamic_bboxes`
- `/onboard_detector/tracked_bboxes`
- `/onboard_detector/filtered_bboxes`
- `/onboard_detector/dynamic_point_cloud`
- `/dynamic_predictor/predict_trajectories`
- `/dynamic_predictor/intent_probability`
- `/dynamic_predictor/pred_bbox`
- `/dynamic_predictor/var_points`
- `/dynamic_predictor/history_trajectories`

地图与仿真：

- `/dynamic_map/voxel_map`
- `/dynamic_map/inflated_voxel_map`
- `/dynamic_map/2D_occupancy_map`
- `/dynamic_map/depth_cloud`
- `/gazebo/model_states`
- `/gazebo/link_states`
- `/tf`
- `/tf_static`

完整 topic 列表：`20_rostopic_list_after_demo.log`
topic 类型与发布/订阅关系：`23_relevant_topic_types_info.log`

## 6. 主要 launch / yaml / 模块

### launch 文件

- `uav_simulator/launch/start.launch`
  - 启动 Gazebo world
  - spawn `quadcopter`
  - 启动 Gazebo GUI
  - 启动 pose/vel/acc/odom throttle
  - 启动 UAV TF broadcaster
  - 启动 Qt keyboard controller

- `autonomous_flight/launch/intent_mpc_demo.launch`
  - 加载 tracking controller、flight base、MPC planner、mapping、detector、predictor 参数
  - 启动 `tracking_controller_node`
  - 启动 `mpc_navigation_node`
  - include RViz：`remote_control/launch/mpc_navigation_rviz.launch`

### 主要参数文件

- `tracking_controller/cfg/controller_param.yaml`
- `autonomous_flight/cfg/mpc_navigation/flight_base.yaml`
- `autonomous_flight/cfg/mpc_navigation/planner_param.yaml`
- `autonomous_flight/cfg/mpc_navigation/mapping_param.yaml`
- `autonomous_flight/cfg/mpc_navigation/fake_detector_param.yaml`
- `autonomous_flight/cfg/mpc_navigation/dynamic_detector_param.yaml`
- `autonomous_flight/cfg/mpc_navigation/predictor_param.yaml`

### 模块功能概览

- `uav_simulator`：Gazebo world、UAV 插件、动态障碍物插件、相机/深度/点云仿真、键盘控制、TF。
- `tracking_controller`：接收 `autonomous_flight/target_state`，输出 UAV 控制命令到仿真接口。
- `autonomous_flight`：demo 主流程，起飞、参考轨迹执行、MPC 导航、规划重规划逻辑。
- `map_manager`：占据地图、动态地图、预构建地图加载与地图可视化。
- `onboard_detector`：fake detector / dynamic detector，输出动态障碍物 bbox、点云和跟踪结果。
- `dynamic_predictor`：对动态障碍物轨迹和 intent probability 做预测。
- `trajectory_planner`：MPC 局部规划、候选轨迹、静态/动态障碍物约束。
- `global_planner`：RRT/RRT* 类全局路径规划工具。
- `remote_control`：RViz 配置和可视化启动。

## 7. 遇到的问题和处理

1. 宿主机没有 ROS1/catkin
   - 处理：使用 Docker 构建 Ubuntu 20.04 + ROS Noetic 环境。

2. Docker 构建初期 apt 源和 ROS key 问题
   - 处理：改 Dockerfile，先装 CA，再使用 ROS 官方 `ros.asc`；保留 Dockerfile 在 `intent_mpc_stage0_docker/Dockerfile`。

3. 首次 `catkin_make` 缺 `LivoxCustomMsg.h`
   - 处理：不改源码，重跑 `catkin_make`，message header 生成后编译成功。

4. 初次 Gazebo GUI / keyboard controller abort
   - 现象：`gazebo_gui` 和 `keyboard_control` exit 134。
   - 原因：容器内 Qt/Gazebo 没有宿主机 D-Bus session 地址。
   - 处理：增加 `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus`，并设置可写 `XDG_RUNTIME_DIR=/tmp/runtime-intent`。

5. 官方 demo 运行中 `mpc_navigation_node` 崩溃
   - 现象：`MPC collision detected!` 后 `mpc_navigation_node` exit code `-11`，之后 odom 速度为 `nan`。
   - 处理：阶段 0 不修改算法代码，因此仅记录问题；该问题阻止“稳定完成官方 demo”验收。

6. 辅助采样脚本错误
   - `35_clean_active_window_sampler.log` 中的 `bad callback` 是我写的采样脚本 TypeError，不属于 Intent-MPC 节点错误；该日志不作为核心验收依据。

## 8. 下一阶段建议重点阅读文件

建议先围绕官方 demo 崩溃点定位，不直接进入算法修改。

- `autonomous_flight/include/autonomous_flight/mpcNavigation.cpp`
- `autonomous_flight/include/autonomous_flight/mpcNavigation.h`
- `autonomous_flight/include/autonomous_flight/flightBase.cpp`
- `autonomous_flight/include/autonomous_flight/flightBase.h`
- `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp`
- `trajectory_planner/include/trajectory_planner/mpcPlanner.h`
- `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.cpp`
- `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.h`
- `onboard_detector/include/onboard_detector/fakeDetector.cpp`
- `onboard_detector/include/onboard_detector/dynamicDetector.cpp`
- `map_manager/include/map_manager/dynamicMap.cpp`
- `map_manager/include/map_manager/occupancyMap.cpp`
- `uav_simulator/src/quadcopterPlugin.cpp`
- `uav_simulator/src/obstaclePathPlugin.cc`
- `autonomous_flight/launch/intent_mpc_demo.launch`
- `uav_simulator/launch/start.launch`
- `autonomous_flight/cfg/mpc_navigation/*.yaml`

## 9. 初次验收结论（已被后续排查更新）

结论：**不完全满足阶段 0 验收标准**。

已满足：

- 环境已梳理。
- ROS1 Noetic Docker 环境已搭建。
- Intent-MPC 已克隆并编译成功。
- Gazebo 可打开。
- RViz 可打开。
- UAV 可生成。
- 动态障碍物存在并运动。
- UAV 在首次运行中能起飞并沿路径运动一段距离。
- 关键 ROS 节点、topic、launch、yaml 已梳理。

未满足：

- 官方 demo 不能稳定完成动态障碍物避障流程。
- `mpc_navigation_node` 可复现崩溃，exit code `-11`。
- 崩溃后 UAV odom 出现 `nan`，TF/odom 状态退化。

阶段 1 之前建议先做“官方 demo 稳定性定位”，最小目标是让 `intent_mpc_demo.launch` 在不改算法逻辑的前提下稳定跑完至少一个完整参考轨迹循环，或明确崩溃是代码兼容性、仿真随机性、Docker 图形/时钟环境，还是参数导致。

## 10. 继续排查与最终验收更新

时间：2026-04-30
状态：在不修改规划目标函数、预测模型和避障策略的前提下，补充了运行稳定性防护和轻量可视化配置。

### 10.1 崩溃定位

使用 gdb 复现 `mpc_navigation_node` 崩溃：

```bash
gdb -q -batch \
  -ex "set pagination off" \
  -ex "handle SIGPIPE nostop noprint pass" \
  -ex "run" \
  -ex "thread apply all bt full" \
  --args /home/intent/catkin_ws/devel/lib/autonomous_flight/mpc_navigation_node
```

关键日志：

- `57_gdb_after_mutex_mpc.log`
- `58_catkin_make_after_mpc_guard.log`
- `70_catkin_make_after_nan_guards.log`

定位结果：

- 崩溃点稳定落在 `trajectory_planner::mpcPlanner::getIntentComb()`。
- 原因是预测障碍物数组、意图概率数组和动态障碍物索引在某些帧不一致，`obIdx` 或 intent 下标可能越界。
- 之后又定位到 `/CERLAB/quadcopter/cmd_acc` 先出现 `nan`，随后 Gazebo UAV odom 变 `nan`，最后 MPC path 变 `nan`。

### 10.2 已做的最小稳定性修复

已修改文件：

- `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.h`
- `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.cpp`
- `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp`
- `tracking_controller/include/tracking_controller/trackingController.cpp`
- `uav_simulator/src/quadcopterPlugin.cpp`

修复内容：

- `dynamicPredictor`：对预测结果读写加 mutex，避免 timer 写入和 MPC 线程读取并发访问同一批预测数组。
- `mpcPlanner`：过滤不完整预测障碍物；检查 `obIdx`、intent 概率和预测轨迹维度；MPC 解向量非有限时判失败，不再发布 NaN path。
- `trackingController`：保护零/异常 `dt`，避免误差微分除零；非有限目标/控制参考不发布。
- `quadcopterPlugin`：拒收非有限 `cmd_acc`，避免仿真器状态被 NaN 命令污染。

说明：这些改动属于运行稳定性和输入防御，不改变 Intent-MPC 的代价函数、预测模型、避障目标或规划策略。

### 10.3 最终 demo 验证

重新编译：

```bash
cd /home/intent/catkin_ws
source /opt/ros/noetic/setup.bash
catkin_make
```

结果：编译成功，`mpc_navigation_node`、`tracking_controller_node`、`quadcopterPlugin` 均重新构建。

官方 demo 启动命令仍为：

```bash
roslaunch uav_simulator start.launch
roslaunch autonomous_flight intent_mpc_demo.launch
```

90 秒 NaN 追踪结果：

```text
counts cmd_acc:3439,odom:952,path:684,target:6989
nonfinite_keys=
```

5 分钟运行监控结果：

```text
finite_odom_samples=3389/3389
odom_first_xyz=-1.458,6.444,2.013
odom_last_xyz=1.488,-7.144,0.963
odom_displacement_m=13.951
odom_path_length_m=139.663
dynamic_model_count=80
dynamic_models_moved_gt_0_05m=79
dynamic_model_max_move_m=21.245
path_lengths=/mpcNavigation/mpc_trajectory:30,/mpc_planner/mpc_trajectory:30
nonfinite_events=0
node_alive /mpc_navigation_node=True
node_alive /tracking_controller_node=True
node_alive /gazebo=True
node_alive /gazebo_gui=True
node_alive /rviz1=True
```

关键日志：

- `72_validation_demo_after_nan_guards.log`
- `73_nan_trace_after_guards.log`
- `74_runtime_monitor_5min_after_nan_guards.log`

验证结论：

- Gazebo 正常打开并生成 UAV。
- RViz 正常打开。
- `/gazebo/model_states` 中存在 80 个动态障碍物。
- 动态障碍物持续移动。
- UAV 起飞并沿轨迹持续运动。
- `/mpc_planner/mpc_trajectory`、`/mpcNavigation/mpc_trajectory` 持续发布，轨迹长度为 30。
- `/dynamic_predictor/predict_trajectories`、`/dynamic_predictor/intent_probability`、`/mpc_planner/dynamic_obstacles` 持续发布。
- 未再出现 `SIGSEGV`、节点死亡、NaN odom/path、OSQP non-convex 报错。
- 日志中仍有多次 `[AutoFlight]: Collision detected. MPC replan.` / `MPC collision detected!`，但节点持续运行且随后多次 `Goal reached`，判断为在线避障重规划行为，不是致命错误。

### 10.4 轻量可视化配置

新增文件：

- `remote_control/rviz/mpc_navigation_fast.rviz`
- `remote_control/launch/mpc_navigation_fast_rviz.launch`
- `autonomous_flight/launch/intent_mpc_demo_fast_visual.launch`

启动方式：

```bash
roslaunch uav_simulator start.launch
roslaunch autonomous_flight intent_mpc_demo_fast_visual.launch
```

优化内容：

- 保留 UAV pose、target pose、MPC trajectory、reference trajectory、dynamic obstacles。
- 关闭膨胀体素地图 PointCloud2 Boxes 渲染。
- 关闭 controller 文本 marker、RobotModel mesh、historic trajectory。
- RViz frame rate 从 30 降为 15。
- 推荐关闭 Gazebo GUI `gzclient`，只保留 `gzserver` 和 RViz 观察。

当前实测：

- 原始 RViz 约 97% CPU，Gazebo GUI `gzclient` 约 75% CPU。
- fast RViz 约 62% CPU，关闭 `gzclient` 后释放 Gazebo GUI 渲染负载。
- `gzserver` 仍约 160% CPU，主要来自物理仿真、动态障碍物和传感器插件；若还需要更流畅，可下一步单独做“低频传感器/低负载 world”运行配置，但那会偏离官方 demo 更远。

### 10.5 最终阶段 0 验收结论

结论：**满足阶段 0 验收标准**。

已满足：

- 环境信息、依赖、Docker ROS1 Noetic 环境已梳理。
- Intent-MPC 已克隆并编译成功。
- 官方 demo 两条主命令可启动。
- Gazebo、RViz、UAV、动态障碍物均正常。
- UAV 能起飞、沿路径运动，并在动态障碍物环境中持续重规划。
- 关键 ROS node/topic 已记录。
- 无节点崩溃、NaN、OSQP non-convex、明显 TF 异常。
- 已提供轻量可视化启动方案。

阶段 1 建议：

- 阅读 `mpcNavigation.cpp` 的重规划状态机和 collision check。
- 阅读 `mpcPlanner.cpp` 中 `makePlanWithPred()`、`getIntentComb()`、`evaluateTraj()`。
- 阅读 `dynamicPredictor.cpp` 中 intent probability 与预测轨迹生成。
- 先固定随机 world / 障碍物 seed，建立可重复实验场景，再进入“不确定性感知”和多模态预测改造。

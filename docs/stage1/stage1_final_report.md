# Stage 1 Final Report: Intent-MPC Data Flow

## 1. Objective

Stage 1 answers one question:

> Where should uncertainty-aware dynamic obstacle planning be inserted into Intent-MPC with the least disruption?

This report is analysis-only. It does not modify the algorithm.

## 2. Scope and Sources

Main sources read:

- `uav_simulator/launch/start.launch`
- `autonomous_flight/launch/intent_mpc_demo.launch`
- `autonomous_flight/include/autonomous_flight/flightBase.cpp`
- `autonomous_flight/include/autonomous_flight/mpcNavigation.cpp`
- `onboard_detector/include/onboard_detector/fakeDetector.cpp`
- `onboard_detector/include/onboard_detector/utils.h`
- `map_manager/include/map_manager/dynamicMap.cpp`
- `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.cpp`
- `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.h`
- `dynamic_predictor/include/dynamic_predictor/utils.h`
- `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp`
- `trajectory_planner/include/trajectory_planner/mpcPlanner.h`
- `tracking_controller/include/tracking_controller/trackingController.cpp`
- `docs/stage0/Intent_MPC_stage0_report.md`

Stage 0 runtime validation is reused for node/topic evidence. No new algorithm run was required for this stage.

## 3. Launch and Runtime Graph

Official launch sequence:

```bash
roslaunch uav_simulator start.launch
roslaunch autonomous_flight intent_mpc_demo.launch
```

`uav_simulator/launch/start.launch`:

- Selects `uav_simulator/worlds/generated_env/generated_env.world` as the demo world.
- Starts Gazebo through `gazebo_ros/empty_world.launch`.
- Loads the UAV URDF.
- Spawns `quadcopter` at `(0.0, 7.0, 0.1)` with yaw `-3.14`.
- Throttles raw simulator state to 30 Hz.
- Starts UAV TF and keyboard control.

Source evidence:

- World selection: `uav_simulator/launch/start.launch:64`
- Gazebo include: `uav_simulator/launch/start.launch:67`
- URDF selection: `uav_simulator/launch/start.launch:78-85`
- State throttles: `uav_simulator/launch/start.launch:90-93`
- UAV spawn: `uav_simulator/launch/start.launch:94`
- TF include: `uav_simulator/launch/start.launch:97-99`

`autonomous_flight/launch/intent_mpc_demo.launch`:

- Loads controller, fake detector, flight base, planner, map, detector, and predictor parameters.
- Starts `tracking_controller_node`.
- Starts `mpc_navigation_node`.
- Starts RViz through `remote_control/launch/mpc_navigation_rviz.launch`.

Source evidence:

- Parameter loading: `autonomous_flight/launch/intent_mpc_demo.launch:2-8`
- Nodes: `autonomous_flight/launch/intent_mpc_demo.launch:10-11`
- RViz include: `autonomous_flight/launch/intent_mpc_demo.launch:13`

Stage 0 runtime nodes:

```text
/gazebo
/gazebo_gui
/gt_acc_throttle
/gt_odom_throttle
/gt_pose_throttle
/gt_vel_throttle
/keyboard_control
/mpc_navigation_node
/quadcopterTF
/rviz1
/tracking_controller_node
```

## 4. Key ROS Topics

UAV state:

- `/CERLAB/quadcopter/pose_raw`
- `/CERLAB/quadcopter/pose`
- `/CERLAB/quadcopter/vel_raw`
- `/CERLAB/quadcopter/vel`
- `/CERLAB/quadcopter/acc_raw`
- `/CERLAB/quadcopter/acc`
- `/CERLAB/quadcopter/odom_raw`
- `/CERLAB/quadcopter/odom`

UAV control:

- `/CERLAB/quadcopter/setpoint_pose`
- `/autonomous_flight/target_state`
- `/CERLAB/quadcopter/cmd_acc`
- `/CERLAB/quadcopter/cmd_vel`

Planning:

- `/mpcNavigation/input_trajectory`
- `/mpcNavigation/mpc_trajectory`
- `/mpc_planner/mpc_trajectory`
- `/mpc_planner/traj_history`
- `/mpc_planner/candidate_trajectories`
- `/mpc_planner/static_obstacles`
- `/mpc_planner/dynamic_obstacles`

Dynamic obstacle and prediction visualization:

- `/onboard_detector/GT_obstacle_bbox`
- `/onboard_detector/history_trajectories`
- `/dynamic_predictor/history_trajectories`
- `/dynamic_predictor/predict_trajectories`
- `/dynamic_predictor/intent_probability`
- `/dynamic_predictor/var_points`
- `/dynamic_predictor/pred_bbox`

Controller evidence:

- `tracking_controller` subscribes `/CERLAB/quadcopter/odom` and `/autonomous_flight/target_state`.
- In simulation mode it publishes `/CERLAB/quadcopter/cmd_acc`.

Source evidence:

- `tracking_controller/include/tracking_controller/trackingController.cpp:181-183`
- `tracking_controller/include/tracking_controller/trackingController.cpp:207-218`

## 5. High-Level Data Flow

Official demo in fake detector + predictor mode:

```text
Gazebo dynamic models
  -> /gazebo/model_states
  -> onboardDetector::fakeDetector
  -> obstacle history: pos/vel/acc/size
  -> dynamicPredictor::predictor
  -> predPos / predSize / intentProb
  -> trajPlanner::mpcPlanner::updatePredObstacles
  -> mpcPlanner::makePlanWithPred
  -> /mpcNavigation/mpc_trajectory
  -> /autonomous_flight/target_state
  -> tracking_controller_node
  -> /CERLAB/quadcopter/cmd_acc
  -> Gazebo quadcopter plugin
```

The `use_predictor=false` fallback path:

```text
fakeDetector or dynamicMap
  -> obstaclesPos / obstaclesVel / obstaclesSize
  -> mpcPlanner::updateDynamicObstacles
  -> mpcPlanner::makePlan
```

Source evidence:

- Predictor initialized and connected to fake detector: `autonomous_flight/include/autonomous_flight/mpcNavigation.cpp:140-144`
- Planner modules initialized: `autonomous_flight/include/autonomous_flight/mpcNavigation.cpp:147-163`
- Predictor path: `autonomous_flight/include/autonomous_flight/mpcNavigation.cpp:293-318`
- Non-predictor path: `autonomous_flight/include/autonomous_flight/mpcNavigation.cpp:300-320`
- Target publication chain: `autonomous_flight/include/autonomous_flight/mpcNavigation.cpp:331-334`

## 6. Dynamic Obstacle Generation

In the official demo, dynamic obstacles are simulated in Gazebo and read by `fakeDetector`.

`fakeDetector` behavior:

- Subscribes `/gazebo/model_states` when mocap is not used.
- Reads target prefixes from `target_obstacle`.
- Official stage 0 config sets target prefixes to `person`, `dynamic_box`, and `dynamic_cylinder`.
- Estimates velocity and acceleration by differencing Gazebo model state across time.
- Parses object size from Gazebo model name strings.
- Stores obstacle history for prediction.
- Publishes ground-truth obstacle boxes and history trajectories.

Source evidence:

- Target prefix parameter: `onboard_detector/include/onboard_detector/fakeDetector.cpp:23-25`
- Gazebo model state subscription: `onboard_detector/include/onboard_detector/fakeDetector.cpp:55-60`
- Odom subscription and visualization topics: `onboard_detector/include/onboard_detector/fakeDetector.cpp:62-70`
- Position extraction: `onboard_detector/include/onboard_detector/fakeDetector.cpp:144-156`
- Velocity and acceleration estimation: `onboard_detector/include/onboard_detector/fakeDetector.cpp:172-196`
- Size parsing from model names: `onboard_detector/include/onboard_detector/fakeDetector.cpp:207-223`
- History update: `onboard_detector/include/onboard_detector/fakeDetector.cpp:311-320`

Core obstacle struct:

```cpp
box3D {
  double x, y, z;
  double x_width, y_width, z_width;
  double id;
  double Vx, Vy, Vz;
  double Ax, Ay, Az;
  bool is_human;
  bool is_dynamic;
  bool fix_size;
  bool is_dynamic_candidate;
  bool is_estimated;
}
```

Source: `onboard_detector/include/onboard_detector/utils.h`

Real detector path:

- `dynamicMap` creates `onboardDetector::dynamicDetector`.
- `dynamicMap::getDynamicObstacles` converts `box3D` to separate `Eigen::Vector3d` arrays for position, velocity, and size.

Source evidence:

- Detector ownership: `map_manager/include/map_manager/dynamicMap.cpp:23-31`
- Dynamic obstacle conversion: `map_manager/include/map_manager/dynamicMap.cpp:48-60`

## 7. Dynamic Predictor I/O

`dynamicPredictor::predictor` receives history and outputs multiple possible intent-conditioned future trajectories.

Inputs:

- `posHist_`
- `velHist_`
- `accHist_`
- `sizeHist_`

Output members:

- `posPred_`
- `sizePred_`
- `intentProb_`

Source evidence:

- Members: `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.h:56-64`
- Fake/real detector history input: `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.cpp:163-170`
- Intent probability and trajectory prediction update: `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.cpp:171-187`
- Public getter: `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.h:101-103`

Intent types:

```cpp
FORWARD, LEFT, RIGHT, STOP
```

Prediction tensor format used by MPC:

```text
predPos[obstacle][intent][time_step] -> Eigen::Vector3d
predSize[obstacle][intent][time_step] -> Eigen::Vector3d
intentProb[obstacle] -> Eigen::VectorXd
```

Prediction generation:

- `predTraj` loops over obstacle and intent.
- `genPoints` dispatches to forward, turning, or stop models.
- `genTraj` computes mean trajectory and inflates predicted size by variance through `zScore_`.

Source evidence:

- Per-obstacle/per-intent loop: `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.cpp:285-331`
- Intent model dispatch: `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.cpp:333-351`
- Forward model: `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.cpp:353-404`
- Turning model: `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.cpp:406-488`
- Stop model: `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.cpp:490-503`
- Mean and variance inflation: `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.cpp:505-540`

Important observation:

`dynamic_predictor` already expands `predSize` from prediction dispersion using `zScore_`. Later uncertainty-aware planning should avoid double-counting this term unless it is explicitly separated from perception uncertainty.

## 8. MPC Dynamic Obstacle Handling

MPC stores dynamic obstacles as horizon-indexed arrays:

- `dynamicObstaclesPos_`
- `dynamicObstaclesVel_`
- `dynamicObstaclesSize_`
- `obPredPos_`
- `obPredSize_`
- `obIntentProb_`

Source evidence:

- Members: `trajectory_planner/include/trajectory_planner/mpcPlanner.h:69-76`
- Public update methods: `trajectory_planner/include/trajectory_planner/mpcPlanner.h:117-123`

Non-predictor path:

- `updateDynamicObstacles` repeats current obstacle state over the whole horizon.

Source: `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp:268-293`

Predictor path:

- `updatePredObstacles` validates shape, pads short trajectories, and stores prediction tensors.
- It also initializes `dynamicObstaclesPos_` and `dynamicObstaclesSize_` from the forward intent at time step 0.

Source: `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp:295-368`

Planning with prediction:

- `makePlanWithPred` builds candidate obstacle intent combinations.
- It solves candidate QPs under a time budget.
- It scores candidates using consistency, detour, and safety terms.
- It selects the best candidate trajectory.

Source evidence:

- `makePlanWithPred`: `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp:560-666`
- `getIntentComb`: `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp:718-802`
- Candidate scoring entry: `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp:804-810`

QP obstacle constraints:

- `solveTraj` calls `updateObstacleParam`, `castMPCToQPConstraintMatrix`, and `castMPCToQPConstraintVectors`.
- `castMPCToQPConstraintMatrix` inserts linearized ellipsoid obstacle constraints.
- `castMPCToQPConstraintVectors` computes lower obstacle bounds.

Source evidence:

- QP setup path: `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp:370-432`
- Constraint matrix obstacle block: `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp:1006-1094`
- Constraint vector obstacle block: `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp:1136-1167`

Obstacle size/safety expansion:

```cpp
osize[j](i,0) = dynamicObstaclesSize[i][j](0)/2 + this->dynamicSafetyDist_;
osize[j](i,1) = dynamicObstaclesSize[i][j](1)/2 + this->dynamicSafetyDist_;
osize[j](i,2) = dynamicObstaclesSize[i][j](2)/2 + this->dynamicSafetyDist_;
```

Source evidence:

- Dynamic obstacle ellipsoid size: `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp:1170-1206`
- Static obstacle ellipsoid size: `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp:1208-1217`

This is the most direct future insertion point for `r_eff`.

## 9. Key Parameters

`autonomous_flight/cfg/mpc_navigation/flight_base.yaml`:

- `simulation: true`
- `use_fake_detector: true`
- `use_predictor: true`
- `desired_velocity: 1.5`
- `desired_acceleration: 1.5`
- `use_predefined_goal: true`
- `execute_path_times: 10`

`autonomous_flight/cfg/mpc_navigation/planner_param.yaml`:

- `mpc_planner/horizon: 30`
- `mpc_planner/static_safety_dist: 0.8`
- `mpc_planner/dynamic_safety_dist: 0.6`
- `mpc_planner/dynamic_constraint_slack_ratio: 0.2`

`autonomous_flight/cfg/mpc_navigation/predictor_param.yaml`:

- `prediction_size: 30`
- `prediction_time_step: 0.1`
- `prediction_z_score: 0.674`
- `min_turning_time: 2.0`
- `max_turning_time: 3.0`

`autonomous_flight/cfg/mpc_navigation/fake_detector_param.yaml`:

- `target_obstacle: ["person", "dynamic_box", "dynamic_cylinder"]`
- `odom_topic: "/CERLAB/quadcopter/odom"`
- `history_size: 100`

## 10. Stage 1 Conclusions

Main findings:

- Official demo dynamic obstacles are not ROS messages first; they are Gazebo models read from `/gazebo/model_states`.
- The fake detector converts Gazebo model state to `box3D`, including estimated velocity and acceleration.
- `dynamic_predictor` consumes obstacle history and outputs predicted position/size trajectories per intent plus intent probabilities.
- `mpcNavigation` passes prediction directly into `mpcPlanner`.
- MPC represents obstacles as ellipsoid constraints in QP.
- Existing dynamic obstacle safety is a fixed `dynamicSafetyDist_` added to half-sizes in `updateObstacleParam`.

Recommended research route:

1. Stage 2: implement metrics/logging before changing behavior.
2. Stage 3: implement perception degradation outside planner.
3. Stage 4: define uncertainty obstacle schema and RViz/logging.
4. Stage 5: first modify the effective dynamic obstacle radius/size path, then optionally add risk costs.

## 11. Stage 1 Acceptance

- [x] Launch tree and runtime node graph documented.
- [x] UAV pose/velocity/control/planning topics documented.
- [x] Dynamic obstacle generation path documented.
- [x] `dynamic_predictor` input/output format documented.
- [x] MPC dynamic obstacle constraint path documented.
- [x] Candidate uncertainty insertion points ranked.
- [x] Stage 1 final report completed.

Conclusion: Stage 1 acceptance criteria are met.


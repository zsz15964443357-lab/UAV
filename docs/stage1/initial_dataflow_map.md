# Initial Dataflow Map

This is the first-pass Stage 1 map based on static code reading. It is intentionally analysis-only and does not change the algorithm.

## Demo Launch Tree

Official demo:

```bash
roslaunch uav_simulator start.launch
roslaunch autonomous_flight intent_mpc_demo.launch
```

Fast visualization variant:

```bash
roslaunch uav_simulator start.launch
roslaunch autonomous_flight intent_mpc_demo_fast_visual.launch
```

### `uav_simulator/launch/start.launch`

Main responsibilities:

- Starts Gazebo with `uav_simulator/worlds/generated_env/generated_env.world`.
- Loads `uav_simulator/urdf/quadcopter.urdf` by default.
- Spawns the UAV model as `quadcopter` at `(0.0, 7.0, 0.1)` with yaw `-3.14`.
- Throttles raw simulator state topics to 30 Hz:
  - `/CERLAB/quadcopter/pose_raw -> /CERLAB/quadcopter/pose`
  - `/CERLAB/quadcopter/vel_raw -> /CERLAB/quadcopter/vel`
  - `/CERLAB/quadcopter/acc_raw -> /CERLAB/quadcopter/acc`
  - `/CERLAB/quadcopter/odom_raw -> /CERLAB/quadcopter/odom`
- Includes `uav_simulator/launch/setupTF.launch`.
- Starts `keyboard_control`.

### `autonomous_flight/launch/intent_mpc_demo.launch`

Loads:

- `tracking_controller/cfg/controller_param.yaml` under namespace `controller`.
- `autonomous_flight/cfg/mpc_navigation/fake_detector_param.yaml`.
- `autonomous_flight/cfg/mpc_navigation/flight_base.yaml` under namespace `autonomous_flight`.
- `autonomous_flight/cfg/mpc_navigation/planner_param.yaml`.
- `autonomous_flight/cfg/mpc_navigation/mapping_param.yaml` under namespace `/dynamic_map`.
- `autonomous_flight/cfg/mpc_navigation/dynamic_detector_param.yaml` under namespace `/onboard_detector`.
- `autonomous_flight/cfg/mpc_navigation/predictor_param.yaml` under namespace `/dynamic_predictor`.

Starts:

- `tracking_controller_node`
- `mpc_navigation_node`
- RViz through `remote_control/launch/mpc_navigation_rviz.launch`

The fast visualization variant replaces the RViz include with `remote_control/launch/mpc_navigation_fast_rviz.launch`.

## Runtime Module Map

### Simulation and UAV State

`uav_simulator/src/quadcopterPlugin.cpp`

- Publishes raw UAV state:
  - `/CERLAB/quadcopter/pose_raw`
  - `/CERLAB/quadcopter/vel_raw`
  - `/CERLAB/quadcopter/acc_raw`
  - `/CERLAB/quadcopter/odom_raw`
- Subscribes control commands:
  - `/CERLAB/quadcopter/cmd_acc`
  - `/CERLAB/quadcopter/cmd_vel`
  - `/CERLAB/quadcopter/setpoint_pose`

`topic_tools/throttle` republishes raw state to the runtime state topics used by the planner and controller.

### Flight Base and Navigation

`autonomous_flight/src/mpc_navigation_node.cpp`

- Creates `AutoFlight::mpcNavigation`.

`autonomous_flight/include/autonomous_flight/flightBase.cpp`

- In simulation mode, subscribes:
  - `/CERLAB/quadcopter/odom`
  - `/move_base_simple/goal`
- Publishes:
  - `/CERLAB/quadcopter/setpoint_pose`
  - `/autonomous_flight/target_state`
- Maintains current position, velocity, acceleration, yaw, and target state.

`autonomous_flight/include/autonomous_flight/mpcNavigation.cpp`

- Builds the high-level stack:
  - `onboardDetector::fakeDetector` when `use_fake_detector: true`.
  - `mapManager::dynamicMap`.
  - `dynamicPredictor::predictor` when `use_predictor: true`.
  - RRT planner.
  - polynomial trajectory planner.
  - MPC planner.
- Publishes visualization paths:
  - `mpcNavigation/rrt_path`
  - `mpcNavigation/poly_traj`
  - `mpcNavigation/pwl_trajectory`
  - `mpcNavigation/mpc_trajectory`
  - `mpcNavigation/input_trajectory`
  - `mpcNavigation/goal`
- Sends planned tracking targets to `/autonomous_flight/target_state`.

## Dynamic Obstacle Data Path

### Ground-truth simulation detector path

`onboard_detector/include/onboard_detector/fakeDetector.cpp`

- Subscribes `/gazebo/model_states`.
- Selects models whose names start with configured target prefixes:
  - `person`
  - `dynamic_box`
  - `dynamic_cylinder`
- Estimates obstacle velocity and acceleration from model state differences.
- Parses obstacle dimensions from Gazebo model names.
- Publishes visualization:
  - `onboard_detector/GT_obstacle_bbox`
  - `onboard_detector/history_trajectories`
- Provides service:
  - `fake_detector/getDynamicObstacles`
- Provides in-process accessors used by `mpcNavigation` and `dynamicPredictor`:
  - `getObstacles`
  - `getObstaclesInSensorRange`
  - `getDynamicObstaclesHist`

Core obstacle struct:

```cpp
onboardDetector::box3D {
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

### Real/perception detector path

`map_manager/include/map_manager/dynamicMap.cpp`

- Owns `onboardDetector::dynamicDetector`.
- Calls `dynamicDetector::getDynamicObstacles`.
- Converts `box3D` to:
  - `std::vector<Eigen::Vector3d> obstaclePos`
  - `std::vector<Eigen::Vector3d> obstacleVel`
  - `std::vector<Eigen::Vector3d> obstacleSize`
- Frees occupied map regions corresponding to dynamic obstacles.

`onboard_detector/include/onboard_detector/dynamicDetector.cpp`

- Uses depth/color/yolo inputs in the non-fake detector path.
- Publishes:
  - `onboard_detector/dynamic_point_cloud`
  - `onboard_detector/dynamic_bboxes`
- Maintains tracked dynamic bounding boxes and histories.

The official demo uses fake detector mode, but the real detector path is important for later multimodal perception uncertainty work.

## Predictor Data Path

`dynamic_predictor/include/dynamic_predictor/dynamicPredictor.cpp`

Inputs:

- Fake detector history through `fakeDetector::getDynamicObstaclesHist`, when simulation fake detector is enabled.
- Real detector history through `dynamicDetector::getDynamicObstaclesHist`, otherwise.

Parameters:

- `dynamic_predictor/prediction_size`
- `dynamic_predictor/prediction_time_step`
- `dynamic_predictor/prediction_z_score`
- `dynamic_predictor/min_turning_time`
- `dynamic_predictor/max_turning_time`
- `dynamic_predictor/max_front_prob`
- `dynamic_predictor/front_angle`
- `dynamic_predictor/stop_velocity_thereshold`
- `dynamic_predictor/prob_scale_param`

Outputs:

- In-process prediction through:
  - `getPrediction(predPos, predSize, intentProb)`
  - `getPrediction(std::vector<dynamicPredictor::obstacle>&)`
- Visualization topics:
  - `dynamic_predictor/history_trajectories`
  - `dynamic_predictor/predict_trajectories`
  - `dynamic_predictor/intent_probability`
  - `dynamic_predictor/var_points`
  - `dynamic_predictor/pred_bbox`

Intent enum:

```cpp
FORWARD, LEFT, RIGHT, STOP
```

Prediction shape used by MPC:

```text
predPos[obstacle][intent][time_step] -> Eigen::Vector3d
predSize[obstacle][intent][time_step] -> Eigen::Vector3d
intentProb[obstacle] -> Eigen::VectorXd
```

## MPC Dynamic Obstacle Path

`autonomous_flight/include/autonomous_flight/mpcNavigation.cpp`

When `use_predictor: true`:

```text
predictor_->getPrediction(predPos, predSize, intentProb)
mpc_->updatePredObstacles(predPos, predSize, intentProb)
mpc_->makePlanWithPred()
```

When `use_predictor: false`:

```text
map/fakeDetector dynamic obstacles
mpc_->updateDynamicObstacles(obstaclesPos, obstaclesVel, obstaclesSize)
mpc_->makePlan()
```

`trajectory_planner/include/trajectory_planner/mpcPlanner.cpp`

Important methods:

- `updateDynamicObstacles`: repeats current obstacle state over the MPC horizon.
- `updatePredObstacles`: validates predicted obstacle trajectories and stores intent probabilities.
- `makePlanWithPred`: generates candidate trajectories for intent combinations and selects the best candidate.
- `getIntentComb`: constructs intent combinations for the closest obstacle and max-probability intent for other obstacles.
- `solveTraj`: formulates and solves the QP.
- `updateObstacleParam`: converts dynamic/static obstacles into ellipsoid constraint parameters.
- `castMPCToQPConstraintMatrix` and `castMPCToQPConstraintVectors`: add obstacle constraints to the QP.
- `getSafetyScore`: scores candidate trajectories by static/dynamic obstacle proximity.

Current dynamic obstacle safety expansion occurs in `updateObstacleParam`:

```cpp
osize[j](i,0) = dynamicObstaclesSize[i][j](0)/2 + dynamicSafetyDist_;
osize[j](i,1) = dynamicObstaclesSize[i][j](1)/2 + dynamicSafetyDist_;
osize[j](i,2) = dynamicObstaclesSize[i][j](2)/2 + dynamicSafetyDist_;
```

This is the most direct Stage 5 insertion point for replacing fixed dynamic margin with uncertainty-aware effective radius.

## Key Topics

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

- `/autonomous_flight/target_state`
- `/CERLAB/quadcopter/cmd_acc`
- `/CERLAB/quadcopter/cmd_vel`
- `/CERLAB/quadcopter/setpoint_pose`

Navigation/planning visualization:

- `mpcNavigation/input_trajectory`
- `mpcNavigation/mpc_trajectory`
- `mpc_planner/mpc_trajectory`
- `mpc_planner/traj_history`
- `mpc_planner/candidate_trajectories`
- `mpc_planner/dynamic_obstacles`
- `mpc_planner/static_obstacles`

Dynamic obstacle visualization:

- `onboard_detector/GT_obstacle_bbox`
- `onboard_detector/history_trajectories`
- `dynamic_predictor/history_trajectories`
- `dynamic_predictor/predict_trajectories`
- `dynamic_predictor/intent_probability`
- `dynamic_predictor/var_points`
- `dynamic_predictor/pred_bbox`

## Initial Insertion-Point Candidates

### Candidate A: Between detector/map and predictor

Shape:

```text
box3D/history -> uncertainty-aware obstacle history -> dynamicPredictor
```

Pros:

- Models perception uncertainty before intent prediction.
- Useful for Stage 3 perception degradation and Stage 4 uncertainty representation.

Risks:

- Requires careful handling of history, delay, dropout, and association.
- Could affect predictor behavior and make debugging harder.

### Candidate B: Between predictor and MPC

Shape:

```text
predPos, predSize, intentProb -> uncertainty-adjusted predSize/effective_radius -> mpcPlanner
```

Pros:

- Minimal first algorithmic change.
- Directly maps to `updatePredObstacles` and `updateObstacleParam`.
- Easy to compare original Intent-MPC, fixed margin, and uncertainty-aware margin.

Risks:

- Uncertainty affects planning but not predictor intent probabilities.

### Candidate C: Inside MPC obstacle constraint construction

Shape:

```text
dynamicObstaclesSize + uncertainty terms -> osize in updateObstacleParam
```

Pros:

- Smallest local Stage 5 code change.
- Clear baseline against existing `dynamicSafetyDist_`.

Risks:

- If uncertainty needs per-obstacle metadata beyond size, `mpcPlanner` data structures must be extended first.

## Current Recommendation

For phased implementation:

1. Stage 2 should add logging before any planner behavior changes.
2. Stage 3 should implement perception degradation outside the planner.
3. Stage 4 should define uncertainty fields and visualization.
4. Stage 5 should first implement Candidate C as fixed/effective radius inflation, then consider Candidate B for predicted obstacle trajectories.

This keeps each stage testable and avoids changing Intent-MPC behavior before metrics are available.


# Stage 5 Final Report

## Goal

Let the local planner use fixed safety margins and Stage 4 uncertainty-aware effective radii while keeping the original Intent-MPC behavior available as the default baseline.

The latest `uav/main` README asks Stage 5 to prioritize:

1. constraint inflation from `r` to `r_eff`;
2. a later risk-cost variant;
3. switchable modes: original Intent-MPC, fixed-margin Intent-MPC, and uncertainty-aware Intent-MPC.

This stage implements the constraint/radius-inflation path first. The nonlinear risk-cost term is kept as a later refinement.

## Implementation

Modified:

- `autonomous_flight/include/autonomous_flight/mpcNavigation.h`
- `autonomous_flight/include/autonomous_flight/mpcNavigation.cpp`
- `autonomous_flight/CMakeLists.txt`
- `autonomous_flight/package.xml`
- `autonomous_flight/cfg/mpc_navigation/flight_base.yaml`

Added:

- `autonomous_flight/launch/intent_mpc_demo_fixed_margin.launch`
- `autonomous_flight/launch/intent_mpc_demo_uncertainty.launch`

The integration is in `mpcNavigation`, before dynamic obstacles are passed to `trajectory_planner::mpcPlanner`. The MPC solver implementation is not rewritten.

## Modes

- `original`: pass dynamic obstacles into MPC unchanged.
- `fixed_margin`: add `2 * fixed_safety_margin` to each dynamic obstacle size.
- `uncertainty_aware`: subscribe to `/multimodal_uncertainty/uncertainty_obstacles` and inflate obstacle sizes using Stage 4 `effective_radius`.

The default in `flight_base.yaml` is `original`, so the official demo remains unchanged unless a Stage 5 launch file or parameter explicitly enables a new mode.

## Runtime Commands

The Gazebo plugin environment must be loaded before launching the simulator:

```bash
source /opt/ros/noetic/setup.bash
source /home/intent/catkin_ws/devel/setup.bash
source /home/intent/catkin_ws/src/Intent-MPC/uav_simulator/gazeboSetup.bash
```

Fixed-margin mode:

```bash
roslaunch uav_simulator start.launch
roslaunch autonomous_flight intent_mpc_demo_fixed_margin.launch fixed_safety_margin:=0.3
```

Uncertainty-aware mode:

```bash
roslaunch uav_simulator start.launch
roslaunch autonomous_flight intent_mpc_demo_uncertainty.launch
```

Both Stage 5 launch files use `remote_control/launch/mpc_navigation_fast_rviz.launch`, which opens the lighter `rviz_fast` view used for smoother visualization on this machine.

## Validation Result

Build:

```bash
catkin_make
```

Result: passed in the Docker ROS Noetic workspace.

Launch parsing:

```bash
roslaunch autonomous_flight intent_mpc_demo_fixed_margin.launch --nodes
roslaunch autonomous_flight intent_mpc_demo_uncertainty.launch --nodes
```

Result:

- fixed-margin nodes: `/tracking_controller_node`, `/mpc_navigation_node`, `/rviz_fast`
- uncertainty-aware nodes: `/perception_degradation_node`, `/uncertainty_obstacle_node`, `/tracking_controller_node`, `/mpc_navigation_node`, `/rviz_fast`

Runtime smoke test with simulator:

- `fixed_margin` loaded `/autonomous_flight/dynamic_obstacle_mode=fixed_margin`.
- `fixed_margin` loaded `/autonomous_flight/fixed_safety_margin=0.3`.
- `uncertainty_aware` loaded `/autonomous_flight/dynamic_obstacle_mode=uncertainty_aware`.
- `uncertainty_aware` loaded `/autonomous_flight/uncertainty_obstacles_topic=/multimodal_uncertainty/uncertainty_obstacles`.
- `mpcNavigation` reported `Odom and mavros topics are ready`.
- `mpcNavigation` reported `Takeoff succeed`.

Observed key topics:

- `/CERLAB/quadcopter/odom`: `nav_msgs/Odometry`
- `/CERLAB/quadcopter/pose`
- `/CERLAB/quadcopter/vel`
- `/dynamic_predictor/intent_probability`
- `/dynamic_predictor/predict_trajectories`
- `/mpcNavigation/mpc_trajectory`: `nav_msgs/Path`
- `/mpc_planner/dynamic_obstacles`: `visualization_msgs/MarkerArray`
- `/mpc_planner/mpc_trajectory`
- `/mpc_planner/candidate_trajectories`
- `/perception_degradation/degraded_obstacles`: `perception_degradation/DegradedObstacleArray`
- `/multimodal_uncertainty/uncertainty_obstacles`: `multimodal_uncertainty/UncertaintyObstacleArray`

## Issue Found

During the first smoke test, `mpcNavigation` stayed at the odometry wait step because the test shell had not loaded `uav_simulator/gazeboSetup.bash`. In that state, the throttled odom topic existed but the Gazebo quadcopter plugin did not publish real odometry messages.

Resolution:

```bash
source /home/intent/catkin_ws/src/Intent-MPC/uav_simulator/gazeboSetup.bash
```

After loading the Gazebo plugin path, odometry, predictor topics, MPC trajectory topics, and Stage 3/4 obstacle topics were all present.

## Boundary

Stage 5 implements radius/size inflation. A nonlinear risk-cost term inside MPC remains a follow-up after validating the constraint-inflation baseline with Stage 6 experiments.

## Acceptance

Stage 5 satisfies the acceptance criteria for the current staged implementation:

- original mode remains the default;
- fixed-margin mode builds, launches, and publishes planner topics;
- uncertainty-aware mode builds, launches, starts the Stage 3/4 pipeline, and publishes uncertainty obstacle topics;
- predictor and non-predictor dynamic obstacle update paths both apply the selected planner mode;
- smoother visualization is available through the lightweight `rviz_fast` launch.

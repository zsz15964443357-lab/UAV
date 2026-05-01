# Stage 3: Perception Degradation

Goal: simulate unreliable obstacle perception before changing the local planner.

This stage implements a configurable external ROS node:

```text
Gazebo / simulation obstacle ground truth
        -> perception_degradation_node
        -> degraded obstacle topic + RViz markers + CSV samples
```

The node does not change Intent-MPC planner behavior yet. It creates the degraded obstacle interface that later stages can connect to uncertainty modeling and planner constraints.

## Artifacts

- `perception_degradation`: new ROS package.
- `perception_degradation/msg/DegradedObstacle.msg`: degraded obstacle state.
- `perception_degradation/msg/DegradedObstacleArray.msg`: degraded obstacle array plus dropout/false-positive counts.
- `perception_degradation/scripts/perception_degradation_node.py`: configurable degradation node.
- `perception_degradation/config/stage3_default.yaml`: default parameters.
- `perception_degradation/launch/run_degradation.launch`: start degradation node.
- `perception_degradation/launch/run_degradation_with_recorder.launch`: start degradation node plus Stage 2 metric recorder.

## Supported Parameters

- `position_noise_std`
- `velocity_noise_std`
- `delay_ms`
- `dropout_prob`
- `false_positive_prob`
- `confidence_noise`
- `random_seed`

Additional parameters configure target obstacle prefixes, output CSV location, false-positive area, marker topics, confidence range, and publish rate.

## Runtime Usage

Start the official demo first:

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch uav_simulator start.launch
roslaunch autonomous_flight intent_mpc_demo_fast_visual.launch
```

Start degradation observation:

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch perception_degradation run_degradation.launch \
  position_noise_std:=0.1 \
  velocity_noise_std:=0.2 \
  delay_ms:=100 \
  dropout_prob:=0.1 \
  false_positive_prob:=0.05 \
  confidence_noise:=0.1 \
  random_seed:=1
```

The main output topic is:

```text
/perception_degradation/degraded_obstacles
```

RViz marker topic:

```text
/perception_degradation/degraded_obstacle_markers
```

CSV output:

```text
~/catkin_ws/experiment_logs/stage3_degraded_obstacles.csv
```

## Current Stage Boundary

Stage 3 produces degraded obstacle states but does not feed them into MPC. The official demo still uses the original fake detector path. Planner consumption of uncertainty-aware obstacle states belongs to Stage 5.

## Acceptance Checklist

- [x] Degraded obstacle message schema exists.
- [x] Configurable degradation node exists.
- [x] Position noise, velocity noise, delay, dropout, false positives, confidence noise, and random seed are implemented.
- [x] RViz marker output exists.
- [x] Per-obstacle degradation CSV output exists.
- [x] No planner behavior is changed.

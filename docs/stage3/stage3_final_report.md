# Stage 3 Final Report

## Goal

Implement a configurable perception degradation module for simulated dynamic obstacles.

## Implementation

Added ROS package:

```text
perception_degradation
```

Main files:

- `perception_degradation/msg/DegradedObstacle.msg`
- `perception_degradation/msg/DegradedObstacleArray.msg`
- `perception_degradation/scripts/perception_degradation_node.py`
- `perception_degradation/config/stage3_default.yaml`
- `perception_degradation/launch/run_degradation.launch`
- `perception_degradation/launch/run_degradation_with_recorder.launch`

## Supported Degradation

- Position noise
- Velocity noise
- Perception delay
- Dropout
- False positives
- Confidence noise
- Reproducible random seed

## Outputs

Topic:

```text
/perception_degradation/degraded_obstacles
```

RViz:

```text
/perception_degradation/degraded_obstacle_markers
```

CSV:

```text
stage3_degraded_obstacles.csv
```

## Validation

Completed checks:

```bash
python3 -m py_compile perception_degradation/scripts/perception_degradation_node.py
```

Result: passed.

```bash
catkin_make
```

Result: passed in the Stage 0 Docker/ROS Noetic container. `perception_degradation` was discovered by catkin, both messages were generated, and the node wrapper was installed into the devel space.

```bash
roslaunch perception_degradation run_degradation.launch --nodes
```

Result: passed, launch resolves `/perception_degradation_node`.

ROS smoke test:

- Started `roscore`.
- Started `perception_degradation_node.py` with nonzero noise and `false_positive_prob=1.0`.
- Published synthetic `/gazebo/model_states` containing `person1_0.5_0.5_1.8` and `dynamic_box_3_0.4_0.3_1.0`.
- Published synthetic `/CERLAB/quadcopter/odom`.
- Confirmed `/perception_degradation/degraded_obstacles` contained two degraded real obstacles and one false-positive obstacle.
- Confirmed CSV rows were written to `stage3_degraded_obstacles.csv`.
- Confirmed `/perception_degradation/degraded_obstacle_markers` publishes RViz cube and radius sphere markers.

Observed sample result:

- `raw_obstacle_count=2`
- `dropped_obstacle_count=0`
- `false_positive_count=1`
- nonzero position and velocity perturbations under configured noise

## Boundary

Stage 3 does not modify Intent-MPC planner behavior. The degraded stream is ready for Stage 4 uncertainty representation and Stage 5 planner integration.

# Stage 4: Multimodal Uncertainty Representation

Goal: convert degraded obstacle observations into a unified uncertainty-aware obstacle state.

Stage 4 implements:

```text
perception_degradation/degraded_obstacles
        -> uncertainty_obstacle_node
        -> multimodal_uncertainty/uncertainty_obstacles
        -> RViz raw radius + effective risk radius markers
        -> per-obstacle uncertainty CSV
```

This stage still does not change Intent-MPC planner behavior. It prepares the obstacle representation that Stage 5 can use for radius inflation or risk cost.

## Artifacts

- `multimodal_uncertainty`: new ROS package.
- `multimodal_uncertainty/msg/UncertaintyObstacle.msg`: unified obstacle state with confidence, covariance, and effective radius.
- `multimodal_uncertainty/msg/UncertaintyObstacleArray.msg`: obstacle array plus risk formula coefficients.
- `multimodal_uncertainty/scripts/uncertainty_obstacle_node.py`: uncertainty conversion node.
- `multimodal_uncertainty/config/stage4_default.yaml`: default coefficients and output settings.
- `multimodal_uncertainty/launch/run_uncertainty.launch`: start uncertainty node only.
- `multimodal_uncertainty/launch/run_stage4_pipeline.launch`: start Stage 3 degradation plus Stage 4 uncertainty conversion.

## Effective Radius

The node implements:

```text
r_eff = r_obstacle
      + alpha * position_uncertainty
      + beta * velocity_uncertainty
      + gamma * perception_delay_ms
      + delta * (1 - confidence)
```

Default coefficients:

```text
alpha = 1.0
beta  = 0.5
gamma = 0.002
delta = 0.8
```

`gamma` uses milliseconds, so `delay_ms=100` contributes `0.2 m` with the default value.

## Runtime Usage

Start the official demo first if using Gazebo:

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch uav_simulator start.launch
roslaunch autonomous_flight intent_mpc_demo_fast_visual.launch
```

Run Stage 3 + Stage 4 observation pipeline:

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch multimodal_uncertainty run_stage4_pipeline.launch \
  position_noise_std:=0.1 \
  velocity_noise_std:=0.2 \
  delay_ms:=100 \
  dropout_prob:=0.1 \
  false_positive_prob:=0.05 \
  confidence_noise:=0.1 \
  random_seed:=1
```

Main output topic:

```text
/multimodal_uncertainty/uncertainty_obstacles
```

RViz marker topic:

```text
/multimodal_uncertainty/uncertainty_markers
```

CSV output:

```text
~/catkin_ws/experiment_logs/stage4_uncertainty_obstacles.csv
```

## Stage Boundary

Stage 4 only publishes uncertainty-aware obstacle states. It does not replace `onboard_detector`, `dynamic_predictor`, or `mpcNavigation` inputs. Planner usage of `effective_radius` is Stage 5.

## Acceptance Checklist

- [x] Unified uncertainty obstacle message exists.
- [x] Position and velocity covariance fields exist.
- [x] `confidence`, `source_modalities`, and `effective_radius` are represented.
- [x] Effective radius formula is implemented and configurable.
- [x] RViz shows raw radius and inflated risk radius.
- [x] CSV records obstacle uncertainty and risk radius.
- [x] Planner behavior is unchanged.

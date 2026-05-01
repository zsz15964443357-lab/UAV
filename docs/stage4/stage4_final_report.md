# Stage 4 Final Report

## Goal

Convert degraded multimodal obstacle observations into a unified uncertainty-aware obstacle representation.

## Implementation

Added ROS package:

```text
multimodal_uncertainty
```

Main files:

- `multimodal_uncertainty/msg/UncertaintyObstacle.msg`
- `multimodal_uncertainty/msg/UncertaintyObstacleArray.msg`
- `multimodal_uncertainty/scripts/uncertainty_obstacle_node.py`
- `multimodal_uncertainty/config/stage4_default.yaml`
- `multimodal_uncertainty/launch/run_uncertainty.launch`
- `multimodal_uncertainty/launch/run_stage4_pipeline.launch`

## Implemented Fields

- `position`
- `velocity`
- `radius`
- `confidence`
- `position_covariance`
- `velocity_covariance`
- `position_uncertainty`
- `velocity_uncertainty`
- `perception_delay`
- `source_modalities`
- `effective_radius`
- `risk_margin`

## Formula

```text
r_eff = r_obstacle
      + alpha * position_uncertainty
      + beta * velocity_uncertainty
      + gamma * perception_delay_ms
      + delta * (1 - confidence)
```

Default coefficients:

- `alpha=1.0`
- `beta=0.5`
- `gamma=0.002`
- `delta=0.8`

## Validation

Completed checks:

```bash
python3 -m py_compile multimodal_uncertainty/scripts/uncertainty_obstacle_node.py
```

Result: passed.

```bash
catkin_make
```

Result: passed in the Stage 0 Docker/ROS Noetic container. `multimodal_uncertainty` was discovered by catkin, both messages were generated, and the node wrapper was installed into the devel space.

```bash
roslaunch multimodal_uncertainty run_uncertainty.launch --nodes
roslaunch multimodal_uncertainty run_stage4_pipeline.launch --nodes
```

Result: passed. The first launch resolves `/uncertainty_obstacle_node`; the pipeline launch resolves `/perception_degradation_node` and `/uncertainty_obstacle_node`.

ROS smoke test:

- Started `roscore`.
- Started `uncertainty_obstacle_node.py`.
- Published synthetic `/perception_degradation/degraded_obstacles`.
- Subscribed to `/multimodal_uncertainty/uncertainty_obstacles` and `/multimodal_uncertainty/uncertainty_markers`.
- Confirmed one uncertainty obstacle message and one marker array message were received.
- Confirmed CSV rows were written to `stage4_uncertainty_obstacles.csv`.
- Confirmed the marker array includes raw radius, effective radius, and text markers.

Formula check with synthetic input:

```text
r = 0.5
confidence = 0.75
position_uncertainty = 0.1
velocity_uncertainty = 0.2
delay_ms = 100
alpha = 1.0
beta = 0.5
gamma = 0.002
delta = 0.8
```

Observed:

```text
risk_margin = 0.6
effective_radius = 1.1
position_cov_xx = 0.01
velocity_cov_xx = 0.04
```

## Boundary

Stage 4 does not modify planner behavior. Planner use of `effective_radius` belongs to Stage 5.

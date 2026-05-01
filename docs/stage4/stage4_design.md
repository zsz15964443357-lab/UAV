# Stage 4 Design

## Data Flow

```text
/perception_degradation/degraded_obstacles
        -> uncertainty_obstacle_node
        -> /multimodal_uncertainty/uncertainty_obstacles
        -> /multimodal_uncertainty/uncertainty_markers
        -> stage4_uncertainty_obstacles.csv
```

Stage 4 uses Stage 3 degraded observations as the practical stand-in for pseudo-LiDAR / pseudo-RGB-D observations. The same message shape can later be fed by LV-DOT or `onboard_detector` adapters.

## Message Schema

`UncertaintyObstacle` stores:

- position and velocity
- physical radius
- confidence
- position covariance
- velocity covariance
- scalar position uncertainty
- scalar velocity uncertainty
- perception delay in milliseconds
- source modalities
- effective radius
- risk margin

The covariance is currently isotropic:

```text
P_pos = diag(position_uncertainty^2)
P_vel = diag(velocity_uncertainty^2)
```

## Effective Radius

```text
r_eff = r_obstacle
      + alpha * position_uncertainty
      + beta * velocity_uncertainty
      + gamma * perception_delay_ms
      + delta * (1 - confidence)
```

Interpretation:

- `alpha`: weight for spatial localization uncertainty.
- `beta`: weight for dynamic prediction uncertainty from velocity noise.
- `gamma`: delay-to-distance inflation in meters per millisecond.
- `delta`: low-confidence risk margin.

## RViz Markers

The marker array publishes:

- blue transparent sphere: raw obstacle radius,
- orange transparent sphere: effective risk radius,
- text label: `r`, `r_eff`, and confidence.

## Planner Boundary

The output is not consumed by Intent-MPC in Stage 4. Stage 5 will decide how to map `effective_radius` to `mpc_->updateDynamicObstacles(...)` or a fixed/risk-cost planner mode.

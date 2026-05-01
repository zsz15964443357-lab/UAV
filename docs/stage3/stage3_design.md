# Stage 3 Design

## Scope

Stage 3 creates a configurable degraded perception stream from simulation ground truth.

Current input:

```text
/gazebo/model_states
```

Current outputs:

```text
/perception_degradation/degraded_obstacles
/perception_degradation/degraded_obstacle_markers
~/catkin_ws/experiment_logs/stage3_degraded_obstacles.csv
```

This is intentionally outside the planner. It lets us validate noise, delay, dropout, false positives, and confidence behavior before modifying Intent-MPC internals.

## Message Schema

`DegradedObstacle` stores:

- `id`
- `label`
- `position`
- `velocity`
- `size`
- `radius`
- `confidence`
- `position_noise_std`
- `velocity_noise_std`
- `delay_ms`
- `is_false_positive`
- `source_modalities`

`DegradedObstacleArray` stores:

- message header
- obstacle array
- raw obstacle count
- dropped obstacle count
- false-positive count

## Degradation Model

Position noise:

```text
p_degraded = p_raw + N(0, position_noise_std)
```

Velocity noise:

```text
v_degraded = v_raw + N(0, velocity_noise_std)
```

Delay:

```text
output(t) = degraded(raw_obstacles(t - delay_ms))
```

Dropout:

```text
publish obstacle with probability 1 - dropout_prob
```

False positive:

```text
with probability false_positive_prob, add a synthetic obstacle
```

Confidence:

```text
confidence = clamp(base_confidence + N(0, confidence_noise),
                   min_confidence,
                   max_confidence)
```

## Reproducibility

All random sampling uses a local Python random generator seeded by `random_seed`.

## Planner Interface Boundary

The official Intent-MPC path currently obtains dynamic obstacles through detector/map C++ objects, not through a generic obstacle topic. Feeding degraded obstacles into MPC would require an integration point in `autonomous_flight` or detector wrappers. That belongs to Stage 5. Stage 3 only provides and validates the degraded obstacle stream.

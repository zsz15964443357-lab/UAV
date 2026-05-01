# Stage 6 Experiment Design

## Matrix Shape

The default matrix is one-factor-at-a-time:

```text
clean baseline
position_noise_std: 0.1, 0.2, 0.3 m
delay_ms: 100, 200, 300 ms
dropout_prob: 0.1, 0.3, 0.5
velocity_noise_std: 0.2, 0.5, 1.0 m/s
```

This gives 13 conditions per method/scenario/seed. It avoids the full factorial explosion while producing clear robustness curves.

## Enabled Methods

`intent_mpc`

: Stage 5 `original` mode.

`intent_mpc_fixed_margin`

: Stage 5 `fixed_margin` mode with `fixed_safety_margin=0.3`.

`uncertainty_aware_intent_mpc`

: Stage 5 `uncertainty_aware` mode with the Stage 3/4 degradation and uncertainty pipeline enabled.

## Disabled Placeholders

`navrl` and `navrl_safety_shield` are present in `stage6_matrix.yaml` but disabled. They should be enabled only after a real NavRL launch path exists.

## Scenarios

The scenario names map to existing Gazebo worlds:

- `single_dynamic_crossing`: `simple_box/simple_box_dynamic_3.world`
- `head_on_corridor`: `corridor/corridor_dynamic_9.world`
- `multi_obstacle_crossing`: `square/square_dynamic_7.world`
- `sudden_occlusion_floorplan`: `floorplan3/floorplan3_box_dynamic_4.world`
- `narrow_passage_meeting`: `tunnel/tunnel_straight_dynamic_5.world`

These names are paper-facing labels. They may still need visual confirmation before final experiments.

## Metrics

The Stage 2 recorder provides:

- success
- collision
- minimum distance
- path length
- travel time
- average speed
- optional planning time

Stage 6 adds metadata:

- world name
- planner mode
- fixed safety margin
- degradation axis
- degradation value

## Analysis Outputs

`analyze_stage6_results.py` creates:

- per-scenario/method/degradation summary;
- clean-condition method comparison;
- robustness table by degradation axis and value;
- success, collision, and minimum-distance SVG curves.

## Fairness Note

The current Stage 5 architecture keeps `original` and `fixed_margin` on the original detector/predictor path. The uncertainty-aware method consumes the Stage 4 uncertainty topic. For final paper claims under degraded perception, either:

1. present original/fixed-margin as ideal-perception baselines; or
2. add a common degraded-obstacle adapter so all methods consume the same degraded obstacle state.

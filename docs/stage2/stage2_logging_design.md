# Stage 2 Logging Design

## Scope

Stage 2 records experiment metrics from existing runtime topics. It does not change obstacle detection, prediction, planning, or control behavior.

The recorder observes:

- UAV odometry: `/CERLAB/quadcopter/odom`
- Gazebo model states: `/gazebo/model_states`
- Optional planning time: user-provided `std_msgs/Float64` topic, disabled by default

## Metric Definitions

`success`

: Boolean stored as `0/1`. Default mode is `duration`: success is true when the run lasts at least `success_min_duration`, the path length exceeds `success_min_path_length`, and no collision is detected. A goal-based mode is available by setting `success_mode:=goal` and `goal_position`.

`collision`

: Boolean stored as `0/1`. A collision is detected when the current UAV clearance to any tracked dynamic obstacle is less than or equal to `collision_threshold`.

`min_distance`

: Minimum signed clearance from UAV position to dynamic obstacle bounding boxes over the run, after subtracting `robot_radius`. Negative values indicate overlap under the configured geometry model.

`path_length`

: Integrated Euclidean distance between consecutive odometry positions. Large jumps above `max_odom_step` are ignored to avoid corrupting runs after simulator resets.

`travel_time`

: ROS-time duration between the first and latest valid odometry message.

`average_speed`

: `path_length / travel_time`.

`planning_time`

: Mean value of an optional `std_msgs/Float64` planning time topic. The official Intent-MPC demo does not publish planner compute time as a ROS topic, so the baseline recorder writes `nan` and sets `planning_time_source=unavailable_without_planner_instrumentation`. This preserves the CSV schema without modifying planner code in Stage 2.

## Dynamic Obstacle Distance

The recorder filters Gazebo models whose names start with:

- `person`
- `dynamic_box`
- `dynamic_cylinder`

Obstacle dimensions are parsed from the last three numeric tokens in the model name, matching the convention used by the existing fake detector. For `person*` models, the Gazebo pose is treated as the base pose and the center z coordinate is shifted by half the height, consistent with `onboard_detector/include/onboard_detector/fakeDetector.cpp`.

The default distance mode is `3d`, using signed distance to an axis-aligned bounding box. Set `distance_mode:=2d` for horizontal-only clearance.

## Multimodal Metadata

The run CSV includes fields needed by later pseudo-multimodal and real perception experiments:

- `position_noise_std`
- `velocity_noise_std`
- `delay_ms`
- `dropout_prob`
- `false_positive_prob`
- `confidence_noise`
- `random_seed`

In Stage 2 baseline runs these values should usually be zero. Stage 3 and Stage 4 can reuse the same schema when adding pseudo-LiDAR, pseudo-RGB-D, confidence, covariance, and effective-radius experiments.

## CSV Outputs

Run-level CSV:

```text
stage2_runs.csv
```

One row per experiment run, written when the recorder node shuts down.

Sample-level CSV:

```text
stage2_samples.csv
```

Optional time-series data for quick debugging and post-run sanity checks.

Summary CSV:

```text
stage2_summary.csv
```

Generated offline by `summarize_runs.py`.

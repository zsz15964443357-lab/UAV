# Stage 2 Final Report

## Goal

Build an experiment logging system before changing Intent-MPC algorithms.

## GitHub Plan Input

The latest `uav/main:README.md` adds obstacle-level multimodal fusion as the research direction. Stage 2 remains a logging-only stage, but the CSV schema now needs to support later pseudo-LiDAR / pseudo-RGB-D uncertainty experiments.

## Implementation

Added ROS package:

```text
experiment_tools
```

Main files:

- `experiment_tools/scripts/experiment_metric_recorder.py`
- `experiment_tools/scripts/summarize_runs.py`
- `experiment_tools/scripts/plot_metrics.py`
- `experiment_tools/launch/record_baseline.launch`
- `experiment_tools/config/stage2_default.yaml`

The recorder subscribes to existing runtime topics and appends CSV rows. It does not modify planner/controller/detector code.

## Recorded Fields

Core metrics:

- `success`
- `collision`
- `min_distance`
- `path_length`
- `travel_time`
- `average_speed`
- `planning_time`

Experiment metadata:

- `scenario_name`
- `method_name`
- `position_noise_std`
- `velocity_noise_std`
- `delay_ms`
- `dropout_prob`
- `false_positive_prob`
- `confidence_noise`
- `random_seed`

## Planning Time Limitation

The official demo does not publish per-plan compute time. Stage 2 preserves the `planning_time` column and writes `nan` unless a `std_msgs/Float64` topic is provided through `planning_time_topic`.

This is intentional because Stage 2 should not instrument planner internals. A later optional instrumentation step can publish planner timing without changing the CSV schema.

## Verification

Completed checks:

```bash
python3 -m py_compile \
  experiment_tools/scripts/experiment_metric_recorder.py \
  experiment_tools/scripts/summarize_runs.py \
  experiment_tools/scripts/plot_metrics.py
```

Result: passed.

```bash
python3 experiment_tools/scripts/summarize_runs.py --input <tmp>/runs.csv --output <tmp>/summary.csv
python3 experiment_tools/scripts/plot_metrics.py --input <tmp>/summary.csv --output-dir <tmp>/plots
```

Result: passed. The plotting script generates SVG files using only the Python standard library, avoiding matplotlib/NumPy version conflicts on the host.

```bash
source /opt/ros/noetic/setup.bash
cd /home/intent/catkin_ws
catkin_make
```

Result: passed in the Stage 0 Docker/ROS Noetic container. `experiment_tools` was discovered by catkin and its Python scripts were installed into the devel space.

```bash
roslaunch experiment_tools record_baseline.launch --nodes
```

Result: passed, launch resolves `/experiment_metric_recorder`.

ROS smoke test:

- Started `roscore`.
- Started `experiment_metric_recorder.py`.
- Published synthetic `/CERLAB/quadcopter/odom` and `/gazebo/model_states`.
- Recorder wrote `stage2_runs.csv`.
- The synthetic run produced `collision=1`, `min_distance=-0.6`, and `path_length=2.2`, confirming the metric pipeline is active.

## Conclusion

Stage 2 acceptance criteria are met:

- the new package builds under catkin,
- the recorder can be launched with the official demo,
- run CSV, summary CSV, and plotting scripts are available,
- no Intent-MPC algorithm code is modified.

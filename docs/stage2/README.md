# Stage 2: Experiment Logging System

Goal: record paper-level metrics before changing Intent-MPC planning behavior.

This stage follows the latest research plan in `uav/main:README.md`, including the multimodal uncertainty metadata fields needed by later pseudo-LiDAR and pseudo-RGB-D experiments. Stage 2 is intentionally non-invasive: it observes ROS/Gazebo runtime topics and writes experiment CSV files, but does not alter planner inputs, costs, constraints, or controller code.

## Artifacts

- `experiment_tools`: new ROS package for runtime metric recording and offline analysis.
- `experiment_tools/launch/record_baseline.launch`: launches the recorder alongside an already running demo.
- `experiment_tools/scripts/experiment_metric_recorder.py`: writes one run-level CSV row on shutdown and optional time-series samples.
- `experiment_tools/scripts/summarize_runs.py`: aggregates repeated runs into success, collision, distance, speed, and timing statistics.
- `experiment_tools/scripts/plot_metrics.py`: generates success-rate, collision-rate, and minimum-distance SVG plots from a summary CSV.
- `stage2_execution_prompt.md`: reusable execution prompt for this stage.
- `stage2_logging_design.md`: metric definitions, assumptions, and current limitations.
- `stage2_final_report.md`: completion report and validation notes.

## Runtime Usage

Start the official demo as before:

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch uav_simulator start.launch
roslaunch autonomous_flight intent_mpc_demo_fast_visual.launch
```

In a third terminal, start the recorder:

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch experiment_tools record_baseline.launch \
  scenario_name:=generated_env \
  method_name:=intent_mpc_baseline \
  output_dir:=~/catkin_ws/experiment_logs
```

Stop the recorder with `Ctrl-C` after the run. It appends a row to:

```text
~/catkin_ws/experiment_logs/stage2_runs.csv
```

If sample logging is enabled, it also appends time-series samples to:

```text
~/catkin_ws/experiment_logs/stage2_samples.csv
```

## Offline Analysis

```bash
rosrun experiment_tools summarize_runs.py \
  --input ~/catkin_ws/experiment_logs/stage2_runs.csv \
  --output ~/catkin_ws/experiment_logs/stage2_summary.csv

rosrun experiment_tools plot_metrics.py \
  --input ~/catkin_ws/experiment_logs/stage2_summary.csv \
  --output-dir ~/catkin_ws/experiment_logs/plots \
  --x position_noise_std \
  --series method_name
```

## Acceptance Checklist

- [x] Run-level experiment CSV schema exists.
- [x] Metrics include `success`, `collision`, `min_distance`, `path_length`, `travel_time`, `average_speed`, and `planning_time`.
- [x] Metadata includes scenario, method, noise, delay, dropout, false positives, confidence noise, and random seed.
- [x] Batch summary script exists.
- [x] Plot generation script exists.
- [x] No planner/controller/detector algorithm code is modified.

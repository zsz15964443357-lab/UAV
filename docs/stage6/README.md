# Stage 6: Paper Experiment Matrix

Goal: turn the Stage 5 planner modes into a repeatable paper experiment workflow.

Stage 6 adds:

- a YAML experiment matrix;
- a manifest generator;
- a headless batch runner;
- Stage 6 recorder metadata;
- summary/table/SVG analysis tools.

## Files

- `experiment_tools/config/stage6_matrix.yaml`
- `experiment_tools/scripts/generate_stage6_manifest.py`
- `experiment_tools/scripts/run_stage6_batch.py`
- `experiment_tools/scripts/analyze_stage6_results.py`
- `experiment_tools/launch/record_stage6.launch`
- `uav_simulator/launch/start_stage6.launch`
- `autonomous_flight/launch/intent_mpc_demo_stage6.launch`

## Generate Manifest

Inside the ROS Noetic Docker/container workspace:

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash

rosrun experiment_tools generate_stage6_manifest.py \
  --config ~/catkin_ws/src/Intent-MPC/experiment_tools/config/stage6_matrix.yaml \
  --output ~/catkin_ws/experiment_logs/stage6/stage6_manifest.csv
```

The default matrix produces 585 executable runs:

```text
3 enabled methods x 5 scenarios x 3 seeds x 13 conditions
```

NavRL and NavRL + safety shield are present as disabled placeholders until a launch integration exists.

## Dry Run Commands

```bash
rosrun experiment_tools run_stage6_batch.py \
  --manifest ~/catkin_ws/experiment_logs/stage6/stage6_manifest.csv \
  --output-dir ~/catkin_ws/experiment_logs/stage6 \
  --limit 3
```

This prints the simulator, planner, and recorder commands without launching them.

## Execute A Pilot Batch

```bash
rosrun experiment_tools run_stage6_batch.py \
  --manifest ~/catkin_ws/experiment_logs/stage6/stage6_manifest.csv \
  --output-dir ~/catkin_ws/experiment_logs/stage6 \
  --limit 1 \
  --run-duration-sec 60 \
  --execute
```

Outputs:

```text
~/catkin_ws/experiment_logs/stage6/stage6_runs.csv
~/catkin_ws/experiment_logs/stage6/stage6_samples.csv
~/catkin_ws/experiment_logs/stage6/logs/<run_id>/
```

## Analyze Results

```bash
rosrun experiment_tools analyze_stage6_results.py \
  --input ~/catkin_ws/experiment_logs/stage6/stage6_runs.csv \
  --output-dir ~/catkin_ws/experiment_logs/stage6/analysis
```

Outputs:

- `stage6_summary.csv`
- `stage6_method_comparison_overall.csv`
- `stage6_method_comparison_by_scenario.csv`
- `stage6_robustness.csv`
- `stage6_tables.md`
- `plots/*_success_rate.svg`
- `plots/*_collision_rate.svg`
- `plots/*_min_distance_mean.svg`

## Boundary

Current executable comparisons cover the Intent-MPC family:

- `intent_mpc`
- `intent_mpc_fixed_margin`
- `uncertainty_aware_intent_mpc`

In the current code path, Stage 3/4 degraded uncertainty is consumed by `uncertainty_aware_intent_mpc`. The original and fixed-margin modes still use the existing Intent-MPC detector/predictor path. Treat those as ideal-perception baselines unless a common degraded-obstacle adapter is added before final paper claims.

# Stage 6 Final Report

## Goal

Build the paper experiment workflow for comparing Stage 5 planner modes under controlled scenario and perception-degradation settings.

The latest `uav/main` README defines Stage 6 around:

- comparison methods;
- dynamic-obstacle scenarios;
- degradation dimensions;
- `summary.csv`;
- success, collision, and minimum-distance tables/curves.

## Implementation

Added:

- `experiment_tools/config/stage6_matrix.yaml`
- `experiment_tools/scripts/generate_stage6_manifest.py`
- `experiment_tools/scripts/run_stage6_batch.py`
- `experiment_tools/scripts/analyze_stage6_results.py`
- `experiment_tools/launch/record_stage6.launch`
- `uav_simulator/launch/start_stage6.launch`
- `autonomous_flight/launch/intent_mpc_demo_stage6.launch`

Modified:

- `experiment_tools/scripts/experiment_metric_recorder.py`
- `experiment_tools/CMakeLists.txt`

## Matrix

Default executable matrix:

```text
3 enabled methods
5 scenarios
3 seeds
13 degradation conditions
= 585 runs
```

Enabled methods:

- `intent_mpc`
- `intent_mpc_fixed_margin`
- `uncertainty_aware_intent_mpc`

Disabled placeholders:

- `navrl`
- `navrl_safety_shield`

## Main Commands

Generate manifest:

```bash
rosrun experiment_tools generate_stage6_manifest.py \
  --config ~/catkin_ws/src/Intent-MPC/experiment_tools/config/stage6_matrix.yaml \
  --output ~/catkin_ws/experiment_logs/stage6/stage6_manifest.csv
```

Dry run:

```bash
rosrun experiment_tools run_stage6_batch.py \
  --manifest ~/catkin_ws/experiment_logs/stage6/stage6_manifest.csv \
  --output-dir ~/catkin_ws/experiment_logs/stage6 \
  --limit 3
```

Execute:

```bash
rosrun experiment_tools run_stage6_batch.py \
  --manifest ~/catkin_ws/experiment_logs/stage6/stage6_manifest.csv \
  --output-dir ~/catkin_ws/experiment_logs/stage6 \
  --limit 1 \
  --run-duration-sec 60 \
  --execute
```

Analyze:

```bash
rosrun experiment_tools analyze_stage6_results.py \
  --input ~/catkin_ws/experiment_logs/stage6/stage6_runs.csv \
  --output-dir ~/catkin_ws/experiment_logs/stage6/analysis
```

## Validation

Python syntax:

```bash
python3 -m py_compile \
  experiment_tools/scripts/experiment_metric_recorder.py \
  experiment_tools/scripts/generate_stage6_manifest.py \
  experiment_tools/scripts/run_stage6_batch.py \
  experiment_tools/scripts/analyze_stage6_results.py \
  experiment_tools/scripts/summarize_runs.py \
  experiment_tools/scripts/plot_metrics.py
```

Result: passed.

Manifest generation:

```bash
python3 experiment_tools/scripts/generate_stage6_manifest.py \
  --config experiment_tools/config/stage6_matrix.yaml \
  --output /tmp/stage6_manifest.csv
```

Result: 585 manifest rows plus header. NavRL placeholders were skipped as disabled.

Dry-run command generation:

```bash
python3 experiment_tools/scripts/run_stage6_batch.py \
  --manifest /tmp/stage6_pilot_manifest.csv \
  --workspace /home/intent/catkin_ws \
  --output-dir /tmp/stage6_out \
  --limit 2
```

Result: printed simulator, planner, and recorder commands.

Synthetic analysis:

```bash
python3 experiment_tools/scripts/analyze_stage6_results.py \
  --input <synthetic_stage6_runs.csv> \
  --output-dir <tmp>/out
```

Result: generated `stage6_summary.csv`, method comparison CSV files, `stage6_robustness.csv`, `stage6_tables.md`, and SVG robustness plots.

Docker ROS Noetic build:

```bash
catkin_make
```

Result: passed. Stage 6 scripts were installed into `devel/lib/experiment_tools`.

Launch parsing:

```bash
roslaunch uav_simulator start_stage6.launch --nodes
roslaunch autonomous_flight intent_mpc_demo_stage6.launch --nodes
roslaunch autonomous_flight intent_mpc_demo_stage6.launch dynamic_obstacle_mode:=uncertainty_aware enable_uncertainty_pipeline:=true --nodes
roslaunch experiment_tools record_stage6.launch --nodes
```

Result: passed.

Pilot runtime:

```bash
python3 experiment_tools/scripts/run_stage6_batch.py \
  --manifest /tmp/stage6_smoke_manifest.csv \
  --output-dir /tmp/stage6_smoke \
  --limit 1 \
  --run-duration-sec 8 \
  --odom-timeout-sec 90 \
  --execute
```

Result: passed. The runner produced:

- `/tmp/stage6_smoke/stage6_runs.csv`
- `/tmp/stage6_smoke/stage6_samples.csv`
- per-run simulator/planner/recorder logs

The 8-second smoke run is shorter than the configured success threshold, so its `success=0` is expected.

## Boundary

Stage 6 provides the experiment infrastructure and validates one pilot run. It does not execute the full 585-run matrix in this commit.

Current comparison fairness:

- `uncertainty_aware_intent_mpc` consumes Stage 3/4 degraded uncertainty.
- `intent_mpc` and `intent_mpc_fixed_margin` still use the original detector/predictor path.

Before final paper claims, decide whether to present original/fixed-margin as ideal-perception baselines or add a common degraded-obstacle adapter for all methods.

## Acceptance

Stage 6 satisfies the implementation acceptance criteria:

- Stage 6 prompt and design docs exist.
- Manifest generation works.
- Batch dry-run works.
- Headless batch execution works for one pilot run.
- Stage 6 CSV analysis and SVG generation work on synthetic data.
- Docker catkin build passes.
- Launch parsing passes.

# Stage 1: Intent-MPC Data Flow

Goal: identify where dynamic obstacle state is generated, predicted, passed into MPC, and constrained, so later uncertainty-aware planning can be added with minimal algorithm disruption.

This stage is analysis-only. Do not modify planner behavior in this branch unless a separate issue explicitly says so.

## Source Plan

The overall roadmap was read from `uav/main:README.md`. Stage 1 focuses on:

- Dynamic obstacle state generation.
- `dynamic_predictor` inputs and outputs.
- `trajectory_planner` / `time_optimizer` obstacle costs or constraints.
- Planner obstacle message/data format.
- Insertion point for `obstacle_state -> uncertainty_obstacle_state -> planner`.

## GitHub Tracking

Milestone: [Stage 1 - Intent-MPC Data Flow](https://github.com/zsz15964443357-lab/UAV/milestone/2)

Primary issues:

- [#2 Launch tree, ROS nodes, topics, and TF interfaces](https://github.com/zsz15964443357-lab/UAV/issues/2)
- [#3 Dynamic obstacle generation and message formats](https://github.com/zsz15964443357-lab/UAV/issues/3)
- [#4 `dynamic_predictor` inputs, outputs, and assumptions](https://github.com/zsz15964443357-lab/UAV/issues/4)
- [#5 `trajectory_planner` / `time_optimizer` dynamic obstacle handling](https://github.com/zsz15964443357-lab/UAV/issues/5)
- [#6 Insertion-point design](https://github.com/zsz15964443357-lab/UAV/issues/6)

## Current Branch

Branch: `stage1-code-reading-baseline`

Base: `stage0-reproduction-stability`

Reason: stage 0 already contains the working Docker/ROS Noetic reproduction environment and runtime stability fixes. Starting stage 1 from it preserves the runnable baseline.

## Initial Artifacts

- [`initial_dataflow_map.md`](initial_dataflow_map.md): first-pass map of launch files, modules, topics, data structures, and insertion-point candidates.

## Acceptance Checklist

- [ ] Launch tree and runtime node graph documented.
- [ ] UAV pose/velocity/control/planning topics documented.
- [ ] Dynamic obstacle generation path documented.
- [ ] `dynamic_predictor` input/output format documented.
- [ ] MPC dynamic obstacle constraint path documented.
- [ ] Candidate uncertainty insertion points ranked.
- [ ] Stage 1 final report completed.


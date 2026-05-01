# GitHub Project Workflow

This repository is managed as a staged research project for:

> 基于多模态感知不确定性的无人机动态障碍物安全避障方法研究

The `main` branch currently stores the high-level research plan. The reproduction and code-reading branches keep the executable Intent-MPC codebase and stage-specific documentation.

## Branch Policy

- `main`: stable project overview, roadmap, and accepted stage summaries.
- `stage0-reproduction-stability`: stage 0 reproduction, Docker/ROS Noetic environment, runtime stability fixes, and validation report.
- `stage1-code-reading-baseline`: stage 1 code-reading branch for Intent-MPC data flow, ROS interfaces, and algorithm insertion-point analysis.
- `stage2-experiment-logging`: stage 2 experiment logging package, CSV schema, summary, and plotting scripts.
- `stage3-perception-degradation`: stage 3 perception degradation node, degraded obstacle messages, RViz markers, and CSV samples.
- Future branches:
  - `stage4-multimodal-uncertainty`
  - `stage5-safety-local-planner`
  - `stage6-paper-experiment-matrix`
  - `stage7-paper-materials`

Each stage should end with:

- A stage report under `docs/stageX/`.
- A clear validation checklist.
- A pull request description covering goal, changed files, commands, result, and remaining risks.

## GitHub Milestones

Created milestones:

- `Stage 0 - Reproduction`
- `Stage 1 - Intent-MPC Data Flow`
- `Stage 2 - Experiment Logging`
- `Stage 3 - Perception Degradation`
- `Stage 4 - Multimodal Uncertainty`
- `Stage 5 - Safety Local Planner`
- `Stage 6 - Paper Experiment Matrix`
- `Stage 7 - Paper Materials`

Closed milestones:

- `Stage 0 - Reproduction`
- `Stage 1 - Intent-MPC Data Flow`
- `Stage 2 - Experiment Logging`

Current active milestone:

- `Stage 3 - Perception Degradation`

Stage 3 scope is deliberately limited to an external degraded perception stream. Planner consumption of degraded/uncertain obstacles remains reserved for Stage 5.

## GitHub Issues

Created tracking issues:

- [#1 Stage 0 accepted: Intent-MPC reproduction environment and report](https://github.com/zsz15964443357-lab/UAV/issues/1)
- [#2 Stage 1: map launch tree, ROS nodes, topics, and TF interfaces](https://github.com/zsz15964443357-lab/UAV/issues/2)
- [#3 Stage 1: trace dynamic obstacle generation and message formats](https://github.com/zsz15964443357-lab/UAV/issues/3)
- [#4 Stage 1: analyze dynamic_predictor inputs, outputs, and assumptions](https://github.com/zsz15964443357-lab/UAV/issues/4)
- [#5 Stage 1: inspect trajectory_planner/time_optimizer dynamic obstacle handling](https://github.com/zsz15964443357-lab/UAV/issues/5)
- [#6 Stage 1: produce insertion-point design for uncertainty-aware planning](https://github.com/zsz15964443357-lab/UAV/issues/6)
- [#7 Stage 2: define experiment CSV schema and run metadata](https://github.com/zsz15964443357-lab/UAV/issues/7)
- [#8 Stage 2: implement baseline metric recorder and statistics scripts](https://github.com/zsz15964443357-lab/UAV/issues/8)
- [#9 Stage 3: design perception_degradation_node interface](https://github.com/zsz15964443357-lab/UAV/issues/9)
- [#10 Stage 3: implement configurable perception degradation module](https://github.com/zsz15964443357-lab/UAV/issues/10)
- [#11 Stage 4: define uncertainty obstacle schema and effective radius formula](https://github.com/zsz15964443357-lab/UAV/issues/11)
- [#12 Stage 4: visualize uncertainty and risk radius in RViz](https://github.com/zsz15964443357-lab/UAV/issues/12)
- [#13 Stage 5: add fixed safety margin baseline](https://github.com/zsz15964443357-lab/UAV/issues/13)
- [#14 Stage 5: add uncertainty-aware radius inflation and risk cost](https://github.com/zsz15964443357-lab/UAV/issues/14)
- [#15 Stage 6: define scenario, degradation, seed, and method matrix](https://github.com/zsz15964443357-lab/UAV/issues/15)
- [#16 Stage 6: generate paper tables and robustness curves](https://github.com/zsz15964443357-lab/UAV/issues/16)
- [#17 Stage 7: organize diagrams, paper outline, and failure analysis](https://github.com/zsz15964443357-lab/UAV/issues/17)
- [#18 Management: reconcile README-only main with reproduction branches](https://github.com/zsz15964443357-lab/UAV/issues/18)

## Main Branch Risk

Current state:

- `uav/main` contains the research roadmap README only.
- `stage0-reproduction-stability` contains the full Intent-MPC codebase and reproduction changes.
- These two histories currently have no common merge base.

Before merging stage work into `main`, decide how to reconcile this:

1. Keep `main` as the project homepage and merge the full code through PR, resolving README conflicts.
2. Update `main` to the full codebase plus the project roadmap.

This is tracked in [#18](https://github.com/zsz15964443357-lab/UAV/issues/18).

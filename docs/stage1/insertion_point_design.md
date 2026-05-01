# Insertion Point Design for Uncertainty-Aware Planning

## Goal

The later research goal is to plan safely when multimodal perception is uncertain. The implementation should preserve the official Intent-MPC baseline and add switchable modes:

- Original Intent-MPC.
- Intent-MPC + fixed safety margin.
- Uncertainty-aware Intent-MPC.

## Candidate Ranking

### Rank 1: MPC Obstacle Constraint Construction

Insertion point:

```text
dynamicObstaclesSize + uncertainty terms
  -> effective size / effective radius
  -> mpcPlanner::updateObstacleParam
  -> QP ellipsoid obstacle constraints
```

Primary file:

- `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp`

Key function:

- `mpcPlanner::updateObstacleParam`

Why this is ranked first:

- It is the smallest behavior-changing insertion point.
- It maps directly to the current fixed margin implementation.
- It gives a clean baseline comparison:
  - `dynamicSafetyDist_`
  - larger fixed margin
  - uncertainty-driven margin
- It avoids changing intent prediction while Stage 2/3 metrics are still being built.

Current fixed dynamic obstacle expansion:

```cpp
osize[j](i,0) = dynamicObstaclesSize[i][j](0)/2 + dynamicSafetyDist_;
osize[j](i,1) = dynamicObstaclesSize[i][j](1)/2 + dynamicSafetyDist_;
osize[j](i,2) = dynamicObstaclesSize[i][j](2)/2 + dynamicSafetyDist_;
```

Recommended Stage 5 evolution:

```text
base_half_size = dynamicObstaclesSize[i][j] / 2
margin = fixed_margin or uncertainty_margin
osize = base_half_size + margin
```

Then:

```text
uncertainty_margin =
    alpha * position_uncertainty
  + beta  * velocity_uncertainty
  + gamma * delay
  + delta * (1 - confidence)
```

Implementation note:

This candidate requires Stage 4 to define how uncertainty metadata reaches `mpcPlanner`. If only size is available, `dynamicObstaclesSize` can be temporarily overloaded to carry effective size, but the cleaner design is to introduce a dedicated obstacle state structure first.

### Rank 2: Between Predictor and MPC

Insertion point:

```text
predPos / predSize / intentProb
  -> uncertainty-adjusted predicted obstacles
  -> mpcPlanner::updatePredObstacles
```

Primary files:

- `autonomous_flight/include/autonomous_flight/mpcNavigation.cpp`
- `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp`
- `dynamic_predictor/include/dynamic_predictor/utils.h`

Why this is useful:

- It can adjust future obstacle sizes per prediction horizon step.
- It aligns well with delay and velocity uncertainty.
- It can treat different intents with different uncertainty growth.

Risks:

- Existing `dynamic_predictor::genTraj` already inflates `predSize` using trajectory variance and `zScore_`.
- Additional perception uncertainty must be separated from prediction dispersion to avoid double counting.
- It may require extending `dynamicPredictor::obstacle`.

Recommended use:

Use this after Candidate 1 works and metrics show fixed/effective radius is insufficient.

### Rank 3: Between Detector/Map and Predictor

Insertion point:

```text
box3D / obstacle history
  -> perception_degradation_node or uncertainty wrapper
  -> dynamicPredictor
```

Primary files:

- `onboard_detector/include/onboard_detector/fakeDetector.cpp`
- `onboard_detector/include/onboard_detector/dynamicDetector.cpp`
- `map_manager/include/map_manager/dynamicMap.cpp`
- future ROS node for perception degradation

Why this matters:

- It is the right conceptual location for perception degradation.
- It can model dropout, delay, noise, false positives, and multimodal disagreement before prediction.
- It supports paper experiments about perception uncertainty directly.

Risks:

- It changes predictor input distribution.
- It may complicate debugging before experiment logging is stable.
- Fake detector currently communicates with predictor in-process, not as a clean ROS obstacle topic.

Recommended use:

Implement in Stage 3 as an external degradation path or wrapper first. Avoid modifying `fakeDetector` deeply unless necessary.

## Recommended Phased Plan

### Stage 2: Metrics First

Do not change planning behavior yet.

Add logging for:

- success
- collision
- min distance
- path length
- travel time
- average speed
- planning time
- scenario name
- method name
- noise/delay/dropout/seed metadata

Reason:

Without a stable metrics layer, later algorithm changes cannot be defended in a paper.

### Stage 3: Perception Degradation

Build a configurable degradation node/interface:

```text
original obstacle state
  -> perception_degradation_node
  -> degraded obstacle state
```

Parameters:

- `position_noise_std`
- `velocity_noise_std`
- `delay_ms`
- `dropout_prob`
- `false_positive_prob`
- `confidence_noise`
- `random_seed`

Reason:

This produces controlled failure modes while keeping the original planner available as baseline.

### Stage 4: Uncertainty Representation

Define a unified obstacle schema:

```text
Obstacle {
  position
  velocity
  radius or size
  confidence
  covariance
  source_modalities
  effective_radius
}
```

Also add RViz and CSV logging for:

- raw obstacle size
- uncertainty
- effective risk radius

### Stage 5: Planner Integration

First implementation:

```text
dynamic obstacle size -> effective size -> updateObstacleParam
```

Second implementation:

```text
distance to high-uncertainty obstacle -> risk cost / trajectory score
```

Candidate cost insertion points:

- `mpcPlanner::getSafetyScore`
- candidate trajectory scoring in `makePlanWithPred`

## Files Likely to Change Later

Stage 2:

- New experiment logging package or scripts.
- Possibly `autonomous_flight` or a standalone monitor node subscribing to existing topics.

Stage 3:

- New perception degradation node/package.
- Possible launch/yaml additions.

Stage 4:

- New message or C++ struct for uncertainty obstacle state.
- RViz marker publisher.
- CSV logging extensions.

Stage 5:

- `trajectory_planner/include/trajectory_planner/mpcPlanner.h`
- `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp`
- `autonomous_flight/include/autonomous_flight/mpcNavigation.cpp`
- Config yaml for planner mode selection.

## Guardrails

- Keep original Intent-MPC mode as default.
- Add method flags rather than replacing existing logic.
- Keep fixed safety margin as a required intermediate baseline.
- Do not merge uncertainty modeling into predictor variance without documenting the distinction.
- Every planning change must be paired with metrics and scenario configs.


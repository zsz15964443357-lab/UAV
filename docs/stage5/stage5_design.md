# Stage 5 Design

## Integration Point

Stage 5 integrates at `autonomous_flight/mpcNavigation`, where dynamic obstacles are passed into `trajectory_planner::mpcPlanner`.

Relevant paths:

```text
mpcNavigation::mpcCB
  -> predictor_->getPrediction
  -> mpc_->updatePredObstacles

mpcNavigation::mpcCB
  -> getDynamicObstacles / dynamicMap::getDynamicObstacles
  -> mpc_->updateDynamicObstacles

mpcNavigation::hasDynamicCollision
  -> dynamic obstacle collision check
```

This keeps the MPC solver itself unchanged and makes the method easy to switch off.

## Modes

`original`

: No modification to dynamic obstacle size.

`fixed_margin`

: Size inflation:

```text
size_planner = size_raw + 2 * fixed_safety_margin
```

This is applied to current obstacles and predictor obstacle-size sequences.

`uncertainty_aware`

: Stage 4 gives `radius` and `effective_radius`. The default mapping is:

```text
scale = max(1, effective_radius / radius)
size_planner = size_raw * scale
```

This preserves the obstacle shape while making its bounding radius equal to `effective_radius`. An alternate `add_margin` mode is available:

```text
size_planner = size_raw + 2 * max(0, effective_radius - radius)
```

## Predictor Handling

The official demo uses `use_predictor: true`, so Stage 5 also handles `updatePredObstacles`.

For each predicted obstacle, the implementation:

1. selects the first available predicted position,
2. finds the nearest Stage 4 uncertainty obstacle within `uncertainty_association_distance`,
3. inflates every predicted size sample for that obstacle using the matched `effective_radius`.

If no fresh uncertainty message is available and `uncertainty_fallback_to_original=true`, the planner uses the original predictor sizes. If fallback is disabled, the predictor obstacle set is cleared for that cycle.

## Boundary

This stage implements constraint inflation through dynamic obstacle size. It does not yet add a separate risk-cost term to the MPC objective.

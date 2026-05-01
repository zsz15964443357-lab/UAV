# Stage 5: Safety Local Planner Integration

Goal: make the local planner optionally use dynamic-obstacle safety margins and Stage 4 uncertainty-aware effective radii.

Stage 5 adds a mode switch in `autonomous_flight/mpcNavigation`:

```text
original
fixed_margin
uncertainty_aware
```

The default remains `original`, so the official Intent-MPC demo behavior is unchanged unless a Stage 5 launch file or parameter explicitly enables a new mode.

## Implemented Modes

`original`

: Existing Intent-MPC behavior. Dynamic obstacles from fake detector/map/predictor are passed into MPC unchanged.

`fixed_margin`

: Inflates dynamic obstacle dimensions by `2 * fixed_safety_margin` before calling MPC. This creates the comparison baseline `Intent-MPC + fixed safety margin`.

`uncertainty_aware`

: Subscribes to `/multimodal_uncertainty/uncertainty_obstacles` and uses each obstacle's `effective_radius` to inflate its planner size. If the predictor is enabled, predicted obstacle sizes are inflated by matching predicted obstacle positions to the nearest uncertainty obstacle. If the predictor is disabled, the current uncertainty obstacles are passed directly to MPC.

## Main Files

- `autonomous_flight/include/autonomous_flight/mpcNavigation.h`
- `autonomous_flight/include/autonomous_flight/mpcNavigation.cpp`
- `autonomous_flight/cfg/mpc_navigation/flight_base.yaml`
- `autonomous_flight/launch/intent_mpc_demo_fixed_margin.launch`
- `autonomous_flight/launch/intent_mpc_demo_uncertainty.launch`

## Usage

Load the simulator plugin environment before launching Gazebo:

```bash
source /opt/ros/noetic/setup.bash
source /home/intent/catkin_ws/devel/setup.bash
source /home/intent/catkin_ws/src/Intent-MPC/uav_simulator/gazeboSetup.bash
```

Fixed-margin baseline:

```bash
roslaunch autonomous_flight intent_mpc_demo_fixed_margin.launch fixed_safety_margin:=0.3
```

Uncertainty-aware mode:

```bash
roslaunch autonomous_flight intent_mpc_demo_uncertainty.launch \
  position_noise_std:=0.1 \
  velocity_noise_std:=0.2 \
  delay_ms:=100 \
  confidence_noise:=0.1
```

Use the existing simulator launch in a separate terminal:

```bash
roslaunch uav_simulator start.launch
```

Both Stage 5 demo launch files use `remote_control/launch/mpc_navigation_fast_rviz.launch`, so they open the lighter `rviz_fast` configuration instead of the heavier original RViz view.

## Stage Boundary

Stage 5 implements radius/size inflation integration. It does not add a new nonlinear risk cost term inside the MPC solver. The risk-cost variant remains a later refinement after validating the safer radius-inflation path.

## Acceptance Checklist

- [x] Original mode remains default.
- [x] Fixed margin mode exists.
- [x] Uncertainty-aware mode consumes Stage 4 `effective_radius`.
- [x] Predictor and non-predictor paths both apply the selected mode.
- [x] Launch files exist for fixed-margin and uncertainty-aware demos.
- [x] Catkin build passes.

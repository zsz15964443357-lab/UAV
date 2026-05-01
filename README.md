# Intent Prediction-Driven Model Predictive Control for UAV Planning and Navigation in Dynamic Environments
[![ROS1](https://img.shields.io/badge/ROS1-Noetic-blue.svg)](https://wiki.ros.org/noetic)
[![Linux platform](https://img.shields.io/badge/platform-Ubuntu-27AE60.svg)](https://releases.ubuntu.com/20.04/)
[![license](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT) 
[![Linux platform](https://img.shields.io/badge/platform-linux--64-orange.svg)](https://releases.ubuntu.com/20.04/)
[![Linux platform](https://img.shields.io/badge/platform-linux--arm-brown.svg)](https://releases.ubuntu.com/20.04/)


The original Intent-MPC project implements the Intent Prediction-Driven Model Predictive Control (Intent-MPC) framework, enabling the robot to navigate safely in dynamic environments.

> **Fork / reproduction note**
>
> This fork is used for reproducing the official Intent-MPC demo on a local Ubuntu 22.04 machine with a Docker-based ROS Noetic environment. The original project is maintained by the Intent-MPC authors at [Zhefan-Xu/Intent-MPC](https://github.com/Zhefan-Xu/Intent-MPC). If you use this repository or the reproduced environment for research, please cite the original Intent-MPC paper and refer to the official repository.
>
> 本仓库仅用于在本机复现官方 Intent-MPC demo，并记录复现过程中的环境配置、稳定性修复和可视化优化入口。原始项目、论文和算法贡献均归原作者所有；请优先引用官方仓库和论文。

<table>
  <tr>
    <td><img src="media/intent-MPC-demo1.gif" style="width: 100%;"></td>
    <td><img src="media/intent-MPC-demo2.gif" style="width: 100%;"></td>
    <td><img src="media/intent-MPC-demo3.gif" style="width: 100%;"></td>
  </tr>
</table>


For additional details, please refer to the related paper available here:

Zhefan Xu*, Hanyu Jin*, Xinming Han, Haoyu Shen, and Kenji Shimada, "Intent Prediction-Driven Model Predictive Control for UAV Planning and Navigation in Dynamic Environments”, *IEEE Robotics and Automation Letters (RA-L)*, 2025. [\[IEEE Xplore\]](https://ieeexplore.ieee.org/document/10945375) [\[preprint\]](https://arxiv.org/pdf/2409.15633) [\[YouTube\]](https://youtu.be/4xsEeMB9WPY) [\[BiliBili\]](https://www.bilibili.com/video/BV1e9XhYQEqA/)

*The authors contributed equally.

## News
- **2025-03-25:** The GitHub code, video demos, and relavant papers for our Intent-MPC Navigation framework are released. The authors will actively maintain and update this repo!


## Table of Contents
- [Installation Guide](#I-Installation-Guide)
- [Run a Quick Demo](#II-Run-a-Quick-Demo)
- [Stage 0 Reproduction Notes](#III-Stage-0-Reproduction-Notes)
- [Citation and Reference](#IV-Citation-and-Reference)
- [Acknowledgement](#V-Acknowledgement)

## I. Installation Guide
The system requirements for this repository are as follows. Please ensure your system meets these requirements:
- Ubuntu 18.04/20.04 LTS
- ROS Melodic/Noetic

Please follow the instructions below to install this package.
```
# step1: install dependencies
sudo apt install ros-${ROS_DISTRO}-octomap* && sudo apt install ros-${ROS_DISTRO}-mavros* && sudo apt install ros-${ROS_DISTRO}-vision-msgs

# step 2: clone this repo to your workspace
cd ~/catkin_ws/src
git clone https://github.com/Zhefan-Xu/Intent-MPC.git

# step 3: follow the standard catkin_make procedure
cd ~/catkin_ws
catkin_make

# step 4: add environment variables to your ~/.bashrc
echo 'source path/to/uav_simulator/gazeboSetup.bash' >> ~/.bashrc
```


## II. Run a Quick Demo
Once the package is properly installed, you can run the following command to launch a quick demo of UAV navigation in a dynamic environment.
```
# start the uav simulator
roslaunch uav_simulator start.launch

# launch the intent MPC navigation 
roslaunch autonomous_flight intent_mpc_demo.launch
```
The simulation environment will load in a Gazebo window, while an RViz window visualizes the robot’s sensor data and planned trajectories. The robot will follow a circular path while avoiding both static and dynamic obstacles.


https://github.com/user-attachments/assets/2ed3163f-c4e3-43d3-9ac5-11ac57a344d3



## III. Stage 0 Reproduction Notes
This section records the reproduction work performed on the local machine for the stage 0 objective: run the official Intent-MPC demo and document the engineering changes made for this reproduction branch, without claiming new algorithmic contribution.

### Local environment
- Host OS: Ubuntu 22.04.
- ROS on host: ROS 2 Humble was present, so ROS 1 was isolated in Docker.
- Reproduction environment: Docker image `intent-mpc:noetic-stage0`, based on Ubuntu 20.04 + ROS Noetic.
- Catkin workspace in the container/host bind mount: `/home/ubuntu2204/catkin_ws`.
- Main report: [`docs/stage0/Intent_MPC_stage0_report.md`](docs/stage0/Intent_MPC_stage0_report.md).

### Reproduction commands
Build the Docker image:
```bash
cd /home/ubuntu2204/catkin_ws/src/Intent-MPC
docker build -f docker/Dockerfile.noetic-stage0 -t intent-mpc:noetic-stage0 .
```

Enter the container and build the workspace:
```bash
docker start intent_mpc_debug
docker exec -it intent_mpc_debug bash
cd /home/ubuntu2204/catkin_ws
catkin_make
source devel/setup.bash
```

Run the official demo:
```bash
roslaunch uav_simulator start.launch
roslaunch autonomous_flight intent_mpc_demo.launch
```

Run the smoother visualization variant used on this machine:
```bash
roslaunch uav_simulator start.launch
roslaunch autonomous_flight intent_mpc_demo_fast_visual.launch
```

The fast visualization variant keeps the same simulation/planning stack, avoids opening the heavy Gazebo client window, and uses a lighter RViz configuration.

### Files added for reproduction
- `docker/Dockerfile.noetic-stage0`: ROS Noetic Docker environment for Ubuntu 22.04 hosts.
- `docs/stage0/Intent_MPC_stage0_report.md`: stage 0 environment, build, run, ROS topic, and validation report.
- `autonomous_flight/launch/intent_mpc_demo_fast_visual.launch`: lighter launch entry for smoother visualization.
- `remote_control/launch/mpc_navigation_fast_rviz.launch`: RViz launch wrapper for the lightweight view.
- `remote_control/rviz/mpc_navigation_fast.rviz`: reduced RViz display load.

### Stability changes made in this fork
The official code was kept as the baseline, but the local reproduction branch includes small runtime guards needed to keep the demo stable in this Docker/Ubuntu 22.04 environment:
- `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.h`
- `dynamic_predictor/include/dynamic_predictor/dynamicPredictor.cpp`
- `trajectory_planner/include/trajectory_planner/mpcPlanner.cpp`
- `tracking_controller/include/tracking_controller/trackingController.cpp`
- `uav_simulator/src/quadcopterPlugin.cpp`

These changes guard against non-finite simulation/planning states observed during local reproduction. They are documented as engineering stability fixes for this reproduction branch, not as new Intent-MPC algorithm contributions.

### Validation result
Stage 0 acceptance was reached on this machine:
- Gazebo server starts normally.
- RViz starts normally.
- UAV model is spawned.
- Dynamic obstacles are present and moving.
- UAV odometry remains finite during the monitored run.
- The UAV follows the planned route and avoids obstacles in the demo.
- No blocking missing-topic or TF failure was observed in the final validation run.


## IV. Citation and Reference
If the original Intent-MPC work is useful to your research, please consider citing the paper below.
```
@ARTICLE{Intent-MPC,
  author={Xu, Zhefan and Jin, Hanyu and Han, Xinming and Shen, Haoyu and Shimada, Kenji},
  journal={IEEE Robotics and Automation Letters}, 
  title={Intent Prediction-Driven Model Predictive Control for UAV Planning and Navigation in Dynamic Environments}, 
  year={2025},
  volume={10},
  number={5},
  pages={4946-4953},
  keywords={Trajectory;Vehicle dynamics;Navigation;Planning;Dynamics;Collision avoidance;Autonomous aerial vehicles;Predictive control;Detectors;Heuristic algorithms;Aerial systems: Perception and autonomy;integrated planning and control;RGB-D perception},
  doi={10.1109/LRA.2025.3555937}}
```

Original repository: [https://github.com/Zhefan-Xu/Intent-MPC](https://github.com/Zhefan-Xu/Intent-MPC)

## V. Acknowledgement
This paper is based on results obtained from a project of Programs for Bridging the gap between R\&D and the IDeal society (society 5.0) and Generating Economic and social value (BRIDGE)/Practical Global Research in the AI×Robotics Services, implemented by the Cabinet Office, Government of Japan.

The authors would like to express their sincere gratitude to Professor Kenji Shimada for his great support and all CERLAB UAV team members who contribute to the development of this research.

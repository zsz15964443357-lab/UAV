cmake_minimum_required(VERSION 3.0.2)
project(experiment_tools)

find_package(catkin REQUIRED COMPONENTS
  rospy
  nav_msgs
  gazebo_msgs
  std_msgs
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/experiment_metric_recorder.py
  scripts/summarize_runs.py
  scripts/plot_metrics.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY
  config
  launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

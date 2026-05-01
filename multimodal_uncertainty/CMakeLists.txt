cmake_minimum_required(VERSION 3.0.2)
project(multimodal_uncertainty)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  geometry_msgs
  visualization_msgs
  message_generation
  perception_degradation
)

add_message_files(
  FILES
  UncertaintyObstacle.msg
  UncertaintyObstacleArray.msg
)

generate_messages(
  DEPENDENCIES
  std_msgs
  geometry_msgs
)

catkin_package(
  CATKIN_DEPENDS
  rospy
  std_msgs
  geometry_msgs
  visualization_msgs
  message_runtime
  perception_degradation
)

catkin_install_python(PROGRAMS
  scripts/uncertainty_obstacle_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY
  config
  launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

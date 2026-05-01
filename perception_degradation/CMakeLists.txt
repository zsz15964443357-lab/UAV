cmake_minimum_required(VERSION 3.0.2)
project(perception_degradation)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  geometry_msgs
  gazebo_msgs
  nav_msgs
  visualization_msgs
  message_generation
)

add_message_files(
  FILES
  DegradedObstacle.msg
  DegradedObstacleArray.msg
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
  gazebo_msgs
  nav_msgs
  visualization_msgs
  message_runtime
)

catkin_install_python(PROGRAMS
  scripts/perception_degradation_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY
  config
  launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

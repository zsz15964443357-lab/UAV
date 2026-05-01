#!/usr/bin/env python3
import csv
import math
import os
import re
import uuid
from datetime import datetime, timezone

import rospy
from gazebo_msgs.msg import ModelStates
from nav_msgs.msg import Odometry
from std_msgs.msg import Float64


FLOAT_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+)")


def as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    if value is None:
        return default
    return bool(value)


def as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [value]


def is_finite_vec(vec):
    return all(math.isfinite(v) for v in vec)


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(len(a))))


def signed_distance_to_box(point, center, size, robot_radius, mode):
    dims = 2 if mode == "2d" else 3
    q = [abs(point[i] - center[i]) - size[i] * 0.5 for i in range(dims)]
    outside = math.sqrt(sum(max(v, 0.0) ** 2 for v in q))
    inside = min(max(q), 0.0)
    return outside + inside - robot_radius


class ExperimentMetricRecorder:
    def __init__(self):
        self.scenario_name = rospy.get_param("~scenario_name", "generated_env")
        self.method_name = rospy.get_param("~method_name", "intent_mpc_baseline")
        configured_run_id = rospy.get_param("~run_id", "")
        self.run_id = configured_run_id or self.make_run_id()
        self.notes = rospy.get_param("~notes", "")

        self.position_noise_std = as_float(rospy.get_param("~position_noise_std", 0.0))
        self.velocity_noise_std = as_float(rospy.get_param("~velocity_noise_std", 0.0))
        self.delay_ms = as_float(rospy.get_param("~delay_ms", 0.0))
        self.dropout_prob = as_float(rospy.get_param("~dropout_prob", 0.0))
        self.false_positive_prob = as_float(rospy.get_param("~false_positive_prob", 0.0))
        self.confidence_noise = as_float(rospy.get_param("~confidence_noise", 0.0))
        self.random_seed = rospy.get_param("~random_seed", 0)

        self.odom_topic = rospy.get_param("~odom_topic", "/CERLAB/quadcopter/odom")
        self.model_states_topic = rospy.get_param("~model_states_topic", "/gazebo/model_states")
        self.planning_time_topic = rospy.get_param("~planning_time_topic", "")
        self.target_prefixes = [str(v) for v in as_list(rospy.get_param("~target_prefixes", ["person", "dynamic_box", "dynamic_cylinder"]))]

        self.distance_mode = str(rospy.get_param("~distance_mode", "3d")).lower()
        if self.distance_mode not in ("2d", "3d"):
            rospy.logwarn("Unsupported distance_mode '%s'; falling back to 3d.", self.distance_mode)
            self.distance_mode = "3d"
        self.robot_radius = as_float(rospy.get_param("~robot_radius", 0.35))
        self.collision_threshold = as_float(rospy.get_param("~collision_threshold", 0.0))
        self.max_odom_step = as_float(rospy.get_param("~max_odom_step", 5.0))

        self.success_mode = str(rospy.get_param("~success_mode", "duration")).lower()
        self.success_min_duration = as_float(rospy.get_param("~success_min_duration", 30.0))
        self.success_min_path_length = as_float(rospy.get_param("~success_min_path_length", 0.0))
        self.goal_position = [as_float(v) for v in as_list(rospy.get_param("~goal_position", []))]
        self.goal_tolerance = as_float(rospy.get_param("~goal_tolerance", 0.5))

        output_dir = rospy.get_param("~output_dir", "")
        if not output_dir:
            output_dir = os.path.expanduser("~/catkin_ws/experiment_logs")
        self.output_dir = os.path.abspath(os.path.expanduser(output_dir))
        self.output_csv = self.resolve_path(rospy.get_param("~output_csv", ""), "stage2_runs.csv")
        self.sample_csv = self.resolve_path(rospy.get_param("~sample_csv", ""), "stage2_samples.csv")
        self.write_sample_csv = as_bool(rospy.get_param("~write_sample_csv", True))
        self.sample_period = max(as_float(rospy.get_param("~sample_period", 0.5)), 0.05)

        self.start_wall_time = datetime.now(timezone.utc)
        self.end_wall_time = None
        self.start_ros_time = None
        self.end_ros_time = None
        self.last_odom_time = None
        self.last_position = None
        self.current_position = None
        self.path_length = 0.0
        self.min_distance = math.nan
        self.closest_obstacle_name = ""
        self.collision = False
        self.goal_reached = False
        self.odom_samples = 0
        self.model_state_samples = 0
        self.dynamic_obstacle_count = 0
        self.planning_times = []
        self.finalized = False

        os.makedirs(self.output_dir, exist_ok=True)
        self.odom_sub = rospy.Subscriber(self.odom_topic, Odometry, self.odom_cb, queue_size=50)
        self.model_sub = rospy.Subscriber(self.model_states_topic, ModelStates, self.model_states_cb, queue_size=10)
        self.planning_time_sub = None
        if self.planning_time_topic:
            self.planning_time_sub = rospy.Subscriber(self.planning_time_topic, Float64, self.planning_time_cb, queue_size=100)

        self.sample_timer = None
        if self.write_sample_csv:
            self.sample_timer = rospy.Timer(rospy.Duration(self.sample_period), self.sample_timer_cb)

        rospy.on_shutdown(self.finalize)
        rospy.loginfo(
            "Stage 2 recorder started: run_id=%s scenario=%s method=%s output=%s",
            self.run_id,
            self.scenario_name,
            self.method_name,
            self.output_csv,
        )

    @staticmethod
    def make_run_id():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return "{}_{}".format(stamp, uuid.uuid4().hex[:8])

    def resolve_path(self, configured_path, default_name):
        path = os.path.expanduser(str(configured_path or ""))
        if not path:
            return os.path.join(self.output_dir, default_name)
        if os.path.isabs(path):
            return path
        return os.path.join(self.output_dir, path)

    @staticmethod
    def ros_time_to_sec(stamp):
        if stamp and stamp.to_sec() > 0.0:
            return stamp.to_sec()
        return rospy.Time.now().to_sec()

    def odom_cb(self, msg):
        stamp = self.ros_time_to_sec(msg.header.stamp)
        pos = [
            msg.pose.pose.position.x,
            msg.pose.pose.position.y,
            msg.pose.pose.position.z,
        ]
        if not is_finite_vec(pos):
            rospy.logwarn_throttle(2.0, "Ignoring non-finite odometry position.")
            return

        if self.start_ros_time is None:
            self.start_ros_time = stamp
        self.end_ros_time = stamp
        self.current_position = pos
        self.odom_samples += 1

        if self.last_position is not None:
            step = dist(pos, self.last_position)
            if math.isfinite(step) and (self.max_odom_step <= 0.0 or step <= self.max_odom_step):
                self.path_length += step
            else:
                rospy.logwarn_throttle(2.0, "Ignoring odometry jump %.3f m.", step)

        self.last_position = pos
        self.last_odom_time = stamp
        self.update_goal_reached(pos)

    def update_goal_reached(self, pos):
        if len(self.goal_position) < 3:
            return
        if dist(pos, self.goal_position[:3]) <= self.goal_tolerance:
            self.goal_reached = True

    def planning_time_cb(self, msg):
        value = as_float(msg.data, math.nan)
        if math.isfinite(value):
            self.planning_times.append(value)

    def model_states_cb(self, msg):
        self.model_state_samples += 1
        if self.current_position is None:
            return

        local_min = math.nan
        local_name = ""
        count = 0
        for name, pose in zip(msg.name, msg.pose):
            if not self.is_target_obstacle(name):
                continue
            size = self.parse_obstacle_size(name)
            center = [pose.position.x, pose.position.y, pose.position.z]
            if name.startswith("person"):
                center[2] += size[2] * 0.5
            if not is_finite_vec(center) or not is_finite_vec(size):
                continue

            clearance = signed_distance_to_box(
                self.current_position,
                center,
                size,
                self.robot_radius,
                self.distance_mode,
            )
            if not math.isfinite(local_min) or clearance < local_min:
                local_min = clearance
                local_name = name
            count += 1

        self.dynamic_obstacle_count = count
        if math.isfinite(local_min):
            if not math.isfinite(self.min_distance) or local_min < self.min_distance:
                self.min_distance = local_min
                self.closest_obstacle_name = local_name
            if local_min <= self.collision_threshold:
                self.collision = True

    def is_target_obstacle(self, name):
        return any(name.startswith(prefix) for prefix in self.target_prefixes)

    @staticmethod
    def parse_obstacle_size(name):
        values = [float(v) for v in FLOAT_RE.findall(name)]
        if len(values) >= 3:
            return values[-3:]
        return [0.5, 0.5, 1.8] if name.startswith("person") else [0.5, 0.5, 1.0]

    def sample_timer_cb(self, _event):
        if self.current_position is None:
            return
        row = {
            "run_id": self.run_id,
            "ros_time": self.end_ros_time if self.end_ros_time is not None else "",
            "scenario_name": self.scenario_name,
            "method_name": self.method_name,
            "uav_x": self.current_position[0],
            "uav_y": self.current_position[1],
            "uav_z": self.current_position[2],
            "path_length": self.path_length,
            "min_distance_so_far": self.min_distance,
            "collision": int(self.collision),
            "dynamic_obstacle_count": self.dynamic_obstacle_count,
            "closest_obstacle_name": self.closest_obstacle_name,
        }
        self.write_row(self.sample_csv, self.sample_header(), row)

    def travel_time(self):
        if self.start_ros_time is None or self.end_ros_time is None:
            return 0.0
        return max(0.0, self.end_ros_time - self.start_ros_time)

    def average_speed(self):
        duration = self.travel_time()
        if duration <= 0.0:
            return math.nan
        return self.path_length / duration

    def planning_time_mean(self):
        if not self.planning_times:
            return math.nan
        return sum(self.planning_times) / len(self.planning_times)

    def planning_time_max(self):
        if not self.planning_times:
            return math.nan
        return max(self.planning_times)

    def success(self):
        if self.collision:
            return False
        duration_ok = self.travel_time() >= self.success_min_duration
        path_ok = self.path_length >= self.success_min_path_length
        if self.success_mode == "goal":
            return self.goal_reached
        if self.success_mode == "goal_or_duration":
            return self.goal_reached or (duration_ok and path_ok)
        return duration_ok and path_ok

    @staticmethod
    def run_header():
        return [
            "run_id",
            "stamp_start_utc",
            "stamp_end_utc",
            "ros_time_start",
            "ros_time_end",
            "scenario_name",
            "method_name",
            "position_noise_std",
            "velocity_noise_std",
            "delay_ms",
            "dropout_prob",
            "false_positive_prob",
            "confidence_noise",
            "random_seed",
            "success",
            "collision",
            "min_distance",
            "path_length",
            "travel_time",
            "average_speed",
            "planning_time",
            "planning_time_max",
            "planning_time_samples",
            "planning_time_source",
            "success_mode",
            "goal_reached",
            "num_odom_samples",
            "num_model_state_samples",
            "num_dynamic_obstacles",
            "closest_obstacle_name",
            "target_prefixes",
            "distance_mode",
            "robot_radius",
            "collision_threshold",
            "notes",
        ]

    @staticmethod
    def sample_header():
        return [
            "run_id",
            "ros_time",
            "scenario_name",
            "method_name",
            "uav_x",
            "uav_y",
            "uav_z",
            "path_length",
            "min_distance_so_far",
            "collision",
            "dynamic_obstacle_count",
            "closest_obstacle_name",
        ]

    @staticmethod
    def write_row(path, header, row):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        should_write_header = not os.path.exists(path) or os.path.getsize(path) == 0
        with open(path, "a", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=header)
            if should_write_header:
                writer.writeheader()
            writer.writerow({key: row.get(key, "") for key in header})

    def final_row(self):
        self.end_wall_time = datetime.now(timezone.utc)
        planning_source = self.planning_time_topic or "unavailable_without_planner_instrumentation"
        return {
            "run_id": self.run_id,
            "stamp_start_utc": self.start_wall_time.isoformat(),
            "stamp_end_utc": self.end_wall_time.isoformat(),
            "ros_time_start": self.start_ros_time if self.start_ros_time is not None else "",
            "ros_time_end": self.end_ros_time if self.end_ros_time is not None else "",
            "scenario_name": self.scenario_name,
            "method_name": self.method_name,
            "position_noise_std": self.position_noise_std,
            "velocity_noise_std": self.velocity_noise_std,
            "delay_ms": self.delay_ms,
            "dropout_prob": self.dropout_prob,
            "false_positive_prob": self.false_positive_prob,
            "confidence_noise": self.confidence_noise,
            "random_seed": self.random_seed,
            "success": int(self.success()),
            "collision": int(self.collision),
            "min_distance": self.min_distance,
            "path_length": self.path_length,
            "travel_time": self.travel_time(),
            "average_speed": self.average_speed(),
            "planning_time": self.planning_time_mean(),
            "planning_time_max": self.planning_time_max(),
            "planning_time_samples": len(self.planning_times),
            "planning_time_source": planning_source,
            "success_mode": self.success_mode,
            "goal_reached": int(self.goal_reached),
            "num_odom_samples": self.odom_samples,
            "num_model_state_samples": self.model_state_samples,
            "num_dynamic_obstacles": self.dynamic_obstacle_count,
            "closest_obstacle_name": self.closest_obstacle_name,
            "target_prefixes": ",".join(self.target_prefixes),
            "distance_mode": self.distance_mode,
            "robot_radius": self.robot_radius,
            "collision_threshold": self.collision_threshold,
            "notes": self.notes,
        }

    def finalize(self):
        if self.finalized:
            return
        self.finalized = True
        row = self.final_row()
        self.write_row(self.output_csv, self.run_header(), row)
        rospy.loginfo(
            "Stage 2 recorder wrote run row: success=%s collision=%s min_distance=%s path_length=%.3f output=%s",
            row["success"],
            row["collision"],
            row["min_distance"],
            row["path_length"],
            self.output_csv,
        )


def main():
    rospy.init_node("experiment_metric_recorder")
    ExperimentMetricRecorder()
    rospy.spin()


if __name__ == "__main__":
    main()

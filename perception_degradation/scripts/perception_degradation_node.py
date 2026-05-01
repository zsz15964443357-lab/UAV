#!/usr/bin/env python3
import csv
import math
import os
import random
import re
from collections import deque

import rospy
from gazebo_msgs.msg import ModelStates
from geometry_msgs.msg import Point, Vector3
from nav_msgs.msg import Odometry
from visualization_msgs.msg import Marker, MarkerArray

from perception_degradation.msg import DegradedObstacle, DegradedObstacleArray


FLOAT_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+)")


def as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value, default=0):
    try:
        return int(value)
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


def clamp(value, low, high):
    return max(low, min(high, value))


def finite(values):
    return all(math.isfinite(item) for item in values)


def vector_norm(values):
    return math.sqrt(sum(item * item for item in values))


class RawObstacle:
    def __init__(self, obstacle_id, label, position, velocity, size):
        self.id = obstacle_id
        self.label = label
        self.position = position
        self.velocity = velocity
        self.size = size


class PerceptionDegradationNode:
    def __init__(self):
        self.input_model_states_topic = rospy.get_param("~input_model_states_topic", "/gazebo/model_states")
        self.odom_topic = rospy.get_param("~odom_topic", "/CERLAB/quadcopter/odom")
        self.degraded_obstacles_topic = rospy.get_param("~degraded_obstacles_topic", "/perception_degradation/degraded_obstacles")
        self.marker_topic = rospy.get_param("~marker_topic", "/perception_degradation/degraded_obstacle_markers")
        self.frame_id = rospy.get_param("~frame_id", "map")

        self.target_prefixes = [str(item) for item in as_list(rospy.get_param("~target_prefixes", ["person", "dynamic_box", "dynamic_cylinder"]))]
        self.source_modalities = rospy.get_param("~source_modalities", "pseudo_multimodal_degraded")
        self.publish_rate = max(as_float(rospy.get_param("~publish_rate", 10.0)), 0.1)

        self.position_noise_std = max(as_float(rospy.get_param("~position_noise_std", 0.0)), 0.0)
        self.velocity_noise_std = max(as_float(rospy.get_param("~velocity_noise_std", 0.0)), 0.0)
        self.delay_ms = max(as_float(rospy.get_param("~delay_ms", 0.0)), 0.0)
        self.dropout_prob = clamp(as_float(rospy.get_param("~dropout_prob", 0.0)), 0.0, 1.0)
        self.false_positive_prob = clamp(as_float(rospy.get_param("~false_positive_prob", 0.0)), 0.0, 1.0)
        self.confidence_noise = max(as_float(rospy.get_param("~confidence_noise", 0.0)), 0.0)
        self.random_seed = as_int(rospy.get_param("~random_seed", 0), 0)
        self.base_confidence = as_float(rospy.get_param("~base_confidence", 1.0), 1.0)
        self.min_confidence = as_float(rospy.get_param("~min_confidence", 0.0), 0.0)
        self.max_confidence = as_float(rospy.get_param("~max_confidence", 1.0), 1.0)

        self.false_positive_size = self.float_list(rospy.get_param("~false_positive_size", [0.5, 0.5, 1.8]), [0.5, 0.5, 1.8])
        self.false_positive_velocity_std = max(as_float(rospy.get_param("~false_positive_velocity_std", 0.2)), 0.0)
        self.false_positive_radius_around_uav = max(as_float(rospy.get_param("~false_positive_radius_around_uav", 6.0)), 0.1)
        self.false_positive_z_range = self.float_list(rospy.get_param("~false_positive_z_range", [0.6, 1.8]), [0.6, 1.8])
        self.world_x_range = self.float_list(rospy.get_param("~world_x_range", [-8.0, 8.0]), [-8.0, 8.0])
        self.world_y_range = self.float_list(rospy.get_param("~world_y_range", [-8.0, 8.0]), [-8.0, 8.0])
        self.max_false_positives_per_tick = max(as_int(rospy.get_param("~max_false_positives_per_tick", 1), 1), 0)

        self.write_csv = as_bool(rospy.get_param("~write_csv", True), True)
        output_dir = rospy.get_param("~output_dir", "")
        if not output_dir:
            output_dir = os.path.expanduser("~/catkin_ws/experiment_logs")
        self.output_dir = os.path.abspath(os.path.expanduser(output_dir))
        self.output_csv = self.resolve_path(rospy.get_param("~output_csv", "stage3_degraded_obstacles.csv"))

        self.rng = random.Random(self.random_seed)
        self.name_to_id = {}
        self.next_id = 1
        self.snapshots = deque()
        self.current_odom_position = None

        self.obstacle_pub = rospy.Publisher(self.degraded_obstacles_topic, DegradedObstacleArray, queue_size=10)
        self.marker_pub = rospy.Publisher(self.marker_topic, MarkerArray, queue_size=10)
        self.model_sub = rospy.Subscriber(self.input_model_states_topic, ModelStates, self.model_states_cb, queue_size=10)
        self.odom_sub = rospy.Subscriber(self.odom_topic, Odometry, self.odom_cb, queue_size=20)
        self.publish_timer = rospy.Timer(rospy.Duration(1.0 / self.publish_rate), self.publish_timer_cb)

        if self.write_csv:
            os.makedirs(self.output_dir, exist_ok=True)

        rospy.loginfo(
            "Perception degradation started: pos_noise=%.3f vel_noise=%.3f delay_ms=%.1f dropout=%.3f false_positive=%.3f output=%s",
            self.position_noise_std,
            self.velocity_noise_std,
            self.delay_ms,
            self.dropout_prob,
            self.false_positive_prob,
            self.degraded_obstacles_topic,
        )

    @staticmethod
    def float_list(value, default):
        items = [as_float(item, math.nan) for item in as_list(value)]
        if len(items) < len(default) or not finite(items[: len(default)]):
            return list(default)
        return items[: len(default)]

    def resolve_path(self, configured_path):
        path = os.path.expanduser(str(configured_path or "stage3_degraded_obstacles.csv"))
        if os.path.isabs(path):
            return path
        return os.path.join(self.output_dir, path)

    def odom_cb(self, msg):
        pos = [msg.pose.pose.position.x, msg.pose.pose.position.y, msg.pose.pose.position.z]
        if finite(pos):
            self.current_odom_position = pos

    def model_states_cb(self, msg):
        stamp = rospy.Time.now()
        raw_obstacles = []
        for name, pose, twist in zip(msg.name, msg.pose, msg.twist):
            if not self.is_target_obstacle(name):
                continue
            size = self.parse_obstacle_size(name)
            position = [pose.position.x, pose.position.y, pose.position.z]
            if name.startswith("person"):
                position[2] += size[2] * 0.5
            velocity = [twist.linear.x, twist.linear.y, twist.linear.z]
            if not finite(position) or not finite(velocity) or not finite(size):
                continue
            obstacle_id = self.stable_id(name)
            raw_obstacles.append(RawObstacle(obstacle_id, name, position, velocity, size))

        self.snapshots.append((stamp, raw_obstacles))
        self.trim_snapshots(stamp)

    def trim_snapshots(self, now):
        delay_sec = self.delay_ms / 1000.0
        keep_after = now - rospy.Duration(delay_sec + 2.0)
        while len(self.snapshots) > 1 and self.snapshots[0][0] < keep_after:
            self.snapshots.popleft()

    def stable_id(self, name):
        if name not in self.name_to_id:
            self.name_to_id[name] = self.next_id
            self.next_id += 1
        return self.name_to_id[name]

    def is_target_obstacle(self, name):
        return any(name.startswith(prefix) for prefix in self.target_prefixes)

    @staticmethod
    def parse_obstacle_size(name):
        values = [float(item) for item in FLOAT_RE.findall(name)]
        if len(values) >= 3:
            return values[-3:]
        return [0.5, 0.5, 1.8] if name.startswith("person") else [0.5, 0.5, 1.0]

    @staticmethod
    def radius_from_size(size):
        return 0.5 * vector_norm(size)

    def delayed_snapshot(self, now):
        if not self.snapshots:
            return []
        target_time = now - rospy.Duration(self.delay_ms / 1000.0)
        selected = self.snapshots[0][1]
        for stamp, obstacles in self.snapshots:
            if stamp <= target_time:
                selected = obstacles
            else:
                break
        return selected

    def publish_timer_cb(self, _event):
        now = rospy.Time.now()
        raw_obstacles = self.delayed_snapshot(now)
        degraded = []
        dropped_count = 0

        for obstacle in raw_obstacles:
            if self.rng.random() < self.dropout_prob:
                dropped_count += 1
                continue
            degraded.append(self.degrade_obstacle(obstacle, now, is_false_positive=False))

        false_positives = self.generate_false_positives(now)
        degraded.extend(false_positives)

        msg = DegradedObstacleArray()
        msg.header.stamp = now
        msg.header.frame_id = self.frame_id
        msg.obstacles = degraded
        msg.raw_obstacle_count = len(raw_obstacles)
        msg.dropped_obstacle_count = dropped_count
        msg.false_positive_count = len(false_positives)
        self.obstacle_pub.publish(msg)
        self.marker_pub.publish(self.build_markers(msg))

        if self.write_csv:
            self.write_csv_rows(msg)

    def degrade_obstacle(self, obstacle, stamp, is_false_positive):
        pos = [
            obstacle.position[0] + self.rng.gauss(0.0, self.position_noise_std),
            obstacle.position[1] + self.rng.gauss(0.0, self.position_noise_std),
            obstacle.position[2] + self.rng.gauss(0.0, self.position_noise_std),
        ]
        vel = [
            obstacle.velocity[0] + self.rng.gauss(0.0, self.velocity_noise_std),
            obstacle.velocity[1] + self.rng.gauss(0.0, self.velocity_noise_std),
            obstacle.velocity[2] + self.rng.gauss(0.0, self.velocity_noise_std),
        ]
        confidence = clamp(
            self.base_confidence + self.rng.gauss(0.0, self.confidence_noise),
            self.min_confidence,
            self.max_confidence,
        )

        msg = DegradedObstacle()
        msg.header.stamp = stamp
        msg.header.frame_id = self.frame_id
        msg.id = obstacle.id
        msg.label = obstacle.label
        msg.position = Point(*pos)
        msg.velocity = Vector3(*vel)
        msg.size = Vector3(*obstacle.size)
        msg.radius = self.radius_from_size(obstacle.size)
        msg.confidence = confidence
        msg.position_noise_std = self.position_noise_std
        msg.velocity_noise_std = self.velocity_noise_std
        msg.delay_ms = self.delay_ms
        msg.is_false_positive = is_false_positive
        msg.source_modalities = self.source_modalities
        return msg

    def generate_false_positives(self, stamp):
        false_positives = []
        for _idx in range(self.max_false_positives_per_tick):
            if self.rng.random() >= self.false_positive_prob:
                continue
            raw = self.false_positive_obstacle()
            false_positives.append(self.degrade_obstacle(raw, stamp, is_false_positive=True))
        return false_positives

    def false_positive_obstacle(self):
        if self.current_odom_position is not None:
            angle = self.rng.uniform(-math.pi, math.pi)
            radius = self.rng.uniform(0.5, self.false_positive_radius_around_uav)
            x = self.current_odom_position[0] + radius * math.cos(angle)
            y = self.current_odom_position[1] + radius * math.sin(angle)
        else:
            x = self.rng.uniform(self.world_x_range[0], self.world_x_range[1])
            y = self.rng.uniform(self.world_y_range[0], self.world_y_range[1])
        z = self.rng.uniform(self.false_positive_z_range[0], self.false_positive_z_range[1])
        velocity = [
            self.rng.gauss(0.0, self.false_positive_velocity_std),
            self.rng.gauss(0.0, self.false_positive_velocity_std),
            0.0,
        ]
        obstacle_id = self.stable_id("false_positive")
        return RawObstacle(obstacle_id, "false_positive", [x, y, z], velocity, list(self.false_positive_size))

    def build_markers(self, obstacle_array):
        markers = MarkerArray()
        for idx, obstacle in enumerate(obstacle_array.obstacles):
            box = Marker()
            box.header = obstacle_array.header
            box.ns = "degraded_obstacles"
            box.id = idx * 2
            box.type = Marker.CUBE
            box.action = Marker.ADD
            box.pose.position = obstacle.position
            box.pose.orientation.w = 1.0
            box.scale.x = max(obstacle.size.x, 0.05)
            box.scale.y = max(obstacle.size.y, 0.05)
            box.scale.z = max(obstacle.size.z, 0.05)
            box.color.a = 0.35
            if obstacle.is_false_positive:
                box.color.r = 1.0
                box.color.g = 0.2
                box.color.b = 0.1
            else:
                box.color.r = 0.1
                box.color.g = 0.45
                box.color.b = 1.0
            box.lifetime = rospy.Duration(0.5)
            markers.markers.append(box)

            sphere = Marker()
            sphere.header = obstacle_array.header
            sphere.ns = "degraded_radius"
            sphere.id = idx * 2 + 1
            sphere.type = Marker.SPHERE
            sphere.action = Marker.ADD
            sphere.pose.position = obstacle.position
            sphere.pose.orientation.w = 1.0
            diameter = max(2.0 * obstacle.radius, 0.05)
            sphere.scale.x = diameter
            sphere.scale.y = diameter
            sphere.scale.z = diameter
            sphere.color.a = 0.12
            sphere.color.r = 1.0 - obstacle.confidence
            sphere.color.g = obstacle.confidence
            sphere.color.b = 0.0
            sphere.lifetime = rospy.Duration(0.5)
            markers.markers.append(sphere)
        return markers

    @staticmethod
    def csv_header():
        return [
            "stamp",
            "obstacle_id",
            "label",
            "x",
            "y",
            "z",
            "vx",
            "vy",
            "vz",
            "size_x",
            "size_y",
            "size_z",
            "radius",
            "confidence",
            "position_noise_std",
            "velocity_noise_std",
            "delay_ms",
            "dropout_prob",
            "false_positive_prob",
            "confidence_noise",
            "random_seed",
            "is_false_positive",
            "source_modalities",
            "raw_obstacle_count",
            "dropped_obstacle_count",
            "false_positive_count",
        ]

    def write_csv_rows(self, msg):
        rows = []
        for obstacle in msg.obstacles:
            rows.append(
                {
                    "stamp": msg.header.stamp.to_sec(),
                    "obstacle_id": obstacle.id,
                    "label": obstacle.label,
                    "x": obstacle.position.x,
                    "y": obstacle.position.y,
                    "z": obstacle.position.z,
                    "vx": obstacle.velocity.x,
                    "vy": obstacle.velocity.y,
                    "vz": obstacle.velocity.z,
                    "size_x": obstacle.size.x,
                    "size_y": obstacle.size.y,
                    "size_z": obstacle.size.z,
                    "radius": obstacle.radius,
                    "confidence": obstacle.confidence,
                    "position_noise_std": self.position_noise_std,
                    "velocity_noise_std": self.velocity_noise_std,
                    "delay_ms": self.delay_ms,
                    "dropout_prob": self.dropout_prob,
                    "false_positive_prob": self.false_positive_prob,
                    "confidence_noise": self.confidence_noise,
                    "random_seed": self.random_seed,
                    "is_false_positive": int(obstacle.is_false_positive),
                    "source_modalities": obstacle.source_modalities,
                    "raw_obstacle_count": msg.raw_obstacle_count,
                    "dropped_obstacle_count": msg.dropped_obstacle_count,
                    "false_positive_count": msg.false_positive_count,
                }
            )
        if not rows:
            return
        should_write_header = not os.path.exists(self.output_csv) or os.path.getsize(self.output_csv) == 0
        with open(self.output_csv, "a", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.csv_header())
            if should_write_header:
                writer.writeheader()
            writer.writerows(rows)


def main():
    rospy.init_node("perception_degradation_node")
    PerceptionDegradationNode()
    rospy.spin()


if __name__ == "__main__":
    main()

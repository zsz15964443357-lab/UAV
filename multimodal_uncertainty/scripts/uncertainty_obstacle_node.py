#!/usr/bin/env python3
import csv
import math
import os

from geometry_msgs.msg import Point
import rospy
from visualization_msgs.msg import Marker, MarkerArray

from multimodal_uncertainty.msg import UncertaintyObstacle, UncertaintyObstacleArray
from perception_degradation.msg import DegradedObstacleArray


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


def clamp(value, low, high):
    return max(low, min(high, value))


def diag_covariance(stddev):
    variance = stddev * stddev
    return [
        variance,
        0.0,
        0.0,
        0.0,
        variance,
        0.0,
        0.0,
        0.0,
        variance,
    ]


def copy_point(point):
    return Point(point.x, point.y, point.z)


class UncertaintyObstacleNode:
    def __init__(self):
        self.input_obstacles_topic = rospy.get_param("~input_obstacles_topic", "/perception_degradation/degraded_obstacles")
        self.uncertainty_obstacles_topic = rospy.get_param("~uncertainty_obstacles_topic", "/multimodal_uncertainty/uncertainty_obstacles")
        self.marker_topic = rospy.get_param("~marker_topic", "/multimodal_uncertainty/uncertainty_markers")
        self.frame_id = rospy.get_param("~frame_id", "map")
        self.uncertainty_model = rospy.get_param("~uncertainty_model", "radius_inflation_v1")
        self.source_modalities_override = rospy.get_param("~source_modalities_override", "")

        self.alpha = as_float(rospy.get_param("~alpha", 1.0), 1.0)
        self.beta = as_float(rospy.get_param("~beta", 0.5), 0.5)
        self.gamma = as_float(rospy.get_param("~gamma", 0.002), 0.002)
        self.delta = as_float(rospy.get_param("~delta", 0.8), 0.8)

        self.min_position_uncertainty = max(as_float(rospy.get_param("~min_position_uncertainty", 0.0)), 0.0)
        self.min_velocity_uncertainty = max(as_float(rospy.get_param("~min_velocity_uncertainty", 0.0)), 0.0)
        self.min_effective_radius = max(as_float(rospy.get_param("~min_effective_radius", 0.05)), 0.0)
        self.max_effective_radius = max(as_float(rospy.get_param("~max_effective_radius", 10.0)), self.min_effective_radius)

        self.write_csv = as_bool(rospy.get_param("~write_csv", True), True)
        output_dir = rospy.get_param("~output_dir", "")
        if not output_dir:
            output_dir = os.path.expanduser("~/catkin_ws/experiment_logs")
        self.output_dir = os.path.abspath(os.path.expanduser(output_dir))
        self.output_csv = self.resolve_path(rospy.get_param("~output_csv", "stage4_uncertainty_obstacles.csv"))
        if self.write_csv:
            os.makedirs(self.output_dir, exist_ok=True)

        self.obstacle_pub = rospy.Publisher(self.uncertainty_obstacles_topic, UncertaintyObstacleArray, queue_size=10)
        self.marker_pub = rospy.Publisher(self.marker_topic, MarkerArray, queue_size=10)
        self.obstacle_sub = rospy.Subscriber(self.input_obstacles_topic, DegradedObstacleArray, self.obstacles_cb, queue_size=10)

        rospy.loginfo(
            "Multimodal uncertainty node started: input=%s output=%s alpha=%.3f beta=%.3f gamma=%.4f delta=%.3f",
            self.input_obstacles_topic,
            self.uncertainty_obstacles_topic,
            self.alpha,
            self.beta,
            self.gamma,
            self.delta,
        )

    def resolve_path(self, configured_path):
        path = os.path.expanduser(str(configured_path or "stage4_uncertainty_obstacles.csv"))
        if os.path.isabs(path):
            return path
        return os.path.join(self.output_dir, path)

    def obstacles_cb(self, msg):
        output = UncertaintyObstacleArray()
        output.header = msg.header
        if not output.header.frame_id:
            output.header.frame_id = self.frame_id
        output.raw_obstacle_count = msg.raw_obstacle_count
        output.dropped_obstacle_count = msg.dropped_obstacle_count
        output.false_positive_count = msg.false_positive_count
        output.alpha = self.alpha
        output.beta = self.beta
        output.gamma = self.gamma
        output.delta = self.delta

        for obstacle in msg.obstacles:
            output.obstacles.append(self.to_uncertainty_obstacle(obstacle, output.header))

        self.obstacle_pub.publish(output)
        self.marker_pub.publish(self.build_markers(output))
        if self.write_csv:
            self.write_csv_rows(output)

    def to_uncertainty_obstacle(self, obstacle, header):
        position_uncertainty = max(obstacle.position_noise_std, self.min_position_uncertainty)
        velocity_uncertainty = max(obstacle.velocity_noise_std, self.min_velocity_uncertainty)
        delay_ms = max(obstacle.delay_ms, 0.0)
        confidence = clamp(obstacle.confidence, 0.0, 1.0)
        source_modalities = self.source_modalities_override or obstacle.source_modalities

        risk_margin = (
            self.alpha * position_uncertainty
            + self.beta * velocity_uncertainty
            + self.gamma * delay_ms
            + self.delta * (1.0 - confidence)
        )
        effective_radius = clamp(obstacle.radius + risk_margin, self.min_effective_radius, self.max_effective_radius)
        risk_margin = effective_radius - obstacle.radius

        out = UncertaintyObstacle()
        out.header = header
        out.id = obstacle.id
        out.label = obstacle.label
        out.position = obstacle.position
        out.velocity = obstacle.velocity
        out.size = obstacle.size
        out.radius = obstacle.radius
        out.confidence = confidence
        out.position_covariance = diag_covariance(position_uncertainty)
        out.velocity_covariance = diag_covariance(velocity_uncertainty)
        out.position_uncertainty = position_uncertainty
        out.velocity_uncertainty = velocity_uncertainty
        out.perception_delay = delay_ms
        out.effective_radius = effective_radius
        out.risk_margin = risk_margin
        out.is_false_positive = obstacle.is_false_positive
        out.source_modalities = source_modalities
        out.uncertainty_model = self.uncertainty_model
        return out

    def build_markers(self, obstacle_array):
        markers = MarkerArray()
        delete_all = Marker()
        delete_all.action = Marker.DELETEALL
        markers.markers.append(delete_all)

        for idx, obstacle in enumerate(obstacle_array.obstacles):
            raw = Marker()
            raw.header = obstacle_array.header
            raw.ns = "raw_obstacle_radius"
            raw.id = idx * 3
            raw.type = Marker.SPHERE
            raw.action = Marker.ADD
            raw.pose.position = copy_point(obstacle.position)
            raw.pose.orientation.w = 1.0
            raw.scale.x = max(2.0 * obstacle.radius, 0.05)
            raw.scale.y = max(2.0 * obstacle.radius, 0.05)
            raw.scale.z = max(2.0 * obstacle.radius, 0.05)
            raw.color.r = 0.1
            raw.color.g = 0.45
            raw.color.b = 1.0
            raw.color.a = 0.14
            raw.lifetime = rospy.Duration(0.5)
            markers.markers.append(raw)

            inflated = Marker()
            inflated.header = obstacle_array.header
            inflated.ns = "effective_risk_radius"
            inflated.id = idx * 3 + 1
            inflated.type = Marker.SPHERE
            inflated.action = Marker.ADD
            inflated.pose.position = copy_point(obstacle.position)
            inflated.pose.orientation.w = 1.0
            inflated.scale.x = max(2.0 * obstacle.effective_radius, 0.05)
            inflated.scale.y = max(2.0 * obstacle.effective_radius, 0.05)
            inflated.scale.z = max(2.0 * obstacle.effective_radius, 0.05)
            inflated.color.r = 1.0
            inflated.color.g = 0.35
            inflated.color.b = 0.0
            inflated.color.a = 0.18
            inflated.lifetime = rospy.Duration(0.5)
            markers.markers.append(inflated)

            text = Marker()
            text.header = obstacle_array.header
            text.ns = "uncertainty_text"
            text.id = idx * 3 + 2
            text.type = Marker.TEXT_VIEW_FACING
            text.action = Marker.ADD
            text.pose.position = copy_point(obstacle.position)
            text.pose.position.z += max(obstacle.size.z * 0.5, obstacle.effective_radius) + 0.25
            text.pose.orientation.w = 1.0
            text.scale.z = 0.32
            text.color.r = 1.0
            text.color.g = 1.0
            text.color.b = 1.0
            text.color.a = 0.9
            text.text = "r={:.2f} reff={:.2f} c={:.2f}".format(
                obstacle.radius,
                obstacle.effective_radius,
                obstacle.confidence,
            )
            text.lifetime = rospy.Duration(0.5)
            markers.markers.append(text)
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
            "radius",
            "effective_radius",
            "risk_margin",
            "confidence",
            "position_uncertainty",
            "velocity_uncertainty",
            "perception_delay_ms",
            "position_cov_xx",
            "position_cov_yy",
            "position_cov_zz",
            "velocity_cov_xx",
            "velocity_cov_yy",
            "velocity_cov_zz",
            "alpha",
            "beta",
            "gamma",
            "delta",
            "is_false_positive",
            "source_modalities",
            "uncertainty_model",
            "raw_obstacle_count",
            "dropped_obstacle_count",
            "false_positive_count",
        ]

    def write_csv_rows(self, msg):
        if not msg.obstacles:
            return
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
                    "radius": obstacle.radius,
                    "effective_radius": obstacle.effective_radius,
                    "risk_margin": obstacle.risk_margin,
                    "confidence": obstacle.confidence,
                    "position_uncertainty": obstacle.position_uncertainty,
                    "velocity_uncertainty": obstacle.velocity_uncertainty,
                    "perception_delay_ms": obstacle.perception_delay,
                    "position_cov_xx": obstacle.position_covariance[0],
                    "position_cov_yy": obstacle.position_covariance[4],
                    "position_cov_zz": obstacle.position_covariance[8],
                    "velocity_cov_xx": obstacle.velocity_covariance[0],
                    "velocity_cov_yy": obstacle.velocity_covariance[4],
                    "velocity_cov_zz": obstacle.velocity_covariance[8],
                    "alpha": msg.alpha,
                    "beta": msg.beta,
                    "gamma": msg.gamma,
                    "delta": msg.delta,
                    "is_false_positive": int(obstacle.is_false_positive),
                    "source_modalities": obstacle.source_modalities,
                    "uncertainty_model": obstacle.uncertainty_model,
                    "raw_obstacle_count": msg.raw_obstacle_count,
                    "dropped_obstacle_count": msg.dropped_obstacle_count,
                    "false_positive_count": msg.false_positive_count,
                }
            )

        should_write_header = not os.path.exists(self.output_csv) or os.path.getsize(self.output_csv) == 0
        with open(self.output_csv, "a", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.csv_header())
            if should_write_header:
                writer.writeheader()
            writer.writerows(rows)


def main():
    rospy.init_node("uncertainty_obstacle_node")
    UncertaintyObstacleNode()
    rospy.spin()


if __name__ == "__main__":
    main()

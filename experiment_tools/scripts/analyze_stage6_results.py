#!/usr/bin/env python3
import argparse
import csv
import html
import math
import os
from collections import defaultdict


SUMMARY_GROUP = [
    "scenario_name",
    "method_name",
    "planner_mode",
    "degradation_axis",
    "degradation_value",
    "position_noise_std",
    "velocity_noise_std",
    "delay_ms",
    "dropout_prob",
]

METRICS = [
    "run_count",
    "success_rate",
    "collision_rate",
    "min_distance_mean",
    "min_distance_min",
    "path_length_mean",
    "travel_time_mean",
    "average_speed_mean",
    "planning_time_mean",
    "planning_time_max",
]


def to_float(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else math.nan
    except (TypeError, ValueError):
        return math.nan


def to_bool(value):
    text = str(value).strip().lower()
    return text in ("1", "true", "yes", "success")


def finite_values(rows, key):
    values = [to_float(row.get(key, "")) for row in rows]
    return [value for value in values if math.isfinite(value)]


def mean(values):
    if not values:
        return math.nan
    return sum(values) / len(values)


def summarize(rows):
    successes = [1.0 if to_bool(row.get("success", "")) else 0.0 for row in rows]
    collisions = [1.0 if to_bool(row.get("collision", "")) else 0.0 for row in rows]
    min_distances = finite_values(rows, "min_distance")
    path_lengths = finite_values(rows, "path_length")
    travel_times = finite_values(rows, "travel_time")
    average_speeds = finite_values(rows, "average_speed")
    planning_times = finite_values(rows, "planning_time")
    planning_time_maxes = finite_values(rows, "planning_time_max")
    return {
        "run_count": len(rows),
        "success_rate": mean(successes),
        "collision_rate": mean(collisions),
        "min_distance_mean": mean(min_distances),
        "min_distance_min": min(min_distances) if min_distances else math.nan,
        "path_length_mean": mean(path_lengths),
        "travel_time_mean": mean(travel_times),
        "average_speed_mean": mean(average_speeds),
        "planning_time_mean": mean(planning_times),
        "planning_time_max": max(planning_time_maxes) if planning_time_maxes else math.nan,
    }


def group_rows(rows, columns):
    groups = defaultdict(list)
    for row in rows:
        key = tuple(row.get(column, "") for column in columns)
        groups[key].append(row)
    output = []
    for key, group in sorted(groups.items()):
        row = {column: value for column, value in zip(columns, key)}
        row.update(summarize(group))
        output.append(row)
    return output


def write_csv(path, fieldnames, rows):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def clean_rows(rows):
    return [row for row in rows if row.get("degradation_axis", "clean") == "clean"]


def robustness_rows(rows):
    axes = sorted({row.get("degradation_axis", "") for row in rows if row.get("degradation_axis", "") not in ("", "clean")})
    output = []
    clean_by_method = group_rows(clean_rows(rows), ["method_name", "planner_mode"])
    for axis in axes:
        for clean in clean_by_method:
            row = dict(clean)
            row["degradation_axis"] = axis
            row["degradation_value"] = "0"
            output.append(row)
    nonclean = [row for row in rows if row.get("degradation_axis", "") not in ("", "clean")]
    output.extend(group_rows(nonclean, ["degradation_axis", "degradation_value", "method_name", "planner_mode"]))
    output.sort(key=lambda row: (row.get("degradation_axis", ""), to_float(row.get("degradation_value", "")), row.get("method_name", "")))
    return output


def value_range(values, default_min=0.0, default_max=1.0):
    if not values:
        return default_min, default_max
    lo = min(values)
    hi = max(values)
    if math.isclose(lo, hi):
        pad = 0.5 if math.isclose(lo, 0.0) else abs(lo) * 0.1
        return lo - pad, hi + pad
    pad = (hi - lo) * 0.08
    return lo - pad, hi + pad


def write_svg_curve(rows, axis, metric, ylabel, path):
    axis_rows = [row for row in rows if row.get("degradation_axis") == axis and math.isfinite(to_float(row.get(metric, "")))]
    grouped = defaultdict(list)
    for row in axis_rows:
        grouped[row.get("method_name", "method")].append((to_float(row.get("degradation_value", "")), to_float(row.get(metric, ""))))
    for points in grouped.values():
        points.sort()

    width, height = 860, 460
    left, right, top, bottom = 86, 28, 34, 76
    plot_width = width - left - right
    plot_height = height - top - bottom
    colors = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf"]

    x_values = [point[0] for points in grouped.values() for point in points]
    y_values = [point[1] for points in grouped.values() for point in points]
    x_min, x_max = value_range(x_values)
    if metric in ("success_rate", "collision_rate"):
        y_min, y_max = 0.0, 1.0
    else:
        y_min, y_max = value_range(y_values)

    def map_x(value):
        return left + (value - x_min) / (x_max - x_min) * plot_width

    def map_y(value):
        return top + (y_max - value) / (y_max - y_min) * plot_height

    title = "{} vs {}".format(ylabel, axis)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" viewBox="0 0 {} {}">'.format(width, height, width, height),
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="{}" y="22" font-family="Arial, sans-serif" font-size="16" font-weight="700">{}</text>'.format(left, html.escape(title)),
    ]
    for idx in range(6):
        ratio = idx / 5.0
        y_value = y_min + (y_max - y_min) * ratio
        y = map_y(y_value)
        lines.append('<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="#e5e7eb" stroke-width="1"/>'.format(left, y, left + plot_width, y))
        lines.append('<text x="{}" y="{:.1f}" font-family="Arial, sans-serif" font-size="11" text-anchor="end" fill="#374151">{:.3g}</text>'.format(left - 8, y + 4, y_value))
    lines.append('<line x1="{0}" y1="{1}" x2="{2}" y2="{1}" stroke="#111827" stroke-width="1.2"/>'.format(left, top + plot_height, left + plot_width))
    lines.append('<line x1="{0}" y1="{1}" x2="{0}" y2="{2}" stroke="#111827" stroke-width="1.2"/>'.format(left, top, top + plot_height))

    for x_value in sorted(set(x_values)):
        x = map_x(x_value)
        lines.append('<line x1="{:.1f}" y1="{}" x2="{:.1f}" y2="{}" stroke="#111827" stroke-width="1"/>'.format(x, top + plot_height, x, top + plot_height + 5))
        lines.append('<text x="{:.1f}" y="{}" font-family="Arial, sans-serif" font-size="11" text-anchor="middle" fill="#374151">{:.3g}</text>'.format(x, top + plot_height + 22, x_value))

    lines.append('<text x="{}" y="{}" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" fill="#111827">{}</text>'.format(left + plot_width / 2, height - 20, html.escape(axis)))
    lines.append('<text x="20" y="{}" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" fill="#111827" transform="rotate(-90 20,{})">{}</text>'.format(top + plot_height / 2, top + plot_height / 2, html.escape(ylabel)))

    for idx, (method, points) in enumerate(sorted(grouped.items())):
        color = colors[idx % len(colors)]
        coords = ["{:.1f},{:.1f}".format(map_x(x), map_y(y)) for x, y in points]
        lines.append('<polyline points="{}" fill="none" stroke="{}" stroke-width="2.2"/>'.format(" ".join(coords), color))
        for x, y in points:
            lines.append('<circle cx="{:.1f}" cy="{:.1f}" r="3.5" fill="{}"/>'.format(map_x(x), map_y(y), color))
        legend_y = top + 18 + idx * 18
        lines.append('<rect x="{}" y="{}" width="12" height="12" fill="{}"/>'.format(left + plot_width - 180, legend_y - 10, color))
        lines.append('<text x="{}" y="{}" font-family="Arial, sans-serif" font-size="12" fill="#111827">{}</text>'.format(left + plot_width - 162, legend_y, html.escape(method)))

    lines.append("</svg>")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as svg_file:
        svg_file.write("\n".join(lines))


def markdown_table(headers, rows):
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        values = []
        for header in headers:
            value = row.get(header, "")
            if isinstance(value, float):
                value = "{:.4g}".format(value)
            values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_markdown(path, overall, robustness):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    headers = ["method_name", "run_count", "success_rate", "collision_rate", "min_distance_mean", "travel_time_mean"]
    robust_headers = ["degradation_axis", "degradation_value", "method_name", "run_count", "success_rate", "collision_rate", "min_distance_mean"]
    with open(path, "w", encoding="utf-8") as md_file:
        md_file.write("# Stage 6 Tables\n\n")
        md_file.write("## Clean Overall Method Comparison\n\n")
        md_file.write(markdown_table(headers, overall))
        md_file.write("\n\n## Robustness By Axis\n\n")
        md_file.write(markdown_table(robust_headers, robustness))
        md_file.write("\n")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate Stage 6 summary tables and robustness curves.")
    parser.add_argument("--input", required=True, help="Stage 6 run CSV")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    return parser.parse_args()


def main():
    args = parse_args()
    with open(args.input, newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    os.makedirs(args.output_dir, exist_ok=True)
    summary = group_rows(rows, SUMMARY_GROUP)
    overall = group_rows(clean_rows(rows), ["method_name", "planner_mode"])
    by_scenario = group_rows(clean_rows(rows), ["scenario_name", "method_name", "planner_mode"])
    robust = robustness_rows(rows)

    write_csv(os.path.join(args.output_dir, "stage6_summary.csv"), SUMMARY_GROUP + METRICS, summary)
    write_csv(os.path.join(args.output_dir, "stage6_method_comparison_overall.csv"), ["method_name", "planner_mode"] + METRICS, overall)
    write_csv(os.path.join(args.output_dir, "stage6_method_comparison_by_scenario.csv"), ["scenario_name", "method_name", "planner_mode"] + METRICS, by_scenario)
    write_csv(os.path.join(args.output_dir, "stage6_robustness.csv"), ["degradation_axis", "degradation_value", "method_name", "planner_mode"] + METRICS, robust)
    write_markdown(os.path.join(args.output_dir, "stage6_tables.md"), overall, robust)

    plot_dir = os.path.join(args.output_dir, "plots")
    axes = sorted({row.get("degradation_axis", "") for row in robust if row.get("degradation_axis", "")})
    plots = [
        ("success_rate", "Success Rate"),
        ("collision_rate", "Collision Rate"),
        ("min_distance_mean", "Mean Min Distance (m)"),
    ]
    for axis in axes:
        for metric, ylabel in plots:
            write_svg_curve(robust, axis, metric, ylabel, os.path.join(plot_dir, "{}_{}.svg".format(axis, metric)))

    print("Wrote Stage 6 analysis to {}".format(args.output_dir))


if __name__ == "__main__":
    main()

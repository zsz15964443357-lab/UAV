#!/usr/bin/env python3
import argparse
import csv
import os
import re
import sys

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required to read the Stage 6 matrix config.") from exc


FIELDNAMES = [
    "run_id",
    "scenario_name",
    "world_name",
    "method_name",
    "planner_mode",
    "fixed_safety_margin",
    "enable_uncertainty_pipeline",
    "degradation_axis",
    "degradation_value",
    "position_noise_std",
    "velocity_noise_std",
    "delay_ms",
    "dropout_prob",
    "false_positive_prob",
    "confidence_noise",
    "random_seed",
    "run_duration_sec",
    "sim_pkg",
    "sim_launch",
    "planner_pkg",
    "planner_launch",
    "recorder_pkg",
    "recorder_launch",
]


def slug(value):
    text = str(value).strip().lower()
    text = text.replace(".", "p")
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    return text.strip("_") or "0"


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def load_config(path):
    with open(path, "r", encoding="utf-8") as yaml_file:
        config = yaml.safe_load(yaml_file) or {}
    for key in ("methods", "scenarios", "seeds", "degradation_defaults", "degradation_sweeps"):
        if key not in config:
            raise ValueError("Missing required config key: {}".format(key))
    return config


def build_conditions(config):
    defaults = dict(config["degradation_defaults"])
    conditions = []
    clean = dict(defaults)
    clean["degradation_axis"] = "clean"
    clean["degradation_value"] = "0"
    conditions.append(clean)

    include_axis_zero = bool(config.get("include_axis_zero", False))
    for sweep in config["degradation_sweeps"]:
        axis = sweep["axis"]
        if axis not in defaults:
            raise ValueError("Sweep axis '{}' is not present in degradation_defaults.".format(axis))
        for value in as_list(sweep.get("values")):
            if not include_axis_zero and float(value) == float(defaults.get(axis, 0.0)):
                continue
            condition = dict(defaults)
            condition[axis] = value
            condition["degradation_axis"] = axis
            condition["degradation_value"] = str(value)
            conditions.append(condition)
    return conditions


def enabled_methods(config, include_disabled):
    methods = []
    skipped = []
    for method in config["methods"]:
        if method.get("enabled", True) or include_disabled:
            methods.append(method)
        else:
            skipped.append(method.get("name", "unknown"))
    return methods, skipped


def generate_rows(config, include_disabled=False, limit=0):
    methods, skipped = enabled_methods(config, include_disabled)
    conditions = build_conditions(config)
    seeds = as_list(config["seeds"])
    launch = config.get("launch", {})
    run_duration = config.get("run_duration_sec", 60)

    rows = []
    for scenario in config["scenarios"]:
        for method in methods:
            for condition in conditions:
                for seed in seeds:
                    run_id = "{}_{}_{}_{}_seed{}".format(
                        slug(scenario["name"]),
                        slug(method["name"]),
                        slug(condition["degradation_axis"]),
                        slug(condition["degradation_value"]),
                        slug(seed),
                    )
                    row = {
                        "run_id": run_id,
                        "scenario_name": scenario["name"],
                        "world_name": scenario["world_name"],
                        "method_name": method["name"],
                        "planner_mode": method.get("planner_mode", "original"),
                        "fixed_safety_margin": method.get("fixed_safety_margin", 0.0),
                        "enable_uncertainty_pipeline": str(bool(method.get("enable_uncertainty_pipeline", False))).lower(),
                        "degradation_axis": condition["degradation_axis"],
                        "degradation_value": condition["degradation_value"],
                        "position_noise_std": condition.get("position_noise_std", 0.0),
                        "velocity_noise_std": condition.get("velocity_noise_std", 0.0),
                        "delay_ms": condition.get("delay_ms", 0.0),
                        "dropout_prob": condition.get("dropout_prob", 0.0),
                        "false_positive_prob": condition.get("false_positive_prob", 0.0),
                        "confidence_noise": condition.get("confidence_noise", 0.0),
                        "random_seed": seed,
                        "run_duration_sec": run_duration,
                        "sim_pkg": launch.get("sim_pkg", "uav_simulator"),
                        "sim_launch": launch.get("sim_launch", "start_stage6.launch"),
                        "planner_pkg": launch.get("planner_pkg", "autonomous_flight"),
                        "planner_launch": launch.get("planner_launch", "intent_mpc_demo_stage6.launch"),
                        "recorder_pkg": launch.get("recorder_pkg", "experiment_tools"),
                        "recorder_launch": launch.get("recorder_launch", "record_stage6.launch"),
                    }
                    rows.append(row)
                    if limit and len(rows) >= limit:
                        return rows, skipped
    return rows, skipped


def write_csv(path, rows):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in FIELDNAMES})


def parse_args():
    parser = argparse.ArgumentParser(description="Generate the Stage 6 experiment manifest.")
    parser.add_argument("--config", required=True, help="Stage 6 matrix YAML config")
    parser.add_argument("--output", required=True, help="Output manifest CSV")
    parser.add_argument("--include-disabled", action="store_true", help="Include disabled methods such as future NavRL placeholders")
    parser.add_argument("--limit", type=int, default=0, help="Optional row limit for pilot manifests")
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(args.config)
    rows, skipped = generate_rows(config, include_disabled=args.include_disabled, limit=max(args.limit, 0))
    write_csv(args.output, rows)
    print("Wrote {} Stage 6 manifest rows to {}".format(len(rows), args.output))
    if skipped:
        print("Skipped disabled methods: {}".format(", ".join(skipped)), file=sys.stderr)


if __name__ == "__main__":
    main()

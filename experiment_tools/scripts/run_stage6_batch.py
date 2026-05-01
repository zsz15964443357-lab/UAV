#!/usr/bin/env python3
import argparse
import csv
import os
import shlex
import signal
import subprocess
import time


def truthy(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def source_prefix(workspace):
    repo = os.path.join(workspace, "src", "Intent-MPC")
    return "source /opt/ros/noetic/setup.bash && source {} && source {}".format(
        shlex.quote(os.path.join(workspace, "devel", "setup.bash")),
        shlex.quote(os.path.join(repo, "uav_simulator", "gazeboSetup.bash")),
    )


def roslaunch_command(pkg, launch_file, args):
    parts = ["roslaunch", pkg, launch_file]
    for key, value in args.items():
        if value is None or value == "":
            continue
        parts.append("{}:={}".format(key, value))
    return " ".join(shlex.quote(str(part)) for part in parts)


def bash_command(prefix, command):
    return "{} && {}".format(prefix, command)


def popen(prefix, command, log_path=None):
    stdout = subprocess.DEVNULL
    log_file = None
    if log_path:
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
        log_file = open(log_path, "a", encoding="utf-8")
        stdout = log_file
    proc = subprocess.Popen(
        ["bash", "-lc", bash_command(prefix, command)],
        stdout=stdout,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid,
    )
    proc._stage6_log_file = log_file
    return proc


def terminate(proc, timeout=8.0):
    if proc is None:
        return
    if proc.poll() is not None:
        if getattr(proc, "_stage6_log_file", None):
            proc._stage6_log_file.close()
        return
    try:
        os.killpg(proc.pid, signal.SIGINT)
        proc.wait(timeout=timeout)
    except Exception:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=timeout)
        except Exception:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass
    if getattr(proc, "_stage6_log_file", None):
        proc._stage6_log_file.close()


def run_shell(prefix, command, timeout=None):
    return subprocess.run(
        ["bash", "-lc", bash_command(prefix, command)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )


def wait_for_odom(prefix, timeout_sec):
    deadline = time.time() + timeout_sec
    topics = ["/CERLAB/quadcopter/odom", "/CERLAB/quadcopter/odom_raw"]
    while time.time() < deadline:
        for topic in topics:
            result = run_shell(prefix, "timeout 3s rostopic echo -n 1 {} >/dev/null 2>&1".format(shlex.quote(topic)))
            if result.returncode == 0:
                return True
        time.sleep(1.0)
    return False


def cleanup_ros(prefix):
    commands = [
        "rosnode kill -a >/dev/null 2>&1 || true",
        "pkill -x rviz >/dev/null 2>&1 || true",
        "pkill -x gzclient >/dev/null 2>&1 || true",
        "pkill -x gzserver >/dev/null 2>&1 || true",
        "pkill -x rosmaster >/dev/null 2>&1 || true",
        "pkill -x roscore >/dev/null 2>&1 || true",
    ]
    run_shell(prefix, " ; ".join(commands), timeout=15)


def read_manifest(path):
    with open(path, newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def select_rows(rows, start_index, limit):
    selected = rows[max(start_index, 0):]
    if limit:
        selected = selected[:limit]
    return selected


def row_commands(row, output_dir, gui, rviz):
    sim_args = {
        "world_name": row["world_name"],
        "gui": str(gui).lower(),
        "keyboard": "false",
    }
    planner_args = {
        "dynamic_obstacle_mode": row["planner_mode"],
        "fixed_safety_margin": row["fixed_safety_margin"],
        "enable_uncertainty_pipeline": row["enable_uncertainty_pipeline"],
        "rviz": str(rviz).lower(),
        "position_noise_std": row["position_noise_std"],
        "velocity_noise_std": row["velocity_noise_std"],
        "delay_ms": row["delay_ms"],
        "dropout_prob": row["dropout_prob"],
        "false_positive_prob": row["false_positive_prob"],
        "confidence_noise": row["confidence_noise"],
        "random_seed": row["random_seed"],
        "output_dir": output_dir,
    }
    recorder_args = {
        "scenario_name": row["scenario_name"],
        "method_name": row["method_name"],
        "run_id": row["run_id"],
        "world_name": row["world_name"],
        "planner_mode": row["planner_mode"],
        "fixed_safety_margin": row["fixed_safety_margin"],
        "degradation_axis": row["degradation_axis"],
        "degradation_value": row["degradation_value"],
        "position_noise_std": row["position_noise_std"],
        "velocity_noise_std": row["velocity_noise_std"],
        "delay_ms": row["delay_ms"],
        "dropout_prob": row["dropout_prob"],
        "false_positive_prob": row["false_positive_prob"],
        "confidence_noise": row["confidence_noise"],
        "random_seed": row["random_seed"],
        "output_dir": output_dir,
        "output_csv": "stage6_runs.csv",
        "sample_csv": "stage6_samples.csv",
    }
    return (
        roslaunch_command(row["sim_pkg"], row["sim_launch"], sim_args),
        roslaunch_command(row["planner_pkg"], row["planner_launch"], planner_args),
        roslaunch_command(row["recorder_pkg"], row["recorder_launch"], recorder_args),
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Run or print Stage 6 experiment batches from a manifest CSV.")
    parser.add_argument("--manifest", required=True, help="Stage 6 manifest CSV")
    parser.add_argument("--workspace", default=os.path.expanduser("~/catkin_ws"), help="Catkin workspace path")
    parser.add_argument("--output-dir", default=os.path.expanduser("~/catkin_ws/experiment_logs/stage6"), help="Run output directory")
    parser.add_argument("--start-index", type=int, default=0, help="First manifest row index to run")
    parser.add_argument("--limit", type=int, default=0, help="Maximum rows to run")
    parser.add_argument("--run-duration-sec", type=float, default=0.0, help="Override manifest run duration")
    parser.add_argument("--odom-timeout-sec", type=float, default=60.0, help="Wait time for simulator odometry")
    parser.add_argument("--gui", action="store_true", help="Show Gazebo GUI")
    parser.add_argument("--rviz", action="store_true", help="Show RViz")
    parser.add_argument("--execute", action="store_true", help="Actually run experiments. Without this flag, commands are printed only.")
    return parser.parse_args()


def main():
    args = parse_args()
    rows = select_rows(read_manifest(args.manifest), args.start_index, args.limit)
    prefix = source_prefix(os.path.abspath(os.path.expanduser(args.workspace)))
    os.makedirs(args.output_dir, exist_ok=True)

    if not args.execute:
        for idx, row in enumerate(rows, start=args.start_index):
            sim_cmd, planner_cmd, recorder_cmd = row_commands(row, args.output_dir, args.gui, args.rviz)
            print("# row {} run_id={}".format(idx, row["run_id"]))
            print(bash_command(prefix, sim_cmd))
            print(bash_command(prefix, planner_cmd))
            print(bash_command(prefix, recorder_cmd))
        print("Dry run only. Re-run with --execute to launch experiments.")
        return

    for idx, row in enumerate(rows, start=args.start_index):
        run_id = row["run_id"]
        duration = args.run_duration_sec or float(row.get("run_duration_sec") or 60.0)
        log_dir = os.path.join(args.output_dir, "logs", run_id)
        sim_cmd, planner_cmd, recorder_cmd = row_commands(row, args.output_dir, args.gui, args.rviz)
        print("[stage6] row {} run_id={} duration={}s".format(idx, run_id, duration), flush=True)

        sim_proc = planner_proc = recorder_proc = None
        try:
            sim_proc = popen(prefix, sim_cmd, os.path.join(log_dir, "sim.log"))
            if not wait_for_odom(prefix, args.odom_timeout_sec):
                raise RuntimeError("Timed out waiting for /CERLAB/quadcopter/odom")
            planner_proc = popen(prefix, planner_cmd, os.path.join(log_dir, "planner.log"))
            time.sleep(8.0)
            recorder_proc = popen(prefix, recorder_cmd, os.path.join(log_dir, "recorder.log"))
            time.sleep(duration)
        finally:
            terminate(recorder_proc)
            terminate(planner_proc)
            terminate(sim_proc)
            cleanup_ros(prefix)
            time.sleep(2.0)


if __name__ == "__main__":
    main()

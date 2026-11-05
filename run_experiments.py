"""
run_experiments.py

Runs the simulations for the project and saves the results as CSV files
in the "results" folder. Each setting is run several times and averaged.

How to run:
    Windows:  python run_experiments.py
    Mac:      python3 run_experiments.py

    Quick mode (for a fast live demo):
    Windows:  python run_experiments.py quick
    Mac:      python3 run_experiments.py quick

Experiments:
    exp1_stations_hidden   : vary number of stations, hidden terminals PRESENT
    exp2_size_hidden       : vary packet size,        hidden terminals PRESENT
    exp3_stations_nohidden : vary number of stations, hidden terminals ABSENT
    exp4_size_nohidden     : vary packet size,        hidden terminals ABSENT
"""

import csv
import os
import sys
import time

from simulator import run_simulation


# ---------------------------------------------------------------
# Settings you can change
# ---------------------------------------------------------------
NUM_RUNS = 3          # how many runs are averaged per setting
SIM_TIME_S = 0.5      # simulated seconds per run

# Quick mode: fewer runs and shorter simulations (for the live demo)
if "quick" in sys.argv:
    NUM_RUNS = 2
    SIM_TIME_S = 0.2

STATION_COUNTS = [2, 5, 10, 20, 30]
PACKET_SIZES = [100, 300, 500, 1000, 1500, 2300]

DEFAULT_STATIONS = 10     # used when packet size is the thing being varied
DEFAULT_PAYLOAD = 1500    # used when station count is the thing being varied

EXPERIMENTS = [
    {"name": "exp1_stations_hidden",   "vary": "stations", "values": STATION_COUNTS, "hidden": True},
    {"name": "exp2_size_hidden",       "vary": "size",     "values": PACKET_SIZES,   "hidden": True},
    {"name": "exp3_stations_nohidden", "vary": "stations", "values": STATION_COUNTS, "hidden": False},
    {"name": "exp4_size_nohidden",     "vary": "size",     "values": PACKET_SIZES,   "hidden": False},
]


# ---------------------------------------------------------------
# Folder for the saved files (works on Windows and Mac)
# ---------------------------------------------------------------
BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))
RESULTS_FOLDER = os.path.join(BASE_FOLDER, "results")


def average_runs(num_stations, payload_bytes, use_rts, hidden):
    """Runs the simulation NUM_RUNS times and returns the average of each metric."""
    total_throughput = 0.0
    total_collision = 0.0
    total_delay = 0.0
    total_dropped = 0.0

    for run_number in range(NUM_RUNS):
        seed = run_number + 1
        result = run_simulation(num_stations=num_stations,
                                payload_bytes=payload_bytes,
                                use_rts=use_rts,
                                hidden_terminals=hidden,
                                sim_time_s=SIM_TIME_S,
                                seed=seed)
        total_throughput += result["throughput_mbps"]
        total_collision += result["collision_rate"]
        total_delay += result["avg_delay_ms"]
        total_dropped += result["dropped"]

    averages = {}
    averages["throughput_mbps"] = total_throughput / NUM_RUNS
    averages["collision_rate"] = total_collision / NUM_RUNS
    averages["avg_delay_ms"] = total_delay / NUM_RUNS
    averages["dropped"] = total_dropped / NUM_RUNS
    return averages


def run_one_experiment(experiment):
    """Runs every value of one experiment, for RTS/CTS off and on. Returns the rows."""
    rows = []

    for value in experiment["values"]:
        # Decide the station count and packet size for this value
        if experiment["vary"] == "stations":
            num_stations = value
            payload_bytes = DEFAULT_PAYLOAD
        else:
            num_stations = DEFAULT_STATIONS
            payload_bytes = value

        for use_rts in (False, True):
            if use_rts:
                mode = "on"
            else:
                mode = "off"

            print("  running:", experiment["vary"], "=", value, "| RTS/CTS", mode)

            averages = average_runs(num_stations, payload_bytes,
                                    use_rts, experiment["hidden"])

            row = {}
            row["value"] = value
            row["rts"] = mode
            row["throughput_mbps"] = round(averages["throughput_mbps"], 3)
            row["collision_rate"] = round(averages["collision_rate"], 2)
            row["avg_delay_ms"] = round(averages["avg_delay_ms"], 3)
            row["dropped"] = round(averages["dropped"], 1)
            rows.append(row)

    return rows


def save_csv(experiment_name, rows):
    """Saves the rows to results/<experiment_name>.csv."""
    if not os.path.exists(RESULTS_FOLDER):
        os.makedirs(RESULTS_FOLDER)

    file_path = os.path.join(RESULTS_FOLDER, experiment_name + ".csv")
    column_names = ["value", "rts", "throughput_mbps", "collision_rate",
                    "avg_delay_ms", "dropped"]

    # newline="" stops blank lines between rows on Windows
    with open(file_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=column_names)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return file_path


def print_table(experiment, rows):
    """Prints the results as a table."""
    print()
    print("Results:", experiment["name"])
    print("-" * 72)
    print(f"{experiment['vary']:<10}{'RTS/CTS':<10}{'Throughput':<14}"
          f"{'Collisions':<14}{'Delay':<12}{'Dropped':<8}")
    print(f"{'':<10}{'':<10}{'(Mbps)':<14}{'(%)':<14}{'(ms)':<12}{'(avg)':<8}")
    print("-" * 72)

    for row in rows:
        print(f"{row['value']:<10}{row['rts']:<10}{row['throughput_mbps']:<14}"
              f"{row['collision_rate']:<14}{row['avg_delay_ms']:<12}{row['dropped']:<8}")
    print("-" * 72)


def print_winners(experiment, rows):
    """For each value, says whether RTS/CTS gave higher throughput. Shows the crossover."""
    print("Which is better for throughput?")

    # Rows come in pairs: first "off", then "on" for the same value
    index = 0
    while index < len(rows):
        row_off = rows[index]
        row_on = rows[index + 1]

        if row_on["throughput_mbps"] > row_off["throughput_mbps"]:
            winner = "RTS/CTS ON"
        else:
            winner = "RTS/CTS OFF"

        print("  ", experiment["vary"], "=", row_off["value"], "->", winner,
              "(off:", row_off["throughput_mbps"], "Mbps, on:",
              row_on["throughput_mbps"], "Mbps)")
        index += 2
    print()


def main():
    print("Settings: runs per setting =", NUM_RUNS, "| simulated seconds =", SIM_TIME_S)
    start_time = time.time()

    for experiment in EXPERIMENTS:
        print()
        print("=== Starting", experiment["name"], "===")
        rows = run_one_experiment(experiment)
        print_table(experiment, rows)
        print_winners(experiment, rows)
        saved_path = save_csv(experiment["name"], rows)
        print("Saved:", saved_path)

    elapsed = time.time() - start_time
    print()
    print("All experiments done in", round(elapsed, 1), "seconds.")


if __name__ == "__main__":
    main()
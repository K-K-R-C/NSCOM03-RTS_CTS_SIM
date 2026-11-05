"""
make_plots.py

Reads the CSV files saved by run_experiments.py and makes one image per
experiment. Each image has 3 graphs side by side:
throughput, collision rate, and average delay (RTS/CTS off vs on).

Needs matplotlib:
    Windows:  pip install matplotlib
    Mac:      pip3 install matplotlib

How to run (after run_experiments.py):
    Windows:  python make_plots.py
    Mac:      python3 make_plots.py

Add "show" to also open the graphs on screen:
    python make_plots.py show
"""

import csv
import os
import sys

import matplotlib
if "show" not in sys.argv:
    matplotlib.use("Agg")   # save-only mode, no window needed
import matplotlib.pyplot as plt


BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))
RESULTS_FOLDER = os.path.join(BASE_FOLDER, "results")

# name of the experiment, title, and label for the x axis
EXPERIMENTS = [
    {"name": "exp1_stations_hidden",
     "title": "Hidden terminals present: varying number of stations",
     "x_label": "Number of stations"},
    {"name": "exp2_size_hidden",
     "title": "Hidden terminals present: varying packet size",
     "x_label": "Packet size (bytes)"},
    {"name": "exp3_stations_nohidden",
     "title": "No hidden terminals: varying number of stations",
     "x_label": "Number of stations"},
    {"name": "exp4_size_nohidden",
     "title": "No hidden terminals: varying packet size",
     "x_label": "Packet size (bytes)"},
]

# the three metrics: column name in the CSV, and y axis label
METRICS = [
    {"column": "throughput_mbps", "label": "Throughput (Mbps)"},
    {"column": "collision_rate", "label": "Collision rate (%)"},
    {"column": "avg_delay_ms", "label": "Average delay (ms)"},
]


def read_csv(file_path):
    """Reads one results CSV and returns the x values and the data for off/on."""
    x_values = []
    data = {"off": {}, "on": {}}
    for metric in METRICS:
        data["off"][metric["column"]] = []
        data["on"][metric["column"]] = []

    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mode = row["rts"]
            if mode == "off":
                x_values.append(float(row["value"]))
            for metric in METRICS:
                column = metric["column"]
                data[mode][column].append(float(row[column]))

    return x_values, data


def make_one_image(experiment):
    """Makes and saves the image for one experiment."""
    csv_path = os.path.join(RESULTS_FOLDER, experiment["name"] + ".csv")

    if not os.path.exists(csv_path):
        print("Skipping", experiment["name"], "(CSV not found. Run run_experiments.py first)")
        return

    x_values, data = read_csv(csv_path)

    figure, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    for i in range(3):
        metric = METRICS[i]
        column = metric["column"]
        axis = axes[i]

        axis.plot(x_values, data["off"][column], marker="o", color="red",
                  label="RTS/CTS off")
        axis.plot(x_values, data["on"][column], marker="s", color="blue",
                  label="RTS/CTS on")

        axis.set_xlabel(experiment["x_label"])
        axis.set_ylabel(metric["label"])
        axis.grid(True)
        axis.legend()

    figure.suptitle(experiment["title"])
    figure.tight_layout()

    image_path = os.path.join(RESULTS_FOLDER, experiment["name"] + ".png")
    figure.savefig(image_path, dpi=120)
    print("Saved:", image_path)

    if "show" not in sys.argv:
        plt.close(figure)


def main():
    for experiment in EXPERIMENTS:
        make_one_image(experiment)

    if "show" in sys.argv:
        plt.show()

    print("Done.")


if __name__ == "__main__":
    main()
# Simulation-Based Evaluation of RTS/CTS as an Interference Mitigation Method for the Hidden Terminal Problem in IEEE 802.11 Networks

A simple Python simulator that compares IEEE 802.11 CSMA/CA **with and without RTS/CTS** when hidden terminals are present or absent.

**Course project:** Network Simulation Study (NSS), Computer Technology Department, NIS_S40B-03, Group 3

## Problem Statement

In Wi-Fi networks, stations that cannot sense each other (hidden terminals) can transmit at the same time, causing collisions that reduce throughput and increase delay. RTS/CTS is designed to reduce these collisions, but its control-frame overhead can reduce throughput under some conditions, so it is unclear when it is actually beneficial.

## Objective

To simulate an 802.11 network with and without RTS/CTS and evaluate its effect on **throughput**, **collision rate**, and **delay** as the number of stations and the packet size increase.

## How the Simulator Works

- One Access Point (AP) and N stations. All stations can reach the AP.
- Time moves in 9 microsecond slots. Every station always has a packet to send (saturated traffic).
- Stations are split into two groups. With hidden terminals, the two groups cannot hear each other. Without hidden terminals, everyone hears everyone.
- CSMA/CA backoff: random backoff, contention window doubles after each failure (15 up to 1023), and a packet is dropped after 7 failed attempts.
- **RTS/CTS off:** if two transmissions overlap at the AP, both DATA frames are lost and the full frame time is wasted.
- **RTS/CTS on:** only the short RTS/CTS handshake can collide. After the CTS, all stations stay quiet (NAV), so the DATA is protected. The cost is extra overhead (RTS, CTS, and SIFS gaps) on every packet.

### Simplifications

- DIFS and propagation delay are ignored.
- Collisions are decided only by time overlap at the AP (no capture effect).
- Bit errors are not modeled.
- This is a simplified MAC-level model, not a full 802.11ax simulation.

## Files

| File | Purpose |
|---|---|
| `simulator.py` | The simulation logic (stations, backoff, collisions, metrics) |
| `run_experiments.py` | Runs all experiments, prints tables, saves CSV files |
| `make_plots.py` | Reads the CSV files and saves graphs |
| `results/` | Saved CSV files and PNG graphs |
| `requirements.txt` | Python package needed (matplotlib) |

## Requirements

- Python 3 (from python.org; on Windows, tick "Add Python to PATH" during install)
- matplotlib (only needed for the graphs)

Install matplotlib:

- Windows: `pip install matplotlib`
- Mac: `pip3 install matplotlib`

## How to Run

Use `python` on Windows and `python3` on Mac.

**1. Quick test of the simulator (one comparison):**

```
python simulator.py
```

**2. Run all experiments:**

```
python run_experiments.py
```

For a faster run (fewer runs, shorter simulation), add `quick`:

```
python run_experiments.py quick
```

**3. Make the graphs (after step 2):**

```
python make_plots.py
```

Add `show` to also open the graphs on screen:

```
python make_plots.py show
```

## Experiments

| Experiment | Varies | Hidden terminals |
|---|---|---|
| `exp1_stations_hidden` | Number of stations (2, 5, 10, 20, 30) | Present |
| `exp2_size_hidden` | Packet size (100 to 2300 bytes) | Present |
| `exp3_stations_nohidden` | Number of stations (2, 5, 10, 20, 30) | Absent |
| `exp4_size_nohidden` | Packet size (100 to 2300 bytes) | Absent |

Each experiment is run with RTS/CTS off and on, and each setting is averaged over several runs.

## Metrics

- **Throughput (Mbps):** successfully delivered payload bits per second
- **Collision rate (%):** failed attempts divided by total transmission attempts
- **Average delay (ms):** time from when a packet starts waiting until it is delivered
- **Dropped packets:** packets discarded after reaching the retry limit

## Output

Results are saved in the `results/` folder:

- `<experiment_name>.csv` for the data
- `<experiment_name>.png` for the graphs (throughput, collision rate, delay)

## Group Members

- Trisha Mae R. Bendol
- Karl Kristoffer R. Camato
- Ryan James Malapitan
- Sofia Ysabela De Leon

## References

1. M. Z. Ali, J. Mišić, and V. B. Mišić, "Performance analysis of IEEE 802.11ax heterogeneous network in the presence of hidden terminals," arXiv:1908.01834, 2019.
2. Z. Chen, Y. Zhong, and M. Haenggi, "Cross-link RTS/CTS for MLO mm-Wave WLANs," arXiv:2511.05027, 2025.
3. V. Sathya, M. I. Rochman, and M. Ghosh, "Hidden-nodes in coexisting LAA & Wi-Fi: a measurement study of real deployments," arXiv:2103.15591, 2021.

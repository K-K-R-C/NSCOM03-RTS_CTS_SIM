"""
simulator.py

A simple slot-based simulator of IEEE 802.11 CSMA/CA with one Access Point (AP)
and N stations, with or without RTS/CTS, and with or without hidden terminals.

How the model works (kept simple on purpose):
  - Time moves in slots (9 microseconds each).
  - Every station always has a packet to send (saturated traffic).
  - Stations are split into two groups (group 0 and group 1).
      * hidden_terminals = True  -> the two groups cannot hear each other,
                                    but all stations can reach the AP.
      * hidden_terminals = False -> everyone can hear everyone.
  - Without RTS/CTS: a station sends the whole DATA frame. If another
    transmission overlaps it at the AP, BOTH frames are lost, and the full
    frame time is wasted.
  - With RTS/CTS: a station first sends a short RTS, waits SIFS, and gets a
    CTS from the AP. Only this short handshake can collide. After the CTS,
    every station hears the AP and stays quiet (NAV), so the DATA is safe.
    The price is extra overhead (RTS + CTS + extra SIFS gaps) on every packet.

Simplifications (both modes are treated the same, so the comparison is fair):
  - DIFS and propagation delay are ignored.
  - Collisions are decided by time overlap at the AP only (no capture effect).
  - Channel errors (bit errors) are not modeled.
"""

import math
import random


def default_config():
    """Returns the default 802.11 timing and size settings."""
    config = {
        "slot_us": 9,              # one slot, in microseconds
        "sifs_us": 16,             # short inter-frame space
        "phy_header_us": 20,       # time for the physical header of every frame
        "data_rate_mbps": 54,      # rate used for DATA frames
        "basic_rate_mbps": 24,     # rate used for RTS, CTS and ACK
        "mac_header_bytes": 28,    # MAC header added to every DATA frame
        "rts_bytes": 20,
        "cts_bytes": 14,
        "ack_bytes": 14,
        "cw_min": 15,              # smallest contention window
        "cw_max": 1023,            # largest contention window
        "retry_limit": 7,          # packet is dropped after this many failures
    }
    return config


def to_slots(time_us, slot_us):
    """Converts microseconds to a whole number of slots (rounded up)."""
    return math.ceil(time_us / slot_us)


def frame_time_us(num_bytes, rate_mbps, phy_header_us):
    """Time to send one frame, in microseconds."""
    # bits divided by Mbps gives microseconds
    return phy_header_us + (num_bytes * 8) / rate_mbps


def build_timing(payload_bytes, config):
    """
    Works out how many slots each part of a transmission takes.
    Returns a dictionary of lengths in slots.
    """
    slot_us = config["slot_us"]
    phy = config["phy_header_us"]

    data_us = frame_time_us(payload_bytes + config["mac_header_bytes"],
                            config["data_rate_mbps"], phy)
    rts_us = frame_time_us(config["rts_bytes"], config["basic_rate_mbps"], phy)
    cts_us = frame_time_us(config["cts_bytes"], config["basic_rate_mbps"], phy)
    ack_us = frame_time_us(config["ack_bytes"], config["basic_rate_mbps"], phy)

    data_slots = to_slots(data_us, slot_us)
    rts_slots = to_slots(rts_us, slot_us)
    cts_slots = to_slots(cts_us, slot_us)
    ack_slots = to_slots(ack_us, slot_us)
    sifs_slots = to_slots(config["sifs_us"], slot_us)

    timing = {}

    # Without RTS/CTS: DATA + SIFS + ACK. The whole thing can be hit by a collision.
    timing["plain_length"] = data_slots + sifs_slots + ack_slots

    # With RTS/CTS, part 1: RTS + SIFS + CTS. This is the only part that can collide.
    timing["handshake_length"] = rts_slots + sifs_slots + cts_slots

    # With RTS/CTS, part 2: SIFS + DATA + SIFS + ACK. Protected by NAV.
    timing["protected_length"] = sifs_slots + data_slots + sifs_slots + ack_slots

    return timing


class Station:
    """One Wi-Fi station."""

    def __init__(self, station_id, group, cw_min):
        self.station_id = station_id
        self.group = group              # 0 or 1
        self.cw = cw_min                # current contention window
        self.backoff = 0                # slots left to wait
        self.retries = 0                # failed attempts for the current packet
        self.packet_start = 0           # slot when the current packet started waiting

        # state is one of: "backoff", "handshake", "plain", "protected"
        self.state = "backoff"
        self.state_end = 0              # slot when the current state finishes
        self.collided = False           # was the current attempt hit by a collision?


def start_new_packet(station, t, config, rng):
    """Resets a station so it is ready to send a fresh packet."""
    station.cw = config["cw_min"]
    station.retries = 0
    station.packet_start = t
    station.backoff = rng.randint(0, station.cw)
    station.state = "backoff"
    station.collided = False


def handle_success(station, t, payload_bytes, config, rng, stats):
    """Called when a packet is delivered successfully."""
    stats["delivered"] += 1
    stats["bits"] += payload_bytes * 8
    stats["delay_slots"] += (t - station.packet_start)
    start_new_packet(station, t, config, rng)


def handle_failure(station, t, config, rng, stats):
    """Called when an attempt fails because of a collision."""
    stats["collisions"] += 1
    station.retries += 1
    station.collided = False

    if station.retries >= config["retry_limit"]:
        # Too many failures: drop the packet and start a new one.
        stats["dropped"] += 1
        start_new_packet(station, t, config, rng)
    else:
        # Double the contention window (2*cw + 1 keeps it as 15, 31, 63, ...)
        station.cw = station.cw * 2 + 1
        if station.cw > config["cw_max"]:
            station.cw = config["cw_max"]
        station.backoff = rng.randint(0, station.cw)
        station.state = "backoff"


def run_simulation(num_stations, payload_bytes, use_rts, hidden_terminals,
                   sim_time_s=1.0, seed=1, config=None):
    """
    Runs one simulation and returns a dictionary of results.

    num_stations      : how many stations talk to the AP
    payload_bytes     : size of the data in each packet
    use_rts           : True = RTS/CTS on, False = RTS/CTS off
    hidden_terminals  : True = two groups cannot hear each other
    sim_time_s        : simulated time in seconds
    seed              : random seed (same seed gives the same result)
    """
    if config is None:
        config = default_config()

    rng = random.Random(seed)
    timing = build_timing(payload_bytes, config)
    total_slots = int(sim_time_s * 1000000 / config["slot_us"])

    # Create the stations. First half goes to group 0, the rest to group 1.
    stations = []
    for i in range(num_stations):
        if i < num_stations // 2:
            group = 0
        else:
            group = 1
        station = Station(i, group, config["cw_min"])
        start_new_packet(station, 0, config, rng)
        stations.append(station)

    # Counters for the results
    stats = {
        "delivered": 0,
        "bits": 0,
        "delay_slots": 0,
        "collisions": 0,
        "attempts": 0,
        "dropped": 0,
    }

    # ---- Main loop: one pass per slot ----
    for t in range(total_slots):

        # STEP 1: finish any transmission that ends in this slot
        for s in stations:
            if s.state == "backoff":
                continue
            if t < s.state_end:
                continue

            if s.state == "handshake":
                if s.collided:
                    handle_failure(s, t, config, rng, stats)
                else:
                    # Handshake worked. Now the protected DATA phase begins.
                    s.state = "protected"
                    s.state_end = t + timing["protected_length"]
            elif s.state == "plain":
                if s.collided:
                    handle_failure(s, t, config, rng, stats)
                else:
                    handle_success(s, t, payload_bytes, config, rng, stats)
            elif s.state == "protected":
                handle_success(s, t, payload_bytes, config, rng, stats)

        # STEP 2: decide what each group can sense right now
        protected_any = False
        transmitting_in_group = [False, False]
        for s in stations:
            if s.state == "protected":
                protected_any = True
            elif s.state == "handshake" or s.state == "plain":
                transmitting_in_group[s.group] = True

        busy = [False, False]
        for g in range(2):
            other = 1 - g
            # Everyone hears the AP's CTS, so a protected exchange blocks all.
            if protected_any:
                busy[g] = True
            # A station always hears its own group.
            if transmitting_in_group[g]:
                busy[g] = True
            # The other group is only heard if there are no hidden terminals.
            if (not hidden_terminals) and transmitting_in_group[other]:
                busy[g] = True

        # STEP 3: stations in backoff count down (if idle) or start sending
        for s in stations:
            if s.state != "backoff":
                continue
            if busy[s.group]:
                continue  # channel busy: freeze the counter

            if s.backoff > 0:
                s.backoff -= 1
            else:
                # Counter is zero: start a transmission now
                stats["attempts"] += 1
                s.collided = False
                if use_rts:
                    s.state = "handshake"
                    s.state_end = t + timing["handshake_length"]
                else:
                    s.state = "plain"
                    s.state_end = t + timing["plain_length"]

        # STEP 4: collision check. If two or more are transmitting at the AP
        # at the same time, all of them are marked as collided.
        transmitting_now = []
        for s in stations:
            if s.state == "handshake" or s.state == "plain":
                transmitting_now.append(s)
        if len(transmitting_now) > 1:
            for s in transmitting_now:
                s.collided = True

    # ---- Work out the final numbers ----
    total_time_us = total_slots * config["slot_us"]
    results = {}

    # bits divided by microseconds gives Mbps
    results["throughput_mbps"] = stats["bits"] / total_time_us

    if stats["attempts"] > 0:
        results["collision_rate"] = 100.0 * stats["collisions"] / stats["attempts"]
    else:
        results["collision_rate"] = 0.0

    if stats["delivered"] > 0:
        avg_delay_us = (stats["delay_slots"] / stats["delivered"]) * config["slot_us"]
        results["avg_delay_ms"] = avg_delay_us / 1000.0
    else:
        results["avg_delay_ms"] = 0.0

    results["delivered"] = stats["delivered"]
    results["dropped"] = stats["dropped"]
    results["attempts"] = stats["attempts"]
    return results


# Quick self-test: run "python simulator.py" to see one comparison.
if __name__ == "__main__":
    print("Quick test: 10 stations, 1500-byte packets, hidden terminals present")
    print("-" * 60)

    for use_rts in (False, True):
        if use_rts:
            label = "RTS/CTS ON "
        else:
            label = "RTS/CTS OFF"

        r = run_simulation(num_stations=10, payload_bytes=1500,
                           use_rts=use_rts, hidden_terminals=True,
                           sim_time_s=1.0, seed=1)

        print(label,
              "| throughput:", round(r["throughput_mbps"], 2), "Mbps",
              "| collisions:", round(r["collision_rate"], 1), "%",
              "| delay:", round(r["avg_delay_ms"], 2), "ms",
              "| dropped:", r["dropped"])
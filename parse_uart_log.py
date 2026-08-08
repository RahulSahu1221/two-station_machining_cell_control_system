#!/usr/bin/env python3
"""
parse_uart_log.py

Parses the UART state-transition log captured from the Proteus Virtual
Terminal (see Project Master Reference, Section 4 / Section 22.11) and
produces:

  1. A timeline/step plot (PNG) showing which state the system was in,
     over time, with fault events clearly marked.
  2. A parsed CSV of every transition event (timestamp, from-state,
     to-state, fault reason if any).
  3. A short text summary printed to the console (total run time,
     number of transitions, number of faults, time spent in each state).

Expected log line formats (exactly as produced by logger.c):

    [00:03.214] IDLE -> LOADED
    [00:12.487] MACHINING -> FAULT (reason: OVERLOAD_TRIP)

Usage:
    python parse_uart_log.py path/to/log.txt
    python parse_uart_log.py path/to/log.txt --output timeline.png --csv events.csv
    python parse_uart_log.py path/to/log.txt --title "Overload Trip Scenario"

No arguments beyond the log file are required — sensible defaults are
used for the output filenames, derived from the input filename.
"""

import argparse
import csv
import os
import re
import sys

# Matplotlib is only imported after argument parsing / file validation,
# so a missing dependency doesn't hide a more basic "file not found"
# style mistake behind a confusing import error.


# The five states in the order they should appear on the y-axis of the
# timeline plot, from bottom to top. This order matches the sequence
# described in the Project Master Reference, Section 10.1.
STATE_ORDER = ["IDLE", "LOADED", "MACHINING", "DONE", "FAULT"]

# Regex matches a line like:
#   [00:03.214] IDLE -> LOADED
#   [00:12.487] MACHINING -> FAULT (reason: OVERLOAD_TRIP)
LOG_LINE_PATTERN = re.compile(
    r"\[(?P<minutes>\d{2}):(?P<seconds>\d{2})\.(?P<millis>\d{3})\]\s*"
    r"(?P<from_state>[A-Z_]+)\s*->\s*(?P<to_state>[A-Z_]+)"
    r"(?:\s*\(reason:\s*(?P<reason>[A-Z_]+)\))?"
)


def parse_log_file(filepath):
    """
    Reads the given log file and returns a list of event dicts:
        {
          "time_s": float,       # seconds since simulation start
          "from_state": str,
          "to_state": str,
          "reason": str or None,
          "raw_line": str,
        }

    Lines that do not match the expected format are silently skipped
    (this keeps the parser tolerant of stray terminal noise or blank
    lines that Proteus's Virtual Terminal sometimes captures alongside
    the real log output), but a count of skipped lines is returned so
    the caller can warn the user if that count looks suspiciously high.
    """
    events = []
    skipped = 0
    total_lines = 0

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            total_lines += 1
            line = raw_line.strip()
            if not line:
                continue

            match = LOG_LINE_PATTERN.search(line)
            if not match:
                skipped += 1
                continue

            minutes = int(match.group("minutes"))
            seconds = int(match.group("seconds"))
            millis = int(match.group("millis"))
            time_s = minutes * 60 + seconds + millis / 1000.0

            events.append({
                "time_s": time_s,
                "from_state": match.group("from_state"),
                "to_state": match.group("to_state"),
                "reason": match.group("reason"),
                "raw_line": line,
            })

    return events, skipped, total_lines


def print_summary(events):
    """Prints a short, human-readable summary of the parsed log to the console."""
    if not events:
        print("No valid transition events were found in this log file.")
        return

    start_time = events[0]["time_s"]
    end_time = events[-1]["time_s"]
    total_duration = end_time - start_time

    fault_events = [e for e in events if e["to_state"] == "FAULT"]

    # Time spent in each state, computed as the gap between consecutive
    # transitions (the state is whatever "to_state" was, from that
    # transition's timestamp until the next transition's timestamp).
    time_in_state = {state: 0.0 for state in STATE_ORDER}
    for i, event in enumerate(events):
        state = event["to_state"]
        this_time = event["time_s"]
        next_time = events[i + 1]["time_s"] if i + 1 < len(events) else end_time
        if state in time_in_state:
            time_in_state[state] += max(0.0, next_time - this_time)

    print("=" * 60)
    print("UART LOG SUMMARY")
    print("=" * 60)
    print(f"Total transitions parsed : {len(events)}")
    print(f"Run duration              : {total_duration:.3f} s "
          f"({start_time:.3f}s to {end_time:.3f}s)")
    print(f"Fault events              : {len(fault_events)}")
    for fe in fault_events:
        reason = fe["reason"] if fe["reason"] else "UNKNOWN"
        print(f"    -> at {fe['time_s']:.3f}s, reason: {reason}")
    print("-" * 60)
    print("Time spent in each state:")
    for state in STATE_ORDER:
        print(f"    {state:<10}: {time_in_state[state]:.3f} s")
    print("=" * 60)


def plot_timeline(events, output_path, title):
    """
    Draws a step-style timeline: x-axis is time (seconds), y-axis is
    the system state (categorical, ordered per STATE_ORDER). Fault
    transitions are marked with a red vertical line and annotated with
    their reason, so the plot makes overload/E-stop events immediately
    visible rather than something you have to read out of raw text.
    """
    import matplotlib
    matplotlib.use("Agg")  # no display needed - just save to a file
    import matplotlib.pyplot as plt

    if not events:
        print("Nothing to plot - no valid events were parsed.")
        return

    state_to_y = {state: i for i, state in enumerate(STATE_ORDER)}

    # Build a step function: for each event, the state becomes active
    # starting at that event's timestamp, and stays active until the
    # next event's timestamp.
    times = [e["time_s"] for e in events]
    y_values = [state_to_y.get(e["to_state"], -1) for e in events]

    # Extend the last state's line to the end of the recorded run so
    # the plot doesn't visually cut off mid-state.
    end_time = times[-1] + 1.0

    fig, ax = plt.subplots(figsize=(11, 4.5))

    ax.step(times + [end_time], y_values + [y_values[-1]], where="post",
            linewidth=2, color="#3E5C76")

    # Mark every transition point with a small dot.
    ax.plot(times, y_values, "o", color="#3E5C76", markersize=5, zorder=3)

    # Highlight fault entries specifically.
    for e in events:
        if e["to_state"] == "FAULT":
            ax.axvline(x=e["time_s"], color="#C0392B", linestyle="--",
                       linewidth=1, alpha=0.7)
            reason = e["reason"] if e["reason"] else "UNKNOWN"
            ax.annotate(
                f"FAULT\n({reason})",
                xy=(e["time_s"], state_to_y["FAULT"]),
                xytext=(e["time_s"], state_to_y["FAULT"] + 0.35),
                fontsize=8.5, color="#C0392B", ha="center", fontweight="bold",
            )

    ax.set_yticks(range(len(STATE_ORDER)))
    ax.set_yticklabels(STATE_ORDER)
    ax.set_ylim(-0.5, len(STATE_ORDER) - 0.2)
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("System State")
    ax.set_title(title)
    ax.grid(True, axis="x", linestyle=":", alpha=0.5)
    fig.tight_layout()

    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Timeline plot saved to: {output_path}")


def write_csv(events, output_path):
    """Writes the parsed events to a plain CSV file for spreadsheet use
    or for feeding into your own further analysis."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time_seconds", "from_state", "to_state", "fault_reason"])
        for e in events:
            writer.writerow([f"{e['time_s']:.3f}", e["from_state"],
                              e["to_state"], e["reason"] or ""])
    print(f"Parsed events written to : {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Parse an STM32 UART state-transition log and generate "
                    "a timeline plot + CSV summary."
    )
    parser.add_argument("logfile", help="Path to the captured UART log (.txt)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output PNG path for the timeline plot "
                             "(default: <logfile-name>_timeline.png)")
    parser.add_argument("--csv", default=None,
                        help="Output CSV path for parsed events "
                             "(default: <logfile-name>_events.csv)")
    parser.add_argument("--title", default=None,
                        help="Title for the timeline plot "
                             "(default: derived from the log filename)")
    args = parser.parse_args()

    if not os.path.isfile(args.logfile):
        print(f"Error: file not found: {args.logfile}", file=sys.stderr)
        sys.exit(1)

    base_name = os.path.splitext(os.path.basename(args.logfile))[0]
    output_png = args.output or f"{base_name}_timeline.png"
    output_csv = args.csv or f"{base_name}_events.csv"
    title = args.title or f"State Timeline — {base_name}"

    events, skipped, total_lines = parse_log_file(args.logfile)

    if skipped > 0:
        print(f"Note: {skipped} of {total_lines} lines in the file did not "
              f"match the expected log format and were skipped.")

    print_summary(events)
    write_csv(events, output_csv)
    plot_timeline(events, output_png, title)


if __name__ == "__main__":
    main()

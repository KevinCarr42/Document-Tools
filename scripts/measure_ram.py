import csv
import signal
import sys
import time
from pathlib import Path

import psutil

TARGET_MARKER = "streamlit_app.py"
POLL_INTERVAL = 0.1
TIMELINE_PATH = Path(__file__).with_name("ram_timeline.csv")

running = True


def find_streamlit_process():
    matches = []
    for proc in psutil.process_iter(["pid", "cmdline"]):
        cmdline = proc.info["cmdline"]
        if not cmdline:
            continue
        if any(TARGET_MARKER in part for part in cmdline):
            matches.append(proc)
    if not matches:
        return None
    # uv/streamlit can spawn helper processes; the real server is the hungriest one.
    return max(matches, key=lambda p: p.memory_info().rss)


def stop(signum, frame):
    global running
    running = False


def main():
    proc = find_streamlit_process()
    if proc is None:
        print(f"No running process with '{TARGET_MARKER}' in its command line.")
        print("Start the app first: uv run streamlit run streamlit_app.py")
        sys.exit(1)

    print(f"Monitoring PID {proc.pid}: {' '.join(proc.cmdline())}", flush=True)
    print(f"Polling every {POLL_INTERVAL:.1f}s - press Ctrl+C to stop.\n", flush=True)

    signal.signal(signal.SIGINT, stop)

    timeline = open(TIMELINE_PATH, "w", newline="")
    writer = csv.writer(timeline)
    writer.writerow(["elapsed_seconds", "rss_mb"])

    start = time.monotonic()
    baseline_mb = None
    max_rss = 0

    while running and proc.is_running():
        rss = proc.memory_info().rss
        elapsed = time.monotonic() - start
        rss_mb = rss / 1024 / 1024
        if baseline_mb is None:
            baseline_mb = rss_mb
        if rss > max_rss:
            max_rss = rss
        writer.writerow([f"{elapsed:.2f}", f"{rss_mb:.1f}"])
        timeline.flush()
        time.sleep(POLL_INTERVAL)

    timeline.close()
    print(f"\nTimeline written to {TIMELINE_PATH}")

    if baseline_mb is None:
        print("No samples collected.")
        return

    print(f"Baseline RSS:    {baseline_mb:,.1f} MB")
    print(f"Peak polled RSS: {max_rss / 1024 / 1024:,.1f} MB")

    # peak_wset (Windows-only) is the OS-tracked lifetime peak working set - no sampling gaps.
    if not proc.is_running():
        print("Process exited before peak_wset could be read.")
        return
    info = proc.memory_info()
    if hasattr(info, "peak_wset"):
        print(f"Peak working set: {info.peak_wset / 1024 / 1024:,.1f} MB")


if __name__ == "__main__":
    main()
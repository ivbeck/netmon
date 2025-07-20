import csv
import os
import threading
import time
from datetime import datetime
from pathlib import Path

from config import TARGETS, CSV_LOG_INTERVAL_SECONDS
from monitor import metric_store

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def append_csv_log(target, records):
    log_file = LOG_DIR / f"{target}.csv"
    file_exists = log_file.exists()

    with open(log_file, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["timestamp", "latency_ms"])
        for record in records:
            writer.writerow([record["timestamp"], record["latency"]])


def csv_logging_task():
    last_written = {target: 0 for target in TARGETS}

    while True:
        for target in TARGETS:
            records = list(metric_store.data[target])
            new_records = [r for r in records if iso_to_epoch(r["timestamp"]) > last_written[target]]

            if new_records:
                append_csv_log(target, new_records)
                last_written[target] = iso_to_epoch(new_records[-1]["timestamp"])

        time.sleep(CSV_LOG_INTERVAL_SECONDS)


def iso_to_epoch(ts):
    return int(datetime.fromisoformat(ts).timestamp())


csv_thread = threading.Thread(target=csv_logging_task, daemon=True)
csv_thread.start()

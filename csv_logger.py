import csv
import os
import threading
import time
from datetime import datetime, date, timedelta
from pathlib import Path
import glob
from io import StringIO

from config import TARGETS, CSV_LOG_INTERVAL_SECONDS
from monitor import metric_store
from wifi_detector import get_wifi_network_name, sanitize_network_name

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Cache the current network name to avoid repeated detection
_current_network = None
_network_check_time = None
_network_cache_duration = 300  # 5 minutes


def get_current_network():
    """Get current network name with caching"""
    global _current_network, _network_check_time

    now = time.time()
    if (
        _current_network is None
        or _network_check_time is None
        or now - _network_check_time > _network_cache_duration
    ):

        _current_network = get_wifi_network_name()
        _network_check_time = now
        print(f"Network detected/updated: {_current_network}")

    return _current_network


def get_daily_log_file(target, date_obj=None, network=None):
    """Get the CSV file path for a specific target, date, and network"""
    if date_obj is None:
        date_obj = date.today()
    if network is None:
        network = get_current_network()

    # Create directory structure: logs/network/YYYY/MM/
    network_dir = LOG_DIR / sanitize_network_name(network)
    year_month_dir = network_dir / str(date_obj.year) / f"{date_obj.month:02d}"
    year_month_dir.mkdir(parents=True, exist_ok=True)

    return year_month_dir / f"{target}_{date_obj.strftime('%Y-%m-%d')}.csv"


def get_daily_metrics_file(target, date_obj=None, network=None):
    """Get the metrics CSV file path for a specific target, date, and network"""
    if date_obj is None:
        date_obj = date.today()
    if network is None:
        network = get_current_network()

    # Create directory structure: logs/network/YYYY/MM/
    network_dir = LOG_DIR / sanitize_network_name(network)
    year_month_dir = network_dir / str(date_obj.year) / f"{date_obj.month:02d}"
    year_month_dir.mkdir(parents=True, exist_ok=True)

    return year_month_dir / f"{target}_{date_obj.strftime('%Y-%m-%d')}_metrics.csv"


def append_csv_log(target, records):
    """Log raw ping data organized by day and network"""
    if not records:
        return

    current_network = get_current_network()

    # Group records by date
    records_by_date = {}
    for record in records:
        record_date = datetime.fromisoformat(record["timestamp"]).date()
        if record_date not in records_by_date:
            records_by_date[record_date] = []
        # Add network info to record
        enhanced_record = record.copy()
        enhanced_record["network"] = current_network
        records_by_date[record_date].append(enhanced_record)

    # Write records to appropriate daily files
    for record_date, daily_records in records_by_date.items():
        log_file = get_daily_log_file(target, record_date, current_network)
        file_exists = log_file.exists()

        with open(log_file, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(["timestamp", "latency_ms", "network"])
            for record in daily_records:
                writer.writerow(
                    [record["timestamp"], record["latency"], record["network"]]
                )


def append_metrics_log(target, metrics, timestamp=None):
    """Log aggregated metrics for a target organized by day and network"""
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()

    today = date.today()
    current_network = get_current_network()
    metrics_file = get_daily_metrics_file(target, today, current_network)
    file_exists = metrics_file.exists()

    with open(metrics_file, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(
                [
                    "timestamp",
                    "network",
                    "packet_loss_percent",
                    "average_latency",
                    "min_latency",
                    "max_latency",
                    "jitter",
                    "std_deviation",
                ]
            )
        writer.writerow(
            [
                timestamp,
                current_network,
                metrics["packet_loss_percent"],
                metrics["average_latency"],
                metrics["min_latency"],
                metrics["max_latency"],
                metrics["jitter"],
                metrics["std_deviation"],
            ]
        )


def load_recent_data():
    """Load recent data from CSV files into memory on startup"""
    print("Loading recent data from CSV files...")

    # Scan all network directories
    network_dirs = [d for d in LOG_DIR.iterdir() if d.is_dir()]

    for target in TARGETS:
        total_loaded = 0

        # Load from all networks, but prioritize current network
        current_network = get_current_network()
        networks_to_check = [current_network]

        # Add other networks found in logs
        for network_dir in network_dirs:
            network_name = network_dir.name
            if network_name != current_network:
                networks_to_check.append(network_name)

        # Load data from last 3 days across networks
        for network_name in networks_to_check[
            :3
        ]:  # Limit to 3 networks to avoid memory issues
            for days_back in range(3):
                target_date = date.today() - timedelta(days=days_back)
                log_file = get_daily_log_file(target, target_date, network_name)

                if log_file.exists():
                    try:
                        records = read_csv_as_dict_reader(log_file)

                        # Add records to metric store (but limit to recent ones)
                        for record in records[-200:]:  # Reduced to 200 per network/day
                            latency = (
                                None
                                if record["latency_ms"] == "None"
                                else float(record["latency_ms"])
                            )
                            metric_store.add(target, latency, record["timestamp"])

                        total_loaded += len(records[-200:])
                    except Exception as e:
                        print(f"Error loading data from {log_file}: {e}")

        print(f"Loaded {total_loaded} recent records for {target}")


def get_historical_files(target, days=30, network=None):
    """Get list of historical CSV files for a target within the last N days"""
    if network is None:
        network = get_current_network()

    files = []
    for days_back in range(days):
        target_date = date.today() - timedelta(days=days_back)
        log_file = get_daily_log_file(target, target_date, network)
        if log_file.exists():
            files.append(log_file)
    return files


def get_available_networks():
    """Get list of all networks that have data"""
    networks = set()
    try:
        for network_dir in LOG_DIR.iterdir():
            if network_dir.is_dir():
                networks.add(network_dir.name)
    except Exception as e:
        print(f"Error scanning networks: {e}")

    return sorted(list(networks))


def csv_logging_task():
    last_written = {target: 0 for target in TARGETS}
    last_metrics_logged = 0  # Track when we last logged metrics

    while True:
        current_time = time.time()

        # Log raw data for targets that have new records
        for target in TARGETS:
            records = list(metric_store.data[target])
            new_records = [
                r
                for r in records
                if iso_to_epoch(r["timestamp"]) > last_written[target]
            ]

            if new_records:
                append_csv_log(target, new_records)
                last_written[target] = iso_to_epoch(new_records[-1]["timestamp"])

        # Log metrics for all targets on a fixed schedule (every CSV_LOG_INTERVAL_SECONDS)
        if current_time - last_metrics_logged >= CSV_LOG_INTERVAL_SECONDS:
            # Generate a single timestamp for this metrics logging cycle
            metrics_timestamp = datetime.utcnow().isoformat()
            for target in TARGETS:
                metrics = metric_store.get_metrics(target)
                append_metrics_log(target, metrics, metrics_timestamp)
            last_metrics_logged = current_time

        time.sleep(CSV_LOG_INTERVAL_SECONDS)


def iso_to_epoch(ts):
    return int(datetime.fromisoformat(ts).timestamp())


def read_csv_with_headers(file_path):
    """
    Read CSV file content
    Returns the content as string ready for CSV parsing
    """
    try:
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading CSV file {file_path}: {e}")
        return ""


def read_csv_as_dataframe(file_path):
    """
    Read CSV file into a pandas DataFrame
    """
    import pandas as pd

    try:
        return pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading CSV file {file_path}: {e}")
        return pd.DataFrame()


def read_csv_as_dict_reader(file_path):
    """
    Read CSV file using DictReader
    """
    try:
        with open(file_path, "r") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"Error reading CSV file {file_path}: {e}")
        return []


# Load recent data on startup
load_recent_data()

csv_thread = threading.Thread(target=csv_logging_task, daemon=True)
csv_thread.start()

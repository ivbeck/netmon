#!/usr/bin/env python3
"""
Network Monitor Data Management Script

This script provides utilities for managing the network monitoring data:
- View data organization
- Load historical data
- Clean up old files
- Export data
"""

import sys
from pathlib import Path
from datetime import date, timedelta, datetime
import csv
import argparse
import os

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

from csv_logger import (
    get_daily_log_file,
    get_daily_metrics_file,
    LOG_DIR,
    get_available_networks,
    read_csv_as_dict_reader,
)
from config import TARGETS
from wifi_detector import get_wifi_network_name


def show_data_organization():
    """Display how data is organized on disk"""
    print("Data Organization:")
    print("==================")
    print(f"Base directory: {LOG_DIR}")
    print("Structure: logs/NETWORK_NAME/YYYY/MM/target_YYYY-MM-DD.csv")
    print("          logs/NETWORK_NAME/YYYY/MM/target_YYYY-MM-DD_metrics.csv")
    print()

    current_network = get_wifi_network_name()
    print(f"Current WiFi Network: {current_network}")
    print()

    # Show available networks
    networks = get_available_networks()
    if networks:
        print(f"Networks with data: {', '.join(networks)}")
    else:
        print("No networks with data found")
    print()

    # Show current structure
    total_files = 0
    for root, dirs, files in os.walk(LOG_DIR):
        csv_files = [f for f in files if f.endswith(".csv")]
        if csv_files:
            rel_path = os.path.relpath(root, LOG_DIR)
            print(f"{rel_path}: {len(csv_files)} CSV files")
            total_files += len(csv_files)

    print(f"\nTotal CSV files: {total_files}")


def show_available_data():
    """Show available data for each target across all networks"""
    print("\nAvailable Data by Target and Network:")
    print("=" * 50)

    networks = get_available_networks()
    if not networks:
        print("No networks with data found")
        return

    for target in TARGETS:
        print(f"\n{target}:")
        target_total = 0

        for network in networks:
            print(f"  Network: {network}")
            files_found = 0

            # Check last 30 days for this network
            for days_back in range(30):
                check_date = date.today() - timedelta(days=days_back)
                log_file = get_daily_log_file(target, check_date, network)
                metrics_file = get_daily_metrics_file(target, check_date, network)

                if log_file.exists() or metrics_file.exists():
                    files_found += 1
                    log_size = log_file.stat().st_size if log_file.exists() else 0
                    metrics_size = (
                        metrics_file.stat().st_size if metrics_file.exists() else 0
                    )

                    print(f"    {check_date}: {log_size + metrics_size:,} bytes")

            if files_found == 0:
                print("    No data files found")
            else:
                target_total += files_found

        if target_total == 0:
            print("  No data files found for any network")


def export_target_data(target, start_date, end_date, output_file, network=None):
    """Export data for a target within date range to a single CSV"""
    if target not in TARGETS:
        print(f"Error: {target} not in configured targets: {TARGETS}")
        return

    # If no network specified, use current network
    if network is None:
        network = get_wifi_network_name()
        print(f"Using current network: {network}")

    all_records = []
    current_date = start_date

    while current_date <= end_date:
        log_file = get_daily_log_file(target, current_date, network)

        if log_file.exists():
            try:
                records = read_csv_as_dict_reader(log_file)
                for row in records:
                    row["date"] = current_date.isoformat()
                    all_records.append(row)
            except Exception as e:
                print(f"Error reading {log_file}: {e}")

        current_date += timedelta(days=1)

    if all_records:
        with open(output_file, "w", newline="") as f:
            # Check if we have network field in the data
            sample_record = all_records[0]
            if "network" in sample_record:
                fieldnames = ["date", "timestamp", "latency_ms", "network"]
            else:
                fieldnames = ["date", "timestamp", "latency_ms"]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_records)

        print(f"Exported {len(all_records)} records to {output_file}")
        print(f"Network: {network}")
    else:
        print(f"No data found for the specified date range and network: {network}")


def export_all_networks_data(target, start_date, end_date, output_file):
    """Export data for a target from all networks within date range"""
    if target not in TARGETS:
        print(f"Error: {target} not in configured targets: {TARGETS}")
        return

    networks = get_available_networks()
    all_records = []

    for network in networks:
        current_date = start_date

        while current_date <= end_date:
            log_file = get_daily_log_file(target, current_date, network)

            if log_file.exists():
                try:
                    records = read_csv_as_dict_reader(log_file)
                    for row in records:
                        row["date"] = current_date.isoformat()
                        if "network" not in row:
                            row["network"] = network
                        all_records.append(row)
                except Exception as e:
                    print(f"Error reading {log_file}: {e}")

            current_date += timedelta(days=1)

    if all_records:
        with open(output_file, "w", newline="") as f:
            fieldnames = ["date", "timestamp", "latency_ms", "network"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_records)

        print(
            f"Exported {len(all_records)} records from {len(networks)} networks to {output_file}"
        )
        print(f"Networks: {', '.join(networks)}")
    else:
        print("No data found for the specified date range across all networks")


def cleanup_old_data(days_to_keep=30, network=None):
    """Clean up data older than specified days"""
    if days_to_keep < 7:
        print("Error: Will not delete data newer than 7 days for safety")
        return

    cutoff_date = date.today() - timedelta(days=days_to_keep)
    deleted_files = []

    # If network specified, clean only that network, otherwise clean all
    networks_to_clean = [network] if network else get_available_networks()

    print(f"Cleaning up data older than {cutoff_date}")
    if network:
        print(f"Network: {network}")
    else:
        print(f"All networks: {', '.join(networks_to_clean)}")

    for network_name in networks_to_clean:
        for target in TARGETS:
            # Check files older than cutoff (up to 1 year back)
            for days_back in range(days_to_keep, days_to_keep + 365):
                check_date = date.today() - timedelta(days=days_back)

                if check_date < cutoff_date:
                    log_file = get_daily_log_file(target, check_date, network_name)
                    metrics_file = get_daily_metrics_file(
                        target, check_date, network_name
                    )

                    for file_path in [log_file, metrics_file]:
                        if file_path.exists():
                            try:
                                file_path.unlink()
                                deleted_files.append(str(file_path))
                                print(f"Deleted: {file_path}")
                            except Exception as e:
                                print(f"Error deleting {file_path}: {e}")

    print(f"\nDeleted {len(deleted_files)} files")


def main():
    parser = argparse.ArgumentParser(description="Network Monitor Data Management")
    parser.add_argument(
        "command",
        choices=["show", "list", "export", "export-all", "cleanup", "networks"],
        help="Command to execute",
    )

    # Export arguments
    parser.add_argument("--target", help="Target for export command")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD) for export")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD) for export")
    parser.add_argument("--output", help="Output file for export")
    parser.add_argument("--network", help="Network name for export/cleanup (optional)")

    # Cleanup arguments
    parser.add_argument(
        "--days", type=int, default=30, help="Days to keep for cleanup (default: 30)"
    )

    args = parser.parse_args()

    if args.command == "show":
        show_data_organization()

    elif args.command == "list":
        show_available_data()

    elif args.command == "networks":
        networks = get_available_networks()
        current = get_wifi_network_name()
        print(f"Current WiFi Network: {current}")
        print(
            f"Available Networks with Data: {', '.join(networks) if networks else 'None'}"
        )

    elif args.command == "export":
        if not all([args.target, args.start_date, args.end_date, args.output]):
            print("Export requires: --target, --start-date, --end-date, --output")
            print("Optional: --network (defaults to current network)")
            return

        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
            export_target_data(
                args.target, start_date, end_date, args.output, args.network
            )
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD")

    elif args.command == "export-all":
        if not all([args.target, args.start_date, args.end_date, args.output]):
            print("Export-all requires: --target, --start-date, --end-date, --output")
            return

        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
            export_all_networks_data(args.target, start_date, end_date, args.output)
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD")

    elif args.command == "cleanup":
        cleanup_old_data(args.days, args.network)


if __name__ == "__main__":
    main()

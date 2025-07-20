from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from monitor import metric_store
from config import TARGETS
import csv
import io


import csv_logger  # start CSV logging thread


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "targets": TARGETS}
    )


@app.get("/api/metrics/{target}")
async def get_metrics(target: str):
    if target not in metric_store.data:
        return {"error": "Invalid target"}
    return metric_store.get_metrics(target)


@app.get("/api/metrics/{target}/csv")
async def export_csv(target: str):
    if target not in metric_store.data:
        return Response(
            content="Invalid target", media_type="text/plain", status_code=400
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "latency_ms"])

    for record in metric_store.data[target]:
        writer.writerow([record["timestamp"], record["latency"]])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={target}.csv"},
    )


@app.get("/api/metrics/{target}/history")
async def get_metrics_history(target: str, days: int = 7, network: str = None):
    """Get historical metrics from daily CSV files"""
    from datetime import date, timedelta
    import pandas as pd
    from csv_logger import (
        get_daily_log_file,
        get_daily_metrics_file,
        get_current_network,
        read_csv_as_dataframe,
    )

    if target not in TARGETS:
        return {"error": "Invalid target"}

    # Use current network if none specified
    if network is None:
        network = get_current_network()

    historical_data = []

    # Load data from the last N days
    for days_back in range(days):
        target_date = date.today() - timedelta(days=days_back)

        # Load raw ping data
        log_file = get_daily_log_file(target, target_date, network)
        if log_file.exists():
            try:
                df = read_csv_as_dataframe(log_file)
                day_data = {
                    "date": target_date.isoformat(),
                    "network": network,
                    "raw_data": df.tail(100).to_dict(
                        "records"
                    ),  # Last 100 entries per day
                }

                # Load metrics data if available
                metrics_file = get_daily_metrics_file(target, target_date, network)
                if metrics_file.exists():
                    metrics_df = read_csv_as_dataframe(metrics_file)
                    day_data["metrics"] = metrics_df.tail(50).to_dict(
                        "records"
                    )  # Last 50 metric entries

                historical_data.append(day_data)

            except Exception as e:
                print(f"Error loading data from {log_file}: {e}")

    return {
        "target": target,
        "network": network,
        "days_requested": days,
        "historical_data": historical_data,
    }


@app.get("/api/metrics/{target}/summary")
async def get_daily_summary(target: str, days: int = 30, network: str = None):
    """Get daily summary statistics"""
    from datetime import date, timedelta
    import pandas as pd
    from csv_logger import (
        get_daily_metrics_file,
        get_current_network,
        read_csv_as_dataframe,
    )

    if target not in TARGETS:
        return {"error": "Invalid target"}

    # Use current network if none specified
    if network is None:
        network = get_current_network()

    summaries = []

    for days_back in range(days):
        target_date = date.today() - timedelta(days=days_back)
        metrics_file = get_daily_metrics_file(target, target_date, network)

        if metrics_file.exists():
            try:
                df = read_csv_as_dataframe(metrics_file)
                if not df.empty:
                    summary = {
                        "date": target_date.isoformat(),
                        "network": network,
                        "avg_latency": df["average_latency"].mean(),
                        "avg_jitter": df["jitter"].mean(),
                        "avg_packet_loss": df["packet_loss_percent"].mean(),
                        "max_latency": df["max_latency"].max(),
                        "min_latency": df["min_latency"].min(),
                        "records_count": len(df),
                    }
                    summaries.append(summary)
            except Exception as e:
                print(f"Error processing {metrics_file}: {e}")

    return {"target": target, "network": network, "daily_summaries": summaries}


@app.get("/api/logs/dates")
async def get_available_dates():
    """Get list of dates with available log data"""
    from csv_logger import LOG_DIR
    import os

    dates_with_data = set()

    # Scan the logs directory structure
    for root, dirs, files in os.walk(LOG_DIR):
        for file in files:
            if file.endswith(".csv") and "_" in file:
                # Extract date from filename like "target_2025-07-20.csv"
                try:
                    date_part = file.split("_")[1].split(".")[0]
                    if len(date_part) == 10:  # YYYY-MM-DD format
                        dates_with_data.add(date_part)
                except:
                    continue

    return {"available_dates": sorted(list(dates_with_data), reverse=True)}


@app.get("/api/logs/cleanup")
async def cleanup_old_logs(days_to_keep: int = 30):
    """Clean up log files older than specified days"""
    from datetime import date, timedelta
    from csv_logger import get_daily_log_file, get_daily_metrics_file
    import os

    if days_to_keep < 7:
        return {"error": "Cannot keep less than 7 days of logs for safety"}

    deleted_files = []
    cutoff_date = date.today() - timedelta(days=days_to_keep)

    for target in TARGETS:
        # Check files older than cutoff
        for days_back in range(
            days_to_keep, days_to_keep + 365
        ):  # Check up to a year back
            check_date = date.today() - timedelta(days=days_back)

            if check_date < cutoff_date:
                log_file = get_daily_log_file(target, check_date)
                metrics_file = get_daily_metrics_file(target, check_date)

                for file_path in [log_file, metrics_file]:
                    if file_path.exists():
                        try:
                            os.remove(file_path)
                            deleted_files.append(str(file_path))
                        except Exception as e:
                            print(f"Error deleting {file_path}: {e}")

    return {"deleted_files": deleted_files, "cutoff_date": cutoff_date.isoformat()}


@app.get("/api/networks")
async def get_networks():
    """Get available networks and current network info"""
    from csv_logger import get_available_networks, get_current_network

    return {
        "current_network": get_current_network(),
        "available_networks": get_available_networks(),
    }


@app.get("/api/metrics/{target}/compare-networks")
async def compare_networks(target: str, days: int = 7):
    """Compare metrics across different networks for a target"""
    from datetime import date, timedelta
    import pandas as pd
    from csv_logger import (
        get_daily_metrics_file,
        get_available_networks,
        read_csv_as_dataframe,
    )

    if target not in TARGETS:
        return {"error": "Invalid target"}

    networks = get_available_networks()
    network_comparison = {}

    for network in networks:
        network_data = []

        for days_back in range(days):
            target_date = date.today() - timedelta(days=days_back)
            metrics_file = get_daily_metrics_file(target, target_date, network)

            if metrics_file.exists():
                try:
                    df = read_csv_as_dataframe(metrics_file)
                    if not df.empty:
                        avg_metrics = {
                            "date": target_date.isoformat(),
                            "avg_latency": df["average_latency"].mean(),
                            "avg_jitter": df["jitter"].mean(),
                            "avg_packet_loss": df["packet_loss_percent"].mean(),
                        }
                        network_data.append(avg_metrics)
                except Exception as e:
                    print(f"Error processing {metrics_file}: {e}")

        if network_data:
            # Calculate overall averages for this network
            all_latencies = [
                d["avg_latency"] for d in network_data if d["avg_latency"] is not None
            ]
            all_jitters = [
                d["avg_jitter"] for d in network_data if d["avg_jitter"] is not None
            ]
            all_losses = [
                d["avg_packet_loss"]
                for d in network_data
                if d["avg_packet_loss"] is not None
            ]

            network_comparison[network] = {
                "daily_data": network_data,
                "overall_avg_latency": (
                    sum(all_latencies) / len(all_latencies) if all_latencies else None
                ),
                "overall_avg_jitter": (
                    sum(all_jitters) / len(all_jitters) if all_jitters else None
                ),
                "overall_avg_packet_loss": (
                    sum(all_losses) / len(all_losses) if all_losses else None
                ),
                "data_points": len(network_data),
            }

    return {
        "target": target,
        "days_analyzed": days,
        "network_comparison": network_comparison,
    }

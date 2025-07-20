import subprocess
import threading
import time
from collections import deque
from datetime import datetime

from config import TARGETS, RETENTION_SECONDS, PING_INTERVAL


class MetricStore:
    def __init__(self, retention_seconds):
        self.retention = retention_seconds
        self.data = {target: deque(maxlen=retention_seconds) for target in TARGETS}

    def add(self, target, latency_ms):
        self.data[target].append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "latency": latency_ms,
            }
        )

    def get_metrics(self, target):
        records = list(self.data[target])
        if not records:
            return {
                "packet_loss_percent": 100.0,
                "average_latency": None,
                "jitter": None,
                "records": [],
            }

        valid_latencies = [r["latency"] for r in records if r["latency"] is not None]
        packet_loss = 100 * (len(records) - len(valid_latencies)) / len(records)
        avg_latency = (
            sum(valid_latencies) / len(valid_latencies) if valid_latencies else None
        )
        jitter = (
            sum(
                abs(valid_latencies[i] - valid_latencies[i - 1])
                for i in range(1, len(valid_latencies))
            )
            / (len(valid_latencies) - 1)
            if len(valid_latencies) > 1
            else 0.0
        )

        return {
            "packet_loss_percent": round(packet_loss, 2),
            "average_latency": (
                round(avg_latency, 2) if avg_latency is not None else None
            ),
            "jitter": round(jitter, 2) if avg_latency is not None else None,
            "records": records,
        }


def ping_once(target):
    try:
        output = subprocess.run(
            ["ping", "-c", "1", "-W", "2", target], capture_output=True, text=True
        )
        if output.returncode == 0:
            for line in output.stdout.splitlines():
                if "time=" in line:
                    latency = float(line.split("time=")[-1].split(" ")[0])
                    return latency
        return None
    except Exception:
        return None


def monitor(store):
    while True:
        for target in TARGETS:
            latency = ping_once(target)
            store.add(target, latency)
        time.sleep(PING_INTERVAL)


metric_store = MetricStore(RETENTION_SECONDS)
monitor_thread = threading.Thread(target=monitor, args=(metric_store,), daemon=True)
monitor_thread.start()

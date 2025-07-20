from datetime import timedelta

RETENTION_SECONDS = int(timedelta(days=1).total_seconds())  # 1 day retention
TARGETS = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
PING_INTERVAL = 1  # seconds
CSV_LOG_INTERVAL_SECONDS = 300  # every 5 minutes

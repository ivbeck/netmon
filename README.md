# Network Monitor

A comprehensive network monitoring dashboard that tracks latency, jitter, packet loss, and other quality metrics for multiple targets.

## Features

- **Real-time Monitoring**: Live dashboard with 5-second updates
- **Quality Metrics**: Tracks latency, jitter, packet loss, min/max, standard deviation
- **Historical Data**: Organized daily CSV storage with automatic loading on restart
- **Dual-axis Charts**: Visualize latency and jitter simultaneously
- **Status Indicators**: Color-coded connection status (Online/Poor/Offline)
- **Data Management**: Built-in tools for data export and cleanup

## Installation

```bash
pip install -r requirements.txt
```

## Running the Application

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open: http://localhost:8000

## Data Organization

Data is automatically organized by WiFi network, date and target:

```
logs/
├── MyHomeWiFi/
│   └── 2025/
│       └── 07/
│           ├── google.de_2025-07-20.csv
│           ├── google.de_2025-07-20_metrics.csv
│           ├── 1.1.1.1_2025-07-20.csv
│           └── 1.1.1.1_2025-07-20_metrics.csv
├── OfficeWiFi/
│   └── 2025/
│       └── 07/
│           ├── google.de_2025-07-20.csv
│           └── google.de_2025-07-20_metrics.csv
└── unknown/
    └── 2025/
        └── 07/
            └── 1.1.1.1_2025-07-20.csv
```

## WiFi Network Detection

The system automatically detects your current WiFi network and organizes data accordingly:

- **Linux**: Uses `nmcli`, `iwgetid`, or `iwconfig`
- **macOS**: Uses `airport` or `networksetup`
- **Windows**: Uses `netsh`
- **Fallback**: Uses 'unknown' if detection fails

## Data Management

Use the included management script with network-aware commands:

```bash
# Show data organization and current network
python manage_data.py show

# List available networks with data
python manage_data.py networks

# List available data by target and network
python manage_data.py list

# Export data for current network
python manage_data.py export --target google.de --start-date 2025-07-15 --end-date 2025-07-20 --output export.csv

# Export data for specific network
python manage_data.py export --target google.de --start-date 2025-07-15 --end-date 2025-07-20 --output export.csv --network MyHomeWiFi

# Export data from all networks
python manage_data.py export-all --target google.de --start-date 2025-07-15 --end-date 2025-07-20 --output export.csv

# Clean up old data for current network
python manage_data.py cleanup --days 30

# Clean up old data for specific network
python manage_data.py cleanup --days 30 --network MyHomeWiFi
```

## API Endpoints

- `GET /` - Dashboard
- `GET /api/metrics/{target}` - Current metrics for target
- `GET /api/metrics/{target}/history?days=7&network=MyWiFi` - Historical data
- `GET /api/metrics/{target}/summary?days=30&network=MyWiFi` - Daily summaries
- `GET /api/metrics/{target}/compare-networks?days=7` - Compare across networks
- `GET /api/metrics/{target}/csv` - Export current data as CSV
- `GET /api/networks` - List available networks and current network
- `GET /api/logs/dates` - List available dates
- `GET /api/logs/cleanup?days_to_keep=30` - Clean up old logs

## Configuration

Edit `config.py` to modify:

- Target hosts to monitor
- Ping interval
- Data retention settings
- CSV logging frequency

## Automatic Data Loading

On startup, the system automatically loads the last 3 days of data into memory, providing continuity across restarts while managing memory usage.

## CSV File Format

The system generates clean CSV files with standard headers:

**Raw ping data files** (`target_YYYY-MM-DD.csv`):

```csv
timestamp,latency_ms,network
2025-07-20T09:00:00.123456,5.16,MyHomeWiFi
2025-07-20T09:00:01.234567,6.23,MyHomeWiFi
```

**Metrics files** (`target_YYYY-MM-DD_metrics.csv`):

```csv
timestamp,network,packet_loss_percent,average_latency,min_latency,max_latency,jitter,std_deviation
2025-07-20T09:05:00.123456,MyHomeWiFi,0.0,6.2,5.16,7.26,1.59,0.86
```

import json
import csv
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
import os


# === CONFIGURATION ===
FORECAST_LAT = 59.3293  # Stockholm latitude
FORECAST_LON = 18.0686  # Stockholm longitude

# Forecast parameters to track
FORECAST_PARAMS = {
    "t": "temperature",
    "ws": "wind_speed",
    "r": "relative_humidity",
    "tcc_mean": "total_cloud_cover",
    "lcc_mean": "low_cloud_cover",
    "mcc_mean": "medium_cloud_cover",
    "hcc_mean": "high_cloud_cover",
    "gust": "wind_gust",
    "msl": "pressure_msl",
    "vis": "visibility"
}

# Archive file
ARCHIVE_CSV = "smhi_forecast_archive.csv"
HOURS_TO_TRACK = 48  # Next 2 days
# ====================


def fetch_smhi_forecast(latitude: float, longitude: float) -> dict:
    """
    Fetch current weather forecast from SMHI API.
    """
    base_url = "https://opendata-download-metfcst.smhi.se/api"
    url = f"{base_url}/category/pmp3g/version/2/geotype/point/lon/{longitude}/lat/{latitude}/data.json"

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
        return data
    except Exception as e:
        print(f"Error fetching forecast: {e}")
        return None


def parse_forecast_snapshot(forecast_data: dict, param_mapping: dict, hours_ahead: int) -> list:
    """
    Parse forecast and extract only the next X hours.
    Returns list of dicts with forecast_time, valid_time, and parameters.
    """
    if not forecast_data or "timeSeries" not in forecast_data:
        return []

    # Get the time this forecast was made
    forecast_issued_time = forecast_data.get("approvedTime", forecast_data.get("referenceTime", ""))
    forecast_issued_dt = datetime.strptime(forecast_issued_time, "%Y-%m-%dT%H:%M:%SZ")

    # Calculate cutoff time (only save forecasts for next X hours)
    cutoff_time = forecast_issued_dt + timedelta(hours=hours_ahead)

    parsed_data = []

    for entry in forecast_data["timeSeries"]:
        valid_time_str = entry["validTime"]
        valid_time_dt = datetime.strptime(valid_time_str, "%Y-%m-%dT%H:%M:%SZ")

        # Only include forecasts within the next X hours
        if valid_time_dt > cutoff_time:
            break

        # Format times
        forecast_time = forecast_issued_dt.strftime("%Y-%m-%d %H:%M:%S")
        valid_time = valid_time_dt.strftime("%Y-%m-%d %H:%M:%S")

        row = {
            "forecast_time": forecast_time,  # When the prediction was made
            "valid_time": valid_time,        # What time the prediction is for
        }

        # Extract parameters
        for param in entry.get("parameters", []):
            param_name = param["name"]
            if param_name in param_mapping:
                friendly_name = param_mapping[param_name]
                values = param.get("values", [])
                if values:
                    row[friendly_name] = values[0]

        parsed_data.append(row)

    return parsed_data


def append_to_archive(new_data: list, archive_file: str, param_mapping: dict):
    """
    Append new forecast snapshot to the archive CSV file.
    Creates file with headers if it doesn't exist.
    """
    if not new_data:
        print("No data to archive")
        return

    # Determine if file exists and needs headers
    file_exists = os.path.exists(archive_file)

    # Define column order
    fieldnames = ["forecast_time", "valid_time"] + list(param_mapping.values())

    # Append to CSV
    with open(archive_file, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write header only if file is new
        if not file_exists:
            writer.writeheader()

        # Write all rows
        for row in new_data:
            writer.writerow(row)

    print(f"Appended {len(new_data)} forecast entries to {archive_file}")


def get_archive_stats(archive_file: str):
    """
    Print statistics about the archive file.
    """
    if not os.path.exists(archive_file):
        print(f"Archive file does not exist yet: {archive_file}")
        return

    with open(archive_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("Archive file is empty")
        return

    # Get unique forecast times
    forecast_times = set(row["forecast_time"] for row in rows)

    print(f"\nArchive Statistics:")
    print(f"  Total entries: {len(rows)}")
    print(f"  Unique forecast snapshots: {len(forecast_times)}")
    print(f"  First forecast: {min(forecast_times)}")
    print(f"  Latest forecast: {max(forecast_times)}")


if __name__ == "__main__":
    print("=" * 60)
    print("=== SMHI Forecast Archive Builder ===")
    print("=" * 60)
    print(f"\nLocation: lat={FORECAST_LAT}, lon={FORECAST_LON}")
    print(f"Tracking: Next {HOURS_TO_TRACK} hours")
    print(f"Archive file: {ARCHIVE_CSV}")
    print("-" * 60)

    # Fetch current forecast
    print(f"\nFetching current forecast...")
    forecast_data = fetch_smhi_forecast(FORECAST_LAT, FORECAST_LON)

    if not forecast_data:
        print("Failed to fetch forecast. Exiting.")
        exit(1)

    # Parse and filter to next 48 hours
    print(f"Parsing forecast (next {HOURS_TO_TRACK} hours only)...")
    snapshot_data = parse_forecast_snapshot(forecast_data, FORECAST_PARAMS, HOURS_TO_TRACK)

    if snapshot_data:
        print(f"Captured {len(snapshot_data)} hourly forecasts")
        print(f"  Forecast issued at: {snapshot_data[0]['forecast_time']}")
        print(f"  Valid from: {snapshot_data[0]['valid_time']}")
        print(f"  Valid to: {snapshot_data[-1]['valid_time']}")
    else:
        print("No forecast data captured")
        exit(1)

    # Append to archive
    print(f"\nAppending to archive...")
    append_to_archive(snapshot_data, ARCHIVE_CSV, FORECAST_PARAMS)

    # Show archive stats
    get_archive_stats(ARCHIVE_CSV)

    print("\n" + "=" * 60)
    print("✓ COMPLETE!")
    print(f"\nTo build a historical archive, run this script regularly:")
    print(f"  • Every hour (recommended)")
    print(f"  • Or every 6 hours (when SMHI updates)")
    print(f"\nOn macOS/Linux, use cron:")
    print(f"  0 * * * * cd {os.getcwd()} && python3 SMHI_forecast_archive.py")
    print("=" * 60)

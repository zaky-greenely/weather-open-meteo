import json
import csv
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path


# === CONFIGURATION: Change these parameters as needed ===

# === OBSERVATIONS (Historical/Real-time Data) ===
STATION_ID = 98230  # Stockholm-Observatoriekullen A

# SMHI parameter codes:
# 1 = Air temperature (°C)
# 4 = Wind speed (m/s)
# 6 = Relative humidity (%)
# 15 = Global irradiance (W/m²)
# 21 = Sunshine time (min)
PARAMETERS = {
    1: "temperature",
    4: "wind_speed",
    6: "relative_humidity",
    15: "global_irradiance",
    21: "sunshine_duration"
}

START_DATE = "2025-12-01"  # Format: YYYY-MM-DD
END_DATE = "2026-02-01"    # Format: YYYY-MM-DD

# Period options: "latest-hour", "latest-day", "latest-months", "corrected-archive"
# Use "latest-months" for recent data (last 4 months, includes current year)
# Use "corrected-archive" for quality-controlled historical data (excludes recent 3 months)
PERIOD = "latest-months"

# === FORECAST (Predictions) ===
FORECAST_LAT = 59.3293  # Stockholm latitude
FORECAST_LON = 18.0686  # Stockholm longitude

# Forecast parameters to extract (SMHI parameter names)
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
# =========================================================


def fetch_smhi_parameter_csv(
    station_id: int,
    parameter: int,
    period: str = "corrected-archive"
) -> list:
    """
    Fetch CSV data for a single parameter from SMHI API.
    Returns list of dicts with timestamp and value.
    """
    base_url = "https://opendata-download-metobs.smhi.se/api"
    url = f"{base_url}/version/1.0/parameter/{parameter}/station/{station_id}/period/{period}/data.csv"

    print(f"Fetching parameter {parameter} from station {station_id}...")

    try:
        with urllib.request.urlopen(url) as response:
            csv_content = response.read().decode('utf-8-sig')  # Handle BOM

        # Find the data section (starts after metadata headers)
        lines = csv_content.strip().split('\n')

        # Find the line with "Datum;Tid (UTC)" which marks the data header
        data_start_idx = None
        for i, line in enumerate(lines):
            if line.startswith('Datum;Tid (UTC)') or line.startswith('Datum;Tid;'):
                data_start_idx = i
                break

        if data_start_idx is None:
            print(f"  Could not find data header in CSV")
            return []

        # Parse only the data rows
        data_lines = lines[data_start_idx:]
        csv_reader = csv.DictReader(data_lines, delimiter=';')
        data = []

        for row in csv_reader:
            # SMHI CSV format: Datum;Tid (UTC);[Parameter Name];Kvalitet;...
            date_str = row.get('Datum', '').strip()
            time_str = row.get('Tid (UTC)', row.get('Tid', '')).strip()

            if date_str and time_str:
                timestamp_str = f"{date_str} {time_str}"
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

                    # Get value column (third column, parameter-specific name)
                    value = None
                    for key in row.keys():
                        if key not in ['Datum', 'Tid (UTC)', 'Tid', 'Kvalitet', 'Quality', '']:
                            value_str = row[key].strip()
                            if value_str:
                                value = value_str
                            break

                    if value:
                        data.append({
                            "timestamp": timestamp,
                            "value": float(value)
                        })
                except (ValueError, KeyError) as e:
                    continue

        return data

    except Exception as e:
        print(f"Error fetching parameter {parameter}: {e}")
        return []


def filter_by_date_range(data: list, start_date: str, end_date: str) -> list:
    """
    Filter data by date range.
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")

    filtered = []
    for entry in data:
        if start_dt <= entry["timestamp"] <= end_dt:
            # Format timestamp for output
            entry["timestamp"] = entry["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            filtered.append(entry)

    return filtered


def fetch_all_smhi_data(
    station_id: int,
    parameters: dict,
    start_date: str,
    end_date: str,
    period: str,
    output_json_path: str
) -> dict:
    """
    Fetch all parameters and combine into single dataset.
    """
    combined_data = {}

    for param_id, param_name in parameters.items():
        print(f"\nFetching {param_name} (parameter {param_id})...")

        data = fetch_smhi_parameter_csv(station_id, param_id, period)

        if data:
            # Filter by date range
            filtered_values = filter_by_date_range(data, start_date, end_date)

            # Store with parameter name
            combined_data[param_name] = {
                "parameter_id": param_id,
                "values": filtered_values
            }

            print(f"  Retrieved {len(filtered_values)} values")
        else:
            print(f"  No data available for this parameter")

    # Save combined data
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=2)

    print(f"\nCombined data saved to {output_json_path}")
    return combined_data


def smhi_json_to_csv(
    input_json_path: str,
    output_csv_path: str
) -> None:
    """
    Convert SMHI JSON data to flat CSV format.
    """
    # Load JSON
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        print("No data to write to CSV")
        return

    # Collect all unique timestamps
    all_timestamps = set()
    for param_name, param_data in data.items():
        for entry in param_data.get("values", []):
            all_timestamps.add(entry["timestamp"])

    # Sort timestamps
    sorted_timestamps = sorted(list(all_timestamps))

    # Create a dictionary for each timestamp with all parameters
    rows = {}
    for ts in sorted_timestamps:
        rows[ts] = {"timestamp": ts}

    # Fill in parameter values
    for param_name, param_data in data.items():
        for entry in param_data.get("values", []):
            ts = entry["timestamp"]
            rows[ts][param_name] = entry["value"]

    # Write CSV
    if rows:
        # Column order: timestamp first, then parameters
        fieldnames = ["timestamp"] + list(data.keys())

        with open(output_csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for ts in sorted_timestamps:
                writer.writerow(rows[ts])

        print(f"CSV with {len(sorted_timestamps)} rows written to {output_csv_path}")
    else:
        print("No data to write to CSV")


# === FORECAST FUNCTIONS ===

def fetch_smhi_forecast(
    latitude: float,
    longitude: float,
    output_json_path: str
) -> dict:
    """
    Fetch weather forecast from SMHI API.
    Provides predictions for the next ~10 days.
    """
    base_url = "https://opendata-download-metfcst.smhi.se/api"
    url = f"{base_url}/category/pmp3g/version/2/geotype/point/lon/{longitude}/lat/{latitude}/data.json"

    print(f"\nFetching forecast for lat={latitude}, lon={longitude}...")

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())

        # Save raw forecast data
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"Forecast data saved to {output_json_path}")
        return data

    except Exception as e:
        print(f"Error fetching forecast: {e}")
        return None


def parse_smhi_forecast(
    forecast_data: dict,
    param_mapping: dict
) -> list:
    """
    Parse SMHI forecast JSON into flat structure.
    Returns list of dicts with timestamp and all parameters.
    """
    if not forecast_data or "timeSeries" not in forecast_data:
        return []

    parsed_data = []

    for entry in forecast_data["timeSeries"]:
        valid_time = entry["validTime"]
        # Convert to local time format
        dt = datetime.strptime(valid_time, "%Y-%m-%dT%H:%M:%SZ")
        timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")

        row = {"timestamp": timestamp}

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


def smhi_forecast_to_csv(
    input_json_path: str,
    output_csv_path: str,
    param_mapping: dict
) -> None:
    """
    Convert SMHI forecast JSON to CSV.
    """
    # Load JSON
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Parse forecast data
    parsed_data = parse_smhi_forecast(data, param_mapping)

    if not parsed_data:
        print("No forecast data to write to CSV")
        return

    # Get all column names
    all_columns = set()
    for row in parsed_data:
        all_columns.update(row.keys())

    # Ensure timestamp is first
    fieldnames = ["timestamp"] + sorted([c for c in all_columns if c != "timestamp"])

    # Write CSV
    with open(output_csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in parsed_data:
            writer.writerow(row)

    print(f"Forecast CSV with {len(parsed_data)} rows written to {output_csv_path}")


if __name__ == "__main__":
    # File names
    obs_json_file = "smhi_data.json"
    obs_csv_file = "smhi_weather.csv"
    forecast_json_file = "smhi_forecast_data.json"
    forecast_csv_file = "smhi_forecast.csv"

    print("=" * 50)
    print("=== SMHI Weather Data Parser ===")
    print("=" * 50)

    # === PART 1: OBSERVATIONS (Historical/Real-time) ===
    print(f"\n[1/2] FETCHING OBSERVATIONS")
    print(f"Station: {STATION_ID} (Stockholm-Observatoriekullen A)")
    print(f"Date range: {START_DATE} to {END_DATE}")
    print(f"Parameters: {list(PARAMETERS.values())}")
    print("-" * 50)

    # Fetch observations from SMHI API
    combined_data = fetch_all_smhi_data(
        station_id=STATION_ID,
        parameters=PARAMETERS,
        start_date=START_DATE,
        end_date=END_DATE,
        period=PERIOD,
        output_json_path=obs_json_file
    )

    # Convert observations to CSV
    print(f"\nConverting observations to CSV...")
    smhi_json_to_csv(obs_json_file, obs_csv_file)

    # === PART 2: FORECAST (Predictions) ===
    print(f"\n[2/2] FETCHING FORECAST")
    print(f"Location: lat={FORECAST_LAT}, lon={FORECAST_LON}")
    print(f"Forecast parameters: {list(FORECAST_PARAMS.values())}")
    print("-" * 50)

    # Fetch forecast
    forecast_data = fetch_smhi_forecast(
        latitude=FORECAST_LAT,
        longitude=FORECAST_LON,
        output_json_path=forecast_json_file
    )

    # Convert forecast to CSV
    if forecast_data:
        print(f"\nConverting forecast to CSV...")
        smhi_forecast_to_csv(forecast_json_file, forecast_csv_file, FORECAST_PARAMS)
    else:
        print(f"Skipping forecast CSV (no data)")

    # Summary
    print("\n" + "=" * 50)
    print("✓ COMPLETE!")
    print(f"  Observations: {obs_csv_file}")
    print(f"  Forecast: {forecast_csv_file}")
    print("=" * 50)

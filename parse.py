import json
import csv
import urllib.request
import urllib.parse
from pathlib import Path


# === CONFIGURATION: Change these parameters as needed ===
LATITUDE = 59.3293
LONGITUDE = 18.0686
START_DATE = "2026-01-03"
END_DATE = "2026-01-06"
HOURLY_VARIABLES = [
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "direct_normal_irradiance",
    "global_tilted_irradiance",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_speed_80m",
    "dew_point_2m",
    "surface_pressure"
]
TIMEZONE = "Europe/Stockholm"
# =========================================================


def fetch_open_meteo_data(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    hourly_variables: list,
    timezone: str,
    output_path: str
) -> None:
    """
    Fetch weather data from Open-Meteo Archive API and save to JSON file.
    """
    base_url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(hourly_variables),
        "timezone": timezone
    }

    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    print(f"Fetching data from Open-Meteo API...")
    print(f"URL: {url}")

    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Data saved to {output_path}")


def open_meteo_json_to_csv(
    input_json_path: str,
    output_csv_path: str
) -> None:
    """
    Parse Open-Meteo hourly JSON and write a flat CSV.
    """
    # Load JSON
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    hourly = data["hourly"]

    # All columns (time + weather variables)
    columns = list(hourly.keys())

    # Number of rows = length of time array
    n_rows = len(hourly["time"])

    # Write CSV
    with open(output_csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns)
        writer.writeheader()

        for i in range(n_rows):
            row = {col: hourly[col][i] for col in columns}
            writer.writerow(row)


if __name__ == "__main__":
    json_file = "open_meteo_sample.json"
    output_csv = "open_meteo_hourly.csv"

    # Fetch data from API
    fetch_open_meteo_data(
        latitude=LATITUDE,
        longitude=LONGITUDE,
        start_date=START_DATE,
        end_date=END_DATE,
        hourly_variables=HOURLY_VARIABLES,
        timezone=TIMEZONE,
        output_path=json_file
    )

    # Parse JSON to CSV
    print(f"\nParsing {json_file}...")
    open_meteo_json_to_csv(json_file, output_csv)

    print(f"CSV written to {output_csv}")

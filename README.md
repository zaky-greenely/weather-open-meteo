# Weather Data Collection Scripts

Python scripts for collecting weather data from Open-Meteo and SMHI APIs.

## Scripts

### 1. `parse.py` - Open-Meteo Historical Data
Fetches historical weather data from Open-Meteo API.

**Usage:**
```bash
python3 parse.py
```

**Output:** `open_meteo_hourly.csv`

### 2. `SMHI_parse.py` - SMHI Observations & Forecasts
Fetches both historical observations and current forecasts from SMHI.

**Usage:**
```bash
python3 SMHI_parse.py
```

**Outputs:**
- `smhi_weather.csv` - Historical/real-time observations
- `smhi_forecast.csv` - Current forecast (next 10 days)

### 3. `SMHI_forecast_archive.py` - Build Forecast History
Archives forecast snapshots to track prediction accuracy over time.

**Usage:**
```bash
python3 SMHI_forecast_archive.py
```

**Output:** `smhi_forecast_archive.csv` - Growing archive of forecast snapshots

## Automated Collection with GitHub Actions

This repository includes a GitHub Actions workflow that automatically runs `SMHI_forecast_archive.py` every 6 hours, building a historical record of weather forecasts.

### How It Works
- Runs automatically every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
- Fetches current SMHI forecast
- Saves the next 48 hours of predictions
- Commits the updated archive back to the repository
- Completely free (no laptop needed!)

### Manual Trigger
You can also trigger the workflow manually from the GitHub Actions tab.

## Configuration

All scripts have configuration sections at the top where you can customize:
- Location (latitude/longitude or station ID)
- Date ranges
- Parameters to fetch
- Output file names

## Requirements

Python 3.x with standard library (no external dependencies needed!)

## Data Sources

- **Open-Meteo**: https://open-meteo.com
- **SMHI**: https://opendata.smhi.se

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .models import SiteConfig

SMET_NODATA = -777


def _normalize_timestamps(weather_df: pd.DataFrame) -> pd.Series:
    timestamps = pd.to_datetime(weather_df["timestamp"])
    if getattr(timestamps.dt, "tz", None) is not None:
        timestamps = timestamps.dt.tz_convert("UTC").dt.tz_localize(None)
    return timestamps


def create_smet_from_weather_data(
    *,
    weather_df: pd.DataFrame,
    output_path: str | Path,
    site: SiteConfig,
) -> Path:
    if "timestamp" not in weather_df.columns:
        raise ValueError("weather_df must include a 'timestamp' column")

    prepared = weather_df.copy()
    prepared["timestamp"] = _normalize_timestamps(prepared)
    if "TSG" not in prepared.columns:
        prepared["TSG"] = 273.15
    if "HS" not in prepared.columns:
        prepared["HS"] = SMET_NODATA

    fields = ["timestamp", "TA", "RH", "TSG", "VW", "DW", "ISWR"]
    if "ILWR" in prepared.columns:
        fields.append("ILWR")
    fields.append("PSUM")
    fields.append("HS")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        handle.write("SMET 1.1 ASCII\n")
        handle.write("[HEADER]\n")
        handle.write(f"station_id = {site.station_id}\n")
        handle.write(f"station_name = {site.station_name}\n")
        handle.write(f"latitude = {site.latitude:.10f}\n")
        handle.write(f"longitude = {site.longitude:.10f}\n")
        handle.write(f"altitude = {site.altitude_meters}\n")
        handle.write(f"nodata = {SMET_NODATA}\n")
        handle.write(f"tz = {site.timezone}\n")
        handle.write(f"fields = {' '.join(fields)}\n")
        handle.write(f"units_offset = {' '.join(['0'] * len(fields))}\n")
        handle.write(f"units_multiplier = {' '.join(['1'] * len(fields))}\n")
        handle.write("[DATA]\n")
        for _, row in prepared.iterrows():
            values = []
            for field in fields:
                if field == "timestamp":
                    values.append(row[field].strftime("%Y-%m-%dT%H:%M:%S"))
                    continue
                value = row.get(field, SMET_NODATA)
                if pd.isna(value):
                    value = SMET_NODATA
                values.append(f"{float(value):.2f}")
            handle.write("\t".join(values) + "\n")

    return path

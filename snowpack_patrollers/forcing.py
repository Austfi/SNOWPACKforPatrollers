from __future__ import annotations

import gzip
import struct
import tarfile
import urllib.request
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from .models import ForcingRequest, ForcingResult, WorkspacePaths

AORC_COVERAGE_END = pd.Timestamp("2024-12-31")
OPENMETEO_MODEL_MAPPING = {
    "nbm": "ncep_nbm_conus",
    "ifs": "ecmwf_ifs",
    "gfs": "gfs_global",
    "nam": "ncep_nam_conus",
}
SNODAS_BOUNDS = {
    "lat_min": 24.95,
    "lat_max": 52.88,
    "lon_min": -124.74,
    "lon_max": -66.94,
}
PRESSURE_CANDIDATES = ("PRES_surface", "PSFC_surface", "PRES")
AORC_BUCKET = "noaa-nws-aorc-v1-1-1km"
AORC_VARIABLES = (
    "TMP_2maboveground",
    "SPFH_2maboveground",
    "UGRD_10maboveground",
    "VGRD_10maboveground",
    "DSWRF_surface",
    "DLWRF_surface",
    "APCP_surface",
)
HRRR_SEARCH = (
    ":TMP:2 m above ground:"
    "|:RH:2 m above ground:"
    "|:UGRD:10 m above ground:"
    "|:VGRD:10 m above ground:"
    "|:APCP:surface:0-1 hour acc fcst"
    "|:DSWRF:surface:"
    "|:DLWRF:surface:"
    "|:SNOD:surface:"
)
HRRR_TREE_NAME = "hrrr_conus"
HRRR_MAX_WORKERS = 4
LONGWAVE_PROVIDERS = {"aorc", "hrrr"}


def is_conus(latitude: float, longitude: float) -> bool:
    return (
        SNODAS_BOUNDS["lat_min"] <= latitude <= SNODAS_BOUNDS["lat_max"]
        and SNODAS_BOUNDS["lon_min"] <= longitude <= SNODAS_BOUNDS["lon_max"]
    )


def resolve_openmeteo_elevation(mode: str, station_altitude_meters: float) -> float | None:
    mode_normalized = mode.lower()
    if mode_normalized == "use_model_elevation":
        return None
    if mode_normalized == "use_selected_altitude":
        return float(station_altitude_meters)
    raise ValueError(f"Unknown Open-Meteo elevation mode: {mode}")


def resolve_forcing_provider(request: ForcingRequest) -> str:
    provider = request.forcing_provider.lower()
    if provider == "auto":
        if is_conus(request.site.latitude, request.site.longitude) and pd.Timestamp(request.end_date) <= AORC_COVERAGE_END:
            return "aorc"
        if is_conus(request.site.latitude, request.site.longitude):
            return "hrrr"
        return "openmeteo"
    if provider == "aorc":
        _validate_aorc_request(request)
        return provider
    if provider == "hrrr":
        _validate_hrrr_request(request)
        return provider
    if provider == "openmeteo":
        return provider
    raise ValueError(f"Unknown forcing provider: {request.forcing_provider}")


def provider_supplies_measured_longwave(provider: str) -> bool:
    return provider.lower() in LONGWAVE_PROVIDERS


def compute_relative_humidity(temp_k: np.ndarray, specific_humidity: np.ndarray, pressure_pa: np.ndarray) -> np.ndarray:
    temp_c = temp_k - 273.15
    es = 6.112 * np.exp((17.67 * temp_c) / (temp_c + 243.5)) * 100.0
    es = np.maximum(es, 1.0)
    vapor_pressure = (specific_humidity * pressure_pa) / (0.622 + 0.378 * specific_humidity)
    return np.clip(vapor_pressure / es, 0.0, 1.0)


def wind_from_components(u: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    speed = np.sqrt(u**2 + v**2)
    direction = (270.0 - np.degrees(np.arctan2(v, u))) % 360.0
    return speed, direction


def cumulative_to_hourly(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    increments = np.diff(array, prepend=np.nan)
    increments[np.isnan(increments)] = array[0]
    resets = increments < 0
    increments[resets] = array[resets]
    return np.clip(increments, 0.0, None)


def build_synthetic_weather_dataframe(start_date: str, hours: int = 48) -> pd.DataFrame:
    timestamps = pd.date_range(start=pd.Timestamp(start_date), periods=hours, freq="h")
    phase = np.linspace(0.0, 2.0 * np.pi, hours)
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "TA": 268.15 + 6.0 * np.sin(phase),
            "RH": np.clip(0.65 + 0.2 * np.cos(phase), 0.2, 0.98),
            "TSG": np.full(hours, 273.15),
            "VW": np.full(hours, 4.5),
            "DW": np.full(hours, 225.0),
            "ISWR": np.clip(350.0 * np.sin(phase), 0.0, None),
            "PSUM": np.where(np.sin(phase) > 0.7, 1.5, 0.0),
            "HS": np.full(hours, 0.5),
        }
    )


def fetch_openmeteo_historical(
    *,
    request: ForcingRequest,
    cache_dir: Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    try:
        import openmeteo_requests
        import requests_cache
        from retry_requests import retry
    except ImportError as exc:
        raise ImportError("Open-Meteo support requires openmeteo-requests, requests-cache, and retry-requests.") from exc

    model_name = OPENMETEO_MODEL_MAPPING.get(request.openmeteo_model)
    if model_name is None:
        raise ValueError(f"Unsupported Open-Meteo model: {request.openmeteo_model}")

    cache_session = requests_cache.CachedSession(str(cache_dir / "openmeteo_cache"), expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    client = openmeteo_requests.Client(session=retry_session)

    url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
    params: dict[str, Any] = {
        "latitude": request.site.latitude,
        "longitude": request.site.longitude,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "wind_direction_10m",
            "snow_depth",
            "direct_radiation",
            "precipitation",
        ],
        "models": model_name,
        "wind_speed_unit": "ms",
        "timezone": "GMT",
    }

    elevation = resolve_openmeteo_elevation(request.openmeteo_elevation_mode, request.site.altitude_meters)
    if elevation is not None:
        params["elevation"] = elevation

    responses = client.weather_api(url, params=params)
    response = responses[0]
    hourly = response.Hourly()
    time_index = pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left",
    )

    dataframe = pd.DataFrame(
        {
            "timestamp": time_index,
            "TA": hourly.Variables(0).ValuesAsNumpy() + 273.15,
            "RH": hourly.Variables(1).ValuesAsNumpy() / 100.0,
            "VW": hourly.Variables(2).ValuesAsNumpy(),
            "DW": hourly.Variables(3).ValuesAsNumpy(),
            "HS": hourly.Variables(4).ValuesAsNumpy(),
            "ISWR": hourly.Variables(5).ValuesAsNumpy(),
            "PSUM": hourly.Variables(6).ValuesAsNumpy(),
            "TSG": np.full(len(time_index), 273.15),
        }
    ).replace([np.inf, -np.inf], np.nan)

    return dataframe, {"model": model_name, "records": len(dataframe), "provider": "openmeteo"}


def build_hrrr_valid_times(start_date: str, end_date: str) -> pd.DatetimeIndex:
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date) + pd.Timedelta(hours=23)
    return pd.date_range(start_ts, end_ts, freq="1h")


def fetch_hrrr_point_series(
    *,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    cache_dir: Path,
    max_workers: int = HRRR_MAX_WORKERS,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    try:
        import xarray as xr
        from herbie import Herbie
    except ImportError as exc:
        raise ImportError("HRRR support requires herbie-data, xarray, and cfgrib/eccodes runtime support.") from exc

    valid_times = build_hrrr_valid_times(start_date, end_date)
    cache_dir.mkdir(parents=True, exist_ok=True)
    point_frame = pd.DataFrame({"latitude": [latitude], "longitude": [longitude]})

    rows: list[dict[str, Any]] = []
    grid_distances_km: list[float] = []
    failures: list[str] = []

    def fetch_single_valid_time(valid_time: pd.Timestamp) -> dict[str, Any]:
        cycle_time = valid_time - pd.Timedelta(hours=1)
        herbie_object = Herbie(
            cycle_time,
            model="hrrr",
            product="sfc",
            fxx=1,
            save_dir=cache_dir,
            verbose=False,
        )
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="In a future version of xarray the default value for compat will change.*",
                category=FutureWarning,
                module="cfgrib.xarray_store",
            )
            dataset = herbie_object.xarray(HRRR_SEARCH, remove_grib=True)
        merged = _merge_herbie_datasets(dataset, xr)
        matched = merged.herbie.pick_points(
            point_frame,
            method="nearest",
            tree_name=HRRR_TREE_NAME,
            verbose=False,
        )
        point = matched.squeeze(drop=True)

        speed, direction = wind_from_components(
            np.array([float(point["u10"].values)]),
            np.array([float(point["v10"].values)]),
        )
        grid_distance_km = _extract_optional_point_grid_distance(point)

        return {
            "timestamp": pd.Timestamp(point["valid_time"].values),
            "TA": float(point["t2m"].values),
            "RH": float(point["r2"].values) / 100.0,
            "TSG": 273.15,
            "VW": float(speed[0]),
            "DW": float(direction[0]),
            "ISWR": float(point["sdswrf"].values),
            "ILWR": float(point["sdlwrf"].values),
            "PSUM": float(point["tp"].values),
            "HS": float(point["sde"].values),
            "_grid_distance_km": grid_distance_km,
        }

    workers = min(max_workers, max(1, len(valid_times)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_single_valid_time, valid_time): valid_time for valid_time in valid_times}
        for future in as_completed(futures):
            valid_time = futures[future]
            try:
                row = future.result()
                grid_distance_km = row.pop("_grid_distance_km")
                if grid_distance_km is not None:
                    grid_distances_km.append(grid_distance_km)
                rows.append(row)
            except Exception as exc:  # pragma: no cover - network/runtime failures are surfaced directly
                failures.append(f"{valid_time.isoformat()}: {exc}")

    if failures:
        preview = "; ".join(failures[:5])
        suffix = "" if len(failures) <= 5 else f" ... ({len(failures)} failures total)"
        raise RuntimeError(f"HRRR retrieval failed for one or more hours. {preview}{suffix}")

    dataframe = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    metadata = {
        "provider": "hrrr",
        "records": len(dataframe),
        "hours_requested": len(valid_times),
        "grid_distance_km_max": max(grid_distances_km) if grid_distances_km else None,
        "grid_distance_km_mean": float(np.mean(grid_distances_km)) if grid_distances_km else None,
    }
    return dataframe, metadata


def fetch_aorc_point_series(
    *,
    latitude: float,
    longitude: float,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    try:
        import s3fs
        import xarray as xr
    except ImportError as exc:
        raise ImportError("AORC support requires s3fs and xarray.") from exc

    s3_filesystem = s3fs.S3FileSystem(anon=True)
    try:
        frames: list[pd.DataFrame] = []
        selected_lat = float("nan")
        selected_lon = float("nan")
        pressure_var = None
        missing_years: list[int] = []

        for year in range(start_ts.year, end_ts.year + 1):
            year_start = pd.Timestamp(f"{year}-01-01 00:00:00")
            year_end = pd.Timestamp(f"{year}-12-31 23:00:00")
            slice_start = max(start_ts, year_start)
            slice_end = min(end_ts, year_end)
            if slice_start > slice_end:
                continue

            store_path = f"{AORC_BUCKET}/{year}.zarr"
            if not s3_filesystem.exists(store_path):
                missing_years.append(year)
                continue

            mapper = s3_filesystem.get_mapper(store_path)
            dataset = xr.open_zarr(mapper, consolidated=True)
            try:
                if pressure_var is None:
                    pressure_var = _detect_pressure_var(dataset)
                    if pressure_var is None:
                        raise KeyError("Surface pressure variable not found in AORC dataset.")

                requested_variables = [name for name in AORC_VARIABLES if name in dataset.data_vars]
                if pressure_var not in requested_variables:
                    requested_variables.append(pressure_var)

                subset = dataset[requested_variables].sel(time=slice(slice_start, slice_end))
                if subset.time.size == 0:
                    continue

                point = subset.sel(latitude=latitude, longitude=longitude, method="nearest").load()
                selected_lat = float(np.asarray(point.latitude.values).flat[0])
                selected_lon = float(np.asarray(point.longitude.values).flat[0])
                frames.append(point.to_dataframe().reset_index())
            finally:
                dataset.close()

        if not frames:
            raise RuntimeError("No AORC data retrieved for the requested date range.")

        raw = pd.concat(frames, ignore_index=True)
        metadata = {
            "selected_lat": selected_lat,
            "selected_lon": selected_lon,
            "pressure_var": pressure_var,
            "missing_years": missing_years,
            "records": len(raw),
        }
        return raw, metadata
    finally:
        _close_s3fs_session(s3_filesystem, s3fs)


def prepare_aorc_weather_dataframe(
    *,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date) + pd.Timedelta(hours=23)

    raw, metadata = fetch_aorc_point_series(
        latitude=latitude,
        longitude=longitude,
        start_ts=start_ts,
        end_ts=end_ts,
    )
    pressure_var = metadata["pressure_var"]
    if pressure_var is None:
        raise KeyError("AORC pressure variable could not be resolved.")

    raw = raw.sort_values("time").reset_index(drop=True)
    rh = compute_relative_humidity(
        raw["TMP_2maboveground"].to_numpy(),
        raw["SPFH_2maboveground"].to_numpy(),
        raw[pressure_var].to_numpy(),
    )
    vw, dw = wind_from_components(
        raw["UGRD_10maboveground"].to_numpy(),
        raw["VGRD_10maboveground"].to_numpy(),
    )
    psum = cumulative_to_hourly(raw["APCP_surface"].to_numpy())

    dataframe = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(raw["time"]),
            "TA": raw["TMP_2maboveground"].to_numpy(),
            "RH": rh,
            "TSG": np.full(len(raw), 273.15),
            "VW": vw,
            "DW": dw,
            "ISWR": raw["DSWRF_surface"].to_numpy(),
            "ILWR": raw["DLWRF_surface"].to_numpy(),
            "PSUM": psum,
            "HS": np.full(len(raw), -777.0),
        }
    ).replace([np.inf, -np.inf], np.nan)
    return dataframe, metadata


def get_snodas_snow_depth(
    latitude: float,
    longitude: float,
    date_key: str,
    cache_dir: str | Path,
) -> float | None:
    if not is_conus(latitude, longitude):
        return None

    grid_configs = {
        "old": {
            "XMIN": -124.73375000000000,
            "YMAX": 52.87458333333333,
            "XMAX": -66.94208333333333,
            "YMIN": 24.94958333333333,
            "NCOLS": 6935,
            "NROWS": 3351,
        },
        "new": {
            "XMIN": -124.73333333333333,
            "YMAX": 52.87500000000000,
            "XMAX": -66.94166666666667,
            "YMIN": 24.95000000000000,
            "NCOLS": 3353,
            "NROWS": 3353,
        },
    }

    month_names = (
        "01_Jan",
        "02_Feb",
        "03_Mar",
        "04_Apr",
        "05_May",
        "06_Jun",
        "07_Jul",
        "08_Aug",
        "09_Sep",
        "10_Oct",
        "11_Nov",
        "12_Dec",
    )
    tar_name = f"SNODAS_{date_key}.tar"
    tar_path = Path(cache_dir) / tar_name
    tar_path.parent.mkdir(parents=True, exist_ok=True)
    year = date_key[:4]
    month = date_key[4:6]
    data_url = f"https://noaadata.apps.nsidc.org/NOAA/G02158/masked/{year}/{month_names[int(month) - 1]}/{tar_name}"

    if tar_path.exists():
        tar_bytes = tar_path.read_bytes()
    else:
        request = urllib.request.Request(data_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            tar_bytes = response.read()
        tar_path.write_bytes(tar_bytes)

    with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r") as archive:
        gz_member = None
        for member in archive.getmembers():
            if "1036" in member.name and member.name.endswith(".dat.gz"):
                gz_member = archive.extractfile(member)
                break
        if gz_member is None:
            return None
        with gzip.open(gz_member, "rb") as handle:
            data = handle.read()

    num_values = len(data) // 2
    config = next((cfg for cfg in grid_configs.values() if cfg["NCOLS"] * cfg["NROWS"] == num_values), None)
    if config is None:
        return None

    values = struct.unpack(f">{config['NCOLS'] * config['NROWS']}h", data)
    grid = np.array(values).reshape((config["NROWS"], config["NCOLS"]))
    cell_size_x = (config["XMAX"] - config["XMIN"]) / config["NCOLS"]
    cell_size_y = (config["YMAX"] - config["YMIN"]) / config["NROWS"]
    col = int((longitude - config["XMIN"]) / cell_size_x)
    row = int((config["YMAX"] - latitude) / cell_size_y)
    col = max(0, min(config["NCOLS"] - 1, col))
    row = max(0, min(config["NROWS"] - 1, row))
    value = grid[row, col]
    if value < 0 or value == -9999:
        return None
    return value / 1000.0


def apply_snodas_hs(
    dataframe: pd.DataFrame,
    *,
    latitude: float,
    longitude: float,
    cache_dir: Path,
    fallback_to_existing: bool = False,
    fetcher: Callable[[float, float, str, str | Path], float | None] = get_snodas_snow_depth,
    max_workers: int = 4,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    result = dataframe.copy()
    existing_hs = result["HS"].copy() if fallback_to_existing and "HS" in result.columns else None

    if not is_conus(latitude, longitude):
        if existing_hs is not None:
            result["HS"] = existing_hs
            return result, {"fallback_hours": len(result), "missing_dates": [], "outside_conus": True}
        result["HS"] = -777.0
        return result, {"fallback_hours": 0, "missing_dates": [], "outside_conus": True}

    date_keys = pd.to_datetime(result["timestamp"]).dt.strftime("%Y%m%d")
    unique_dates = sorted(date_keys.unique())
    depths: dict[str, float] = {}
    missing_dates: list[str] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetcher, latitude, longitude, date_key, cache_dir): date_key for date_key in unique_dates}
        for future in as_completed(futures):
            date_key = futures[future]
            depth = future.result()
            if depth is None:
                missing_dates.append(date_key)
            else:
                depths[date_key] = depth

    hs_values = []
    replaced_hours = 0
    fallback_hours = 0
    nodata_hours = 0
    for index, date_key in enumerate(date_keys):
        if date_key in depths:
            hs_values.append(depths[date_key])
            replaced_hours += 1
        elif existing_hs is not None and pd.notna(existing_hs.iloc[index]):
            hs_values.append(float(existing_hs.iloc[index]))
            fallback_hours += 1
        else:
            hs_values.append(-777.0)
            nodata_hours += 1

    result["HS"] = np.asarray(hs_values, dtype=float)
    metadata = {
        "replaced_hours": replaced_hours,
        "fallback_hours": fallback_hours,
        "nodata_hours": nodata_hours,
        "missing_dates": sorted(missing_dates),
    }
    return result, metadata


def build_forcing_dataframe(
    *,
    request: ForcingRequest,
    workspace: WorkspacePaths,
) -> ForcingResult:
    provider = resolve_forcing_provider(request)
    if provider == "openmeteo":
        dataframe, metadata = fetch_openmeteo_historical(request=request, cache_dir=workspace.root)
    elif provider == "hrrr":
        dataframe, metadata = fetch_hrrr_point_series(
            latitude=request.site.latitude,
            longitude=request.site.longitude,
            start_date=request.start_date,
            end_date=request.end_date,
            cache_dir=workspace.root / "hrrr_cache",
        )
    else:
        dataframe, metadata = prepare_aorc_weather_dataframe(
            latitude=request.site.latitude,
            longitude=request.site.longitude,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        metadata["provider"] = "aorc"

    effective_hs_source = "snodas" if provider == "aorc" else request.hs_source.lower()
    if effective_hs_source == "snodas":
        dataframe, snodas_metadata = apply_snodas_hs(
            dataframe,
            latitude=request.site.latitude,
            longitude=request.site.longitude,
            cache_dir=workspace.cache_dir,
            fallback_to_existing=provider in {"openmeteo", "hrrr"},
        )
        metadata["snodas"] = snodas_metadata
    elif "HS" not in dataframe.columns:
        dataframe["HS"] = -777.0

    if "TSG" not in dataframe.columns:
        dataframe["TSG"] = 273.15
    dataframe = dataframe.replace([np.inf, -np.inf], np.nan)

    smet_path = workspace.input_dir / f"{request.site.station_id}.smet"
    return ForcingResult(provider=provider, dataframe=dataframe, smet_path=smet_path, metadata=metadata)


def _merge_herbie_datasets(dataset_or_list: Any, xr_module: Any) -> Any:
    if isinstance(dataset_or_list, list):
        cleaned = [dataset.drop_vars("gribfile_projection", errors="ignore") for dataset in dataset_or_list]
        return xr_module.merge(cleaned, compat="override")
    return dataset_or_list.drop_vars("gribfile_projection", errors="ignore")


def _extract_optional_point_grid_distance(point: Any) -> float | None:
    if "point_grid_distance" not in point:
        return None
    value = float(point["point_grid_distance"].values)
    if np.isnan(value):
        return None
    return value


def _close_s3fs_session(filesystem: Any, s3fs_module: Any) -> None:
    session_target = getattr(filesystem, "_s3creator", None)
    loop = getattr(filesystem, "loop", None)
    if session_target is not None and loop is not None and hasattr(session_target, "__aexit__"):
        try:
            from fsspec.asyn import sync

            sync(loop, session_target.__aexit__, None, None, None)
            return
        except Exception:
            pass

    session_target = getattr(filesystem, "s3", None)
    if session_target is None:
        return
    try:
        s3fs_module.S3FileSystem.close_session(loop, session_target)
    except Exception:
        return


def _detect_pressure_var(dataset: Any) -> str | None:
    for candidate in PRESSURE_CANDIDATES:
        if candidate in dataset.data_vars:
            return candidate
    return None


def _validate_aorc_request(request: ForcingRequest) -> None:
    if pd.Timestamp(request.end_date) > AORC_COVERAGE_END:
        raise ValueError("AORC forcing is only supported through 2024-12-31.")
    if not is_conus(request.site.latitude, request.site.longitude):
        raise ValueError("AORC forcing is currently limited to CONUS points supported by the public archive.")


def _validate_hrrr_request(request: ForcingRequest) -> None:
    if not is_conus(request.site.latitude, request.site.longitude):
        raise ValueError("Direct HRRR forcing is currently limited to CONUS points.")

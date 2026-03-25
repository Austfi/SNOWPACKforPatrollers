import numpy as np
import pandas as pd
import pytest

from snowpack_patrollers.forcing import (
    _close_s3fs_session,
    apply_snodas_hs,
    build_hrrr_valid_times,
    compute_relative_humidity,
    cumulative_to_hourly,
    _extract_optional_point_grid_distance,
    _merge_herbie_datasets,
    provider_supplies_measured_longwave,
    resolve_forcing_provider,
    wind_from_components,
)
from snowpack_patrollers.models import ForcingRequest, SiteConfig


def _request(end_date: str, forcing_provider: str = "auto") -> ForcingRequest:
    site = SiteConfig(
        station_id="demo",
        station_name="Demo",
        latitude=39.7,
        longitude=-105.8,
        altitude_meters=3200.0,
    )
    return ForcingRequest(
        site=site,
        start_date="2024-11-01",
        end_date=end_date,
        forcing_provider=forcing_provider,
    )


def test_resolve_forcing_provider_auto_uses_aorc_for_supported_runs():
    assert resolve_forcing_provider(_request("2024-12-31")) == "aorc"


def test_resolve_forcing_provider_auto_uses_hrrr_after_aorc_cutoff_for_conus():
    assert resolve_forcing_provider(_request("2025-01-02")) == "hrrr"


def test_resolve_forcing_provider_explicit_hrrr_is_supported_for_conus():
    assert resolve_forcing_provider(_request("2025-01-02", forcing_provider="hrrr")) == "hrrr"


def test_provider_supplies_measured_longwave_for_aorc_and_hrrr():
    assert provider_supplies_measured_longwave("aorc") is True
    assert provider_supplies_measured_longwave("hrrr") is True
    assert provider_supplies_measured_longwave("openmeteo") is False


def test_build_hrrr_valid_times_expands_to_full_hourly_window():
    valid_times = build_hrrr_valid_times("2025-03-01", "2025-03-02")
    assert len(valid_times) == 48
    assert str(valid_times[0]) == "2025-03-01 00:00:00"
    assert str(valid_times[-1]) == "2025-03-02 23:00:00"


def test_cumulative_to_hourly_handles_resets():
    values = np.array([0.5, 0.75, 1.1, 0.2, 0.4])
    assert np.allclose(cumulative_to_hourly(values), np.array([0.5, 0.25, 0.35, 0.2, 0.2]))


def test_wind_from_components_returns_speed_and_direction():
    speed, direction = wind_from_components(np.array([1.0]), np.array([0.0]))
    assert np.allclose(speed, np.array([1.0]))
    assert np.allclose(direction, np.array([270.0]))


def test_compute_relative_humidity_is_clamped_between_zero_and_one():
    humidity = compute_relative_humidity(
        np.array([273.15, 280.15]),
        np.array([0.002, 0.020]),
        np.array([85000.0, 85000.0]),
    )
    assert np.all(humidity >= 0.0)
    assert np.all(humidity <= 1.0)


def test_apply_snodas_hs_uses_fallback_for_missing_dates(tmp_path):
    dataframe = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-11-01T00:00:00", "2024-11-02T00:00:00"]),
            "HS": [0.4, 0.8],
        }
    )

    def fake_fetcher(latitude, longitude, date_key, cache_dir):
        return 0.6 if date_key == "20241101" else None

    updated, metadata = apply_snodas_hs(
        dataframe,
        latitude=39.7,
        longitude=-105.8,
        cache_dir=tmp_path,
        fallback_to_existing=True,
        fetcher=fake_fetcher,
        max_workers=1,
    )

    assert updated["HS"].tolist() == [0.6, 0.8]
    assert metadata["replaced_hours"] == 1
    assert metadata["fallback_hours"] == 1


def test_apply_snodas_hs_sets_nodata_when_no_fallback(tmp_path):
    dataframe = pd.DataFrame({"timestamp": pd.to_datetime(["2024-11-01T00:00:00"])})

    def fake_fetcher(latitude, longitude, date_key, cache_dir):
        return None

    updated, metadata = apply_snodas_hs(
        dataframe,
        latitude=39.7,
        longitude=-105.8,
        cache_dir=tmp_path,
        fallback_to_existing=False,
        fetcher=fake_fetcher,
        max_workers=1,
    )

    assert updated["HS"].tolist() == [-777.0]
    assert metadata["nodata_hours"] == 1


def test_merge_herbie_datasets_merges_list_and_drops_projection():
    xr = pytest.importorskip("xarray")

    first = xr.Dataset(
        {"t2m": (("y", "x"), [[270.0]])},
        coords={"y": [0], "x": [0]},
    )
    first["gribfile_projection"] = xr.DataArray(1)
    second = xr.Dataset(
        {"u10": (("y", "x"), [[5.0]])},
        coords={"y": [0], "x": [0]},
    )

    merged = _merge_herbie_datasets([first, second], xr)
    assert "t2m" in merged.data_vars
    assert "u10" in merged.data_vars
    assert "gribfile_projection" not in merged.data_vars


def test_extract_optional_point_grid_distance_handles_missing_variable():
    xr = pytest.importorskip("xarray")
    dataset = xr.Dataset({"t2m": ((), 270.0)})
    assert _extract_optional_point_grid_distance(dataset) is None


def test_close_s3fs_session_uses_static_close_when_client_exists():
    calls = []

    class FakeClient:
        pass

    class FakeFilesystem:
        loop = "loop"
        s3 = FakeClient()

    class FakeS3FileSystem:
        @staticmethod
        def close_session(loop, s3):
            calls.append((loop, s3))

    class FakeModule:
        S3FileSystem = FakeS3FileSystem

    _close_s3fs_session(FakeFilesystem(), FakeModule)
    assert calls == [("loop", FakeFilesystem.s3)]

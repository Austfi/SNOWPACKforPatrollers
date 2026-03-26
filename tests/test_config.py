import pytest

from snowpack_patrollers.config import generate_config_files
from snowpack_patrollers.models import SiteConfig, SlopeConfig, SnowpackConfig
from snowpack_patrollers.workflow import create_workspace, get_buffered_start_date


def test_generate_config_files_writes_expected_ini(tmp_path):
    workspace = create_workspace(tmp_path / "work")
    site = SiteConfig(
        station_id="demo",
        station_name="Demo Station",
        latitude=39.7,
        longitude=-105.8,
        altitude_meters=3200.0,
    )
    slopes = SlopeConfig(custom_directions="45,135")
    snowpack = SnowpackConfig(
        profile_date="2024-11-01T00:00:00",
        snowpack_end_date="2025-04-01T00:00",
        atmospheric_stability="MO_MICHLMAYR",
        meas_incoming_longwave=True,
    )

    artifacts = generate_config_files(site=site, slopes=slopes, snowpack=snowpack, workspace=workspace)

    ini_text = artifacts.ini_path.read_text()
    assert "BUFFER_SIZE = 370" in ini_text
    assert "BUFF_BEFORE = 1.5" in ini_text
    assert "ATMOSPHERIC_STABILITY = MO_MICHLMAYR" in ini_text
    assert "MEAS_INCOMING_LONGWAVE = true" in ini_text
    assert "SNOW_REDISTRIBUTION = TRUE" in ini_text
    assert "PSUM::ACCUMULATE::PERIOD = 1800" in ini_text
    assert "HS::LINEAR::MAX_GAP_SIZE = 43200" in ini_text
    assert "VW::resample1 = linear" in ini_text
    assert len(artifacts.sno_paths) == 5


def test_generate_config_files_uses_station_id_for_flat_slope(tmp_path):
    workspace = create_workspace(tmp_path / "work")
    site = SiteConfig(
        station_id="watrous",
        station_name="Watrous",
        latitude=39.7,
        longitude=-105.8,
        altitude_meters=3200.0,
    )
    slopes = SlopeConfig(num_slopes=2, include_flat=True, east_slope=True, north_slope=False, south_slope=False, west_slope=False)
    snowpack = SnowpackConfig(
        profile_date="2024-11-01T00:00:00",
        snowpack_end_date="2025-04-01T00:00",
    )

    artifacts = generate_config_files(site=site, slopes=slopes, snowpack=snowpack, workspace=workspace)

    names = [path.name for path in artifacts.sno_paths]
    assert names == ["watrous.sno", "watrous1.sno"]


def test_generate_config_files_disables_redistribution_for_single_slope(tmp_path):
    workspace = create_workspace(tmp_path / "work")
    site = SiteConfig(
        station_id="flatdemo",
        station_name="Flat Demo",
        latitude=39.7,
        longitude=-105.8,
        altitude_meters=3200.0,
    )
    slopes = SlopeConfig(
        num_slopes=1,
        include_flat=True,
        north_slope=False,
        east_slope=False,
        south_slope=False,
        west_slope=False,
    )
    snowpack = SnowpackConfig(
        profile_date="2024-11-01T00:00:00",
        snowpack_end_date="2025-04-01T00:00",
    )

    artifacts = generate_config_files(site=site, slopes=slopes, snowpack=snowpack, workspace=workspace)

    ini_text = artifacts.ini_path.read_text()
    assert "NUMBER_SLOPES = 1" in ini_text
    assert "SNOW_REDISTRIBUTION = FALSE" in ini_text


def test_generate_config_files_requires_at_least_one_slope(tmp_path):
    workspace = create_workspace(tmp_path / "work")
    site = SiteConfig(
        station_id="watrous",
        station_name="Watrous",
        latitude=39.7,
        longitude=-105.8,
        altitude_meters=3200.0,
    )
    slopes = SlopeConfig(
        num_slopes=1,
        include_flat=False,
        north_slope=False,
        east_slope=False,
        south_slope=False,
        west_slope=False,
    )
    snowpack = SnowpackConfig(
        profile_date="2024-11-01T00:00:00",
        snowpack_end_date="2025-04-01T00:00",
    )

    with pytest.raises(ValueError, match="At least one slope must be selected"):
        generate_config_files(site=site, slopes=slopes, snowpack=snowpack, workspace=workspace)


def test_get_buffered_start_date_uses_two_day_buffer():
    assert get_buffered_start_date("2024-03-01") == "2024-02-28"

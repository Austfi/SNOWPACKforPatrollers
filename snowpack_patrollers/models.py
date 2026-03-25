from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SiteConfig:
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    altitude_meters: float
    timezone: float = 0.0
    coord_sys: str = "UTM"
    coord_param: str = "13S"


@dataclass(slots=True)
class SlopeConfig:
    num_slopes: int = 5
    include_flat: bool = True
    default_slope_angle: float = 38.0
    north_slope: bool = True
    east_slope: bool = True
    south_slope: bool = True
    west_slope: bool = True
    custom_directions: str = ""


@dataclass(slots=True)
class SnowpackConfig:
    profile_date: str
    snowpack_end_date: str
    meas_tss: bool = False
    enforce_measured_snow_heights: bool = False
    write_profiles: bool = True
    write_timeseries: bool = False
    write_snowpack: bool = False
    atmospheric_stability: str = "NEUTRAL"
    snow_erosion: bool = True
    snow_redistribution: bool = True
    roughness_length: float = 0.002
    calculation_step_length: float = 30.0
    height_of_wind_value: float = 10.0
    height_of_meteo_values: float = 2.0
    meas_incoming_longwave: bool = False
    psum_accumulate_period: int = 1800
    max_gap_size: int = 86400
    hs_linear_max_gap_size: int = 43200
    buffer_size: int = 370
    buff_before: float = 1.5
    vw_resample: str = "linear"
    dw_resample: str = "nearest"


@dataclass(slots=True)
class ForcingRequest:
    site: SiteConfig
    start_date: str
    end_date: str
    forcing_provider: str = "auto"
    openmeteo_model: str = "ifs"
    hs_source: str = "model"
    openmeteo_elevation_mode: str = "use_selected_altitude"
    debug: bool = False


@dataclass(slots=True)
class WorkspacePaths:
    root: Path
    input_dir: Path
    config_dir: Path
    output_dir: Path
    cache_dir: Path
    bundle_path: Path


@dataclass(slots=True)
class ConfigArtifacts:
    ini_path: Path
    sno_paths: list[Path]


@dataclass(slots=True)
class ForcingResult:
    provider: str
    dataframe: Any
    smet_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowResult:
    provider: str
    workspace: WorkspacePaths
    ini_path: Path
    sno_paths: list[Path]
    smet_path: Path
    profile_files: list[Path] = field(default_factory=list)
    bundle_path: Path | None = None
    forcing_metadata: dict[str, Any] = field(default_factory=dict)
    snowpack_stdout: str = ""

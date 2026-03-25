from __future__ import annotations

from pathlib import Path

from .models import ConfigArtifacts, SiteConfig, SlopeConfig, SnowpackConfig, WorkspacePaths


def to_meters(value: float, unit: str) -> float:
    unit_normalized = unit.lower()
    if unit_normalized == "meters":
        return float(value)
    if unit_normalized == "feet":
        return float(value) * 0.3048
    raise ValueError(f"Unsupported altitude unit: {unit}")


def _as_ini_bool(value: bool) -> str:
    return str(bool(value)).lower()


def generate_slopes(config: SlopeConfig) -> list[tuple[float, float]]:
    slopes: list[tuple[float, float]] = []
    if config.include_flat:
        slopes.append((0.0, 0.0))
    if config.north_slope:
        slopes.append((config.default_slope_angle, 0.0))
    if config.east_slope:
        slopes.append((config.default_slope_angle, 90.0))
    if config.south_slope:
        slopes.append((config.default_slope_angle, 180.0))
    if config.west_slope:
        slopes.append((config.default_slope_angle, 270.0))

    if config.custom_directions.strip():
        custom_angles = [value.strip() for value in config.custom_directions.split(",") if value.strip()]
        for value in custom_angles:
            angle = float(value)
            if 0 <= angle <= 360:
                slopes.append((config.default_slope_angle, angle))

    selected = slopes[: config.num_slopes]
    if not selected:
        raise ValueError("At least one slope must be selected. Enable flat terrain, a compass slope, or provide a custom direction.")
    return selected


def get_slope_filename(angle: float, slope_index: int, include_flat: bool, station_id: str) -> str:
    if angle == 0.0:
        return station_id
    if include_flat:
        return f"{station_id}{slope_index}"
    return f"{station_id}{slope_index + 1}"


def create_sno_content(
    *,
    site: SiteConfig,
    profile_date: str,
    slope_angle: float,
    slope_azimuth: float,
) -> str:
    return f"""SMET 1.1 ASCII
[HEADER]
station_id       = {site.station_id}
station_name     = {site.station_name}
longitude        = {site.longitude}
latitude         = {site.latitude}
altitude         = {site.altitude_meters}
nodata           = -999
tz               = {site.timezone}
source           = SNOWPACKforPatrollers
prototype        = SNOWPACK
ProfileDate      = {profile_date}
HS_Last          = 0.0000
SlopeAngle       = {slope_angle}
SlopeAzi         = {slope_azimuth}
nSoilLayerData   = 0
nSnowLayerData   = 0
SoilAlbedo       = 0.09
BareSoil_z0      = 0.020
CanopyHeight     = 0.00
CanopyLeafAreaIndex = 0.00
CanopyDirectThroughfall = 1.00
ErosionLevel     = 0
TimeCountDeltaHS = 0.000000
WindScalingFactor = 1.00

fields           = timestamp Layer_Thick T Vol_Frac_I Vol_Frac_W Vol_Frac_V Vol_Frac_S Rho_S Conduc_S HeatCapac_S rg rb dd sp mk mass_hoar ne CDot metamo
[DATA]
"""


def create_ini_content(
    *,
    site: SiteConfig,
    smet_filename: str,
    snowfiles: list[str],
    snowpack: SnowpackConfig,
) -> str:
    return f"""[General]
BUFFER_SIZE = {snowpack.buffer_size}
BUFF_BEFORE = {snowpack.buff_before}

[Input]
COORDSYS = {site.coord_sys}
COORDPARAM = {site.coord_param}
TIME_ZONE = {site.timezone}

METEO = SMET
METEOPATH = ../input
METEOFILE1 = {smet_filename}
{_render_snowfile_lines(snowfiles)}
[Output]
COORDSYS = {site.coord_sys}
COORDPARAM = {site.coord_param}
TIME_ZONE = {site.timezone}
METEOPATH = ./output
EXPERIMENT = res
SNOW_WRITE = {_as_ini_bool(snowpack.write_snowpack)}

TS_WRITE = {_as_ini_bool(snowpack.write_timeseries)}
TS_FORMAT = SMET
TS_START = 0.0
TS_DAYS_BETWEEN = 0.125
PROF_WRITE = {_as_ini_bool(snowpack.write_profiles)}
PROF_FORMAT = PRO
AGGREG_PRF = false
PROF_START = 0.0
PROF_DAYS_BETWEEN = 0.125

[Snowpack]
MEAS_TSS = {_as_ini_bool(snowpack.meas_tss)}
ENFORCE_MEASURED_SNOW_HEIGHTS = {_as_ini_bool(snowpack.enforce_measured_snow_heights)}
FORCING = ATMOS
SW_MODE = INCOMING
MEAS_INCOMING_LONGWAVE = {_as_ini_bool(snowpack.meas_incoming_longwave)}
HEIGHT_OF_WIND_VALUE = {snowpack.height_of_wind_value}
HEIGHT_OF_METEO_VALUES = {snowpack.height_of_meteo_values}
ATMOSPHERIC_STABILITY = {snowpack.atmospheric_stability}
ROUGHNESS_LENGTH = {snowpack.roughness_length}
CALCULATION_STEP_LENGTH = {snowpack.calculation_step_length}
CHANGE_BC = false
THRESH_CHANGE_BC = -1.0
SNP_SOIL = false
SOIL_FLUX = false
GEO_HEAT = 0.06
CANOPY = false

[SnowpackAdvanced]
THRESH_RAIN = 1.4
SSI_IS_RTA = TRUE
FIXED_POSITIONS = 0.25 0.5 1.0 -0.25 -0.10
SNOW_EROSION = {_as_ini_bool(snowpack.snow_erosion)}
WIND_SCALING_FACTOR = 1.0
NUMBER_SLOPES = {len(snowfiles)}
SNOW_REDISTRIBUTION = {_as_ini_bool(snowpack.snow_redistribution)}

[Filters]
ENABLE_METEO_FILTERS = true
PSUM::filter1 = min
PSUM::arg1::soft = true
PSUM::arg1::min = 0.0
TA::filter1 = min_max
TA::arg1::min = 240
TA::arg1::max = 320
RH::filter1 = min_max
RH::arg1::min = 0.01
RH::arg1::max = 1.2
RH::filter2 = min_max
RH::arg2::soft = true
RH::arg2::min = 0.05
RH::arg2::max = 1.0
ISWR::filter1 = min_max
ISWR::arg1::min = -10
ISWR::arg1::max = 1500
ISWR::filter2 = min_max
ISWR::arg2::soft = true
ISWR::arg2::min = 0
ISWR::arg2::max = 1500
RSWR::filter1 = min_max
RSWR::arg1::min = -10
RSWR::arg1::max = 1500
RSWR::filter2 = min_max
RSWR::arg2::soft = true
RSWR::arg2::min = 0
RSWR::arg2::max = 1500
ILWR::filter1 = min_max
ILWR::arg1::min = 188
ILWR::arg1::max = 600
ILWR::filter2 = min_max
ILWR::arg2::soft = true
ILWR::arg2::min = 200
ILWR::arg2::max = 400
TSS::filter1 = min_max
TSS::arg1::min = 200
TSS::arg1::max = 320
TSG::filter1 = min_max
TSG::arg1::min = 200
TSG::arg1::max = 320
HS::filter1 = min
HS::arg1::soft = true
HS::arg1::min = 0.0
HS::filter2 = rate
HS::arg2::max = 5.55e-5
VW::filter1 = min_max
VW::arg1::min = -2
VW::arg1::max = 70
VW::filter2 = min_max
VW::arg2::soft = true
VW::arg2::min = 0.0
VW::arg2::max = 50.0

[Interpolations1D]
MAX_GAP_SIZE = {snowpack.max_gap_size}
PSUM::resample1 = accumulate
PSUM::ARG1::period = {snowpack.psum_accumulate_period}
HS::resample1 = linear
HS::ARG1::MAX_GAP_SIZE = {snowpack.hs_linear_max_gap_size}
VW::resample1 = {snowpack.vw_resample}
VW::ARG1::extrapolate = true
DW::resample1 = {snowpack.dw_resample}
DW::ARG1::extrapolate = true
ILWR::RESAMPLE1 = LINEAR
ISWR::RESAMPLE1 = LINEAR
RH::RESAMPLE1 = LINEAR
TA::RESAMPLE1 = LINEAR

[Generators]
ILWR::generator1 = AllSky_LW
ILWR::arg1::type = Carmona
ILWR::arg1::shade_from_dem = FALSE
ILWR::arg1::use_rswr = FALSE
ILWR::generator2 = ClearSky_LW
ILWR::arg2::type = Dilley
"""


def _render_snowfile_lines(snowfiles: list[str]) -> str:
    return "".join(f"SNOWFILE{i} = ../input/{snowfile}\n" for i, snowfile in enumerate(snowfiles, start=1))


def generate_config_files(
    *,
    site: SiteConfig,
    slopes: SlopeConfig,
    snowpack: SnowpackConfig,
    workspace: WorkspacePaths,
) -> ConfigArtifacts:
    slope_pairs = generate_slopes(slopes)
    snowfile_names: list[str] = []
    sno_paths: list[Path] = []

    for index, (angle, azimuth) in enumerate(slope_pairs):
        name = f"{get_slope_filename(angle, index, slopes.include_flat, site.station_id)}.sno"
        path = workspace.input_dir / name
        path.write_text(
            create_sno_content(
                site=site,
                profile_date=snowpack.profile_date,
                slope_angle=angle,
                slope_azimuth=azimuth,
            )
        )
        snowfile_names.append(name)
        sno_paths.append(path)

    ini_path = workspace.config_dir / f"{site.station_id}.ini"
    ini_path.write_text(
        create_ini_content(
            site=site,
            smet_filename=f"{site.station_id}.smet",
            snowfiles=snowfile_names,
            snowpack=snowpack,
        )
    )
    return ConfigArtifacts(ini_path=ini_path, sno_paths=sno_paths)

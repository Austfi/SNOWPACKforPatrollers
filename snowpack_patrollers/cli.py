from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from .config import generate_config_files
from .forcing import (
    build_forcing_dataframe,
    build_synthetic_weather_dataframe,
    provider_supplies_measured_longwave,
    resolve_forcing_provider,
)
from .models import ForcingRequest, SiteConfig, SlopeConfig, SnowpackConfig
from .runner import bundle_profiles, find_snowpack_executable, run_snowpack
from .smet import create_smet_from_weather_data
from .workflow import create_workspace, run_full_workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="snowpack-patrollers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_config = subparsers.add_parser("generate-config", help="Generate .sno and .ini files.")
    _add_common_arguments(generate_config)

    fetch_forcing = subparsers.add_parser("fetch-forcing", help="Fetch forcing data and write a SMET file.")
    _add_common_arguments(fetch_forcing)

    run_model = subparsers.add_parser("run-model", help="Run SNOWPACK against an existing workdir.")
    run_model.add_argument("--workdir", default=".snowpack_work")
    run_model.add_argument("--station-id", default="watrous")
    run_model.add_argument("--snowpack-executable")
    run_model.add_argument("--snowpack-end-date", default="2025-04-01T00:00")

    smoke = subparsers.add_parser("smoke", help="Run an offline smoke path with synthetic forcing data.")
    _add_common_arguments(smoke)
    smoke.add_argument("--hours", type=int, default=48)
    smoke.add_argument("--skip-model", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate-config":
        return _command_generate_config(args)
    if args.command == "fetch-forcing":
        return _command_fetch_forcing(args)
    if args.command == "run-model":
        return _command_run_model(args)
    if args.command == "smoke":
        return _command_smoke(args)
    parser.error(f"Unsupported command: {args.command}")
    return 2


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workdir", default=".snowpack_work")
    parser.add_argument("--station-id", default="watrous")
    parser.add_argument("--station-name", default="watrous_E_NTL")
    parser.add_argument("--latitude", type=float, default=39.71438)
    parser.add_argument("--longitude", type=float, default=-105.84475)
    parser.add_argument("--altitude-meters", type=float, default=3596.64)
    parser.add_argument("--timezone", type=float, default=0.0)
    parser.add_argument("--coord-sys", default="UTM")
    parser.add_argument("--coord-param", default="13S")
    parser.add_argument("--profile-date", default="2024-11-01T00:00:00")
    parser.add_argument("--snowpack-end-date", default="2025-04-01T00:00")
    parser.add_argument("--start-date", default="2024-11-01")
    parser.add_argument("--end-date", default="2025-04-30")
    parser.add_argument("--forcing-provider", default="auto", choices=["auto", "aorc", "hrrr", "openmeteo"])
    parser.add_argument("--openmeteo-model", default="ifs", choices=["ifs", "gfs", "nbm", "nam"])
    parser.add_argument("--hs-source", default="model", choices=["model", "snodas"])
    parser.add_argument("--openmeteo-elevation-mode", default="use_selected_altitude", choices=["use_model_elevation", "use_selected_altitude"])
    parser.add_argument("--num-slopes", type=int, default=5)
    parser.add_argument("--default-slope-angle", type=float, default=38.0)
    parser.add_argument("--include-flat", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--north-slope", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--east-slope", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--south-slope", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--west-slope", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--custom-directions", default="")
    parser.add_argument("--atmospheric-stability", default="NEUTRAL", choices=["NEUTRAL", "MO_MICHLMAYR", "MO_LOC_STABILITY"])


def _site_from_args(args: argparse.Namespace) -> SiteConfig:
    return SiteConfig(
        station_id=args.station_id,
        station_name=args.station_name,
        latitude=args.latitude,
        longitude=args.longitude,
        altitude_meters=args.altitude_meters,
        timezone=args.timezone,
        coord_sys=args.coord_sys,
        coord_param=args.coord_param,
    )


def _slopes_from_args(args: argparse.Namespace) -> SlopeConfig:
    return SlopeConfig(
        num_slopes=args.num_slopes,
        include_flat=args.include_flat,
        default_slope_angle=args.default_slope_angle,
        north_slope=args.north_slope,
        east_slope=args.east_slope,
        south_slope=args.south_slope,
        west_slope=args.west_slope,
        custom_directions=args.custom_directions,
    )


def _snowpack_from_args(args: argparse.Namespace) -> SnowpackConfig:
    return SnowpackConfig(
        profile_date=args.profile_date,
        snowpack_end_date=args.snowpack_end_date,
        atmospheric_stability=args.atmospheric_stability,
    )


def _forcing_from_args(args: argparse.Namespace, site: SiteConfig) -> ForcingRequest:
    return ForcingRequest(
        site=site,
        start_date=args.start_date,
        end_date=args.end_date,
        forcing_provider=args.forcing_provider,
        openmeteo_model=args.openmeteo_model,
        hs_source=args.hs_source,
        openmeteo_elevation_mode=args.openmeteo_elevation_mode,
    )


def _command_generate_config(args: argparse.Namespace) -> int:
    site = _site_from_args(args)
    slopes = _slopes_from_args(args)
    snowpack = _snowpack_from_args(args)
    forcing = _forcing_from_args(args, site)
    provider = resolve_forcing_provider(forcing)
    workspace = create_workspace(args.workdir)
    snowpack = replace(snowpack, meas_incoming_longwave=provider_supplies_measured_longwave(provider))
    artifacts = generate_config_files(site=site, slopes=slopes, snowpack=snowpack, workspace=workspace)
    print(f"Generated INI: {artifacts.ini_path}")
    for sno_path in artifacts.sno_paths:
        print(f"Generated SNO: {sno_path}")
    return 0


def _command_fetch_forcing(args: argparse.Namespace) -> int:
    site = _site_from_args(args)
    forcing = _forcing_from_args(args, site)
    workspace = create_workspace(args.workdir)
    result = build_forcing_dataframe(request=forcing, workspace=workspace)
    smet_path = create_smet_from_weather_data(weather_df=result.dataframe, output_path=result.smet_path, site=site)
    print(f"Provider: {result.provider}")
    print(f"SMET: {smet_path}")
    return 0


def _command_run_model(args: argparse.Namespace) -> int:
    workdir = Path(args.workdir).expanduser().resolve()
    ini_path = workdir / "config" / f"{args.station_id}.ini"
    stdout = run_snowpack(
        ini_path=ini_path,
        end_date=args.snowpack_end_date,
        snowpack_executable=args.snowpack_executable,
    )
    profile_files, bundle_path = bundle_profiles(workdir / "config" / "output", workdir / "snowpack_profiles.zip")
    print(stdout)
    if bundle_path is not None:
        print(f"Bundle: {bundle_path}")
        print(f"Profiles: {len(profile_files)}")
    return 0


def _command_smoke(args: argparse.Namespace) -> int:
    site = _site_from_args(args)
    slopes = _slopes_from_args(args)
    snowpack = _snowpack_from_args(args)
    workspace = create_workspace(args.workdir)

    artifacts = generate_config_files(site=site, slopes=slopes, snowpack=snowpack, workspace=workspace)
    synthetic = build_synthetic_weather_dataframe(args.start_date, hours=args.hours)
    smet_path = create_smet_from_weather_data(
        weather_df=synthetic,
        output_path=workspace.input_dir / f"{site.station_id}.smet",
        site=site,
    )
    print(f"Generated synthetic SMET: {smet_path}")
    print(f"Generated INI: {artifacts.ini_path}")

    if args.skip_model:
        return 0

    try:
        find_snowpack_executable(None)
    except FileNotFoundError:
        print("SNOWPACK executable not found; smoke run stopped after config and SMET generation.")
        return 0

    stdout = run_snowpack(
        ini_path=artifacts.ini_path,
        end_date=snowpack.snowpack_end_date,
    )
    profile_files, bundle_path = bundle_profiles(workspace.output_dir, workspace.bundle_path)
    print(stdout)
    if bundle_path is not None:
        print(f"Bundle: {bundle_path}")
        print(f"Profiles: {len(profile_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

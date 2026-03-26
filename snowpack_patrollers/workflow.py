from __future__ import annotations

from datetime import datetime, timedelta
from dataclasses import replace
from pathlib import Path

from .config import generate_config_files
from .forcing import build_forcing_dataframe, provider_supplies_measured_longwave, resolve_forcing_provider
from .models import ForcingRequest, SiteConfig, SlopeConfig, SnowpackConfig, WorkflowResult, WorkspacePaths
from .runner import bundle_profiles, run_snowpack
from .smet import create_smet_from_weather_data

DEFAULT_WORKDIR = ".snowpack_work"
DEFAULT_FORCING_BUFFER_HOURS = 48


def create_workspace(root: str | Path | None = None) -> WorkspacePaths:
    workspace_root = Path(root or DEFAULT_WORKDIR).expanduser().resolve()
    input_dir = workspace_root / "input"
    config_dir = workspace_root / "config"
    output_dir = config_dir / "output"
    cache_dir = workspace_root / "snodas_cache"
    bundle_path = workspace_root / "snowpack_profiles.zip"

    for path in (workspace_root, input_dir, config_dir, output_dir, cache_dir):
        path.mkdir(parents=True, exist_ok=True)

    return WorkspacePaths(
        root=workspace_root,
        input_dir=input_dir,
        config_dir=config_dir,
        output_dir=output_dir,
        cache_dir=cache_dir,
        bundle_path=bundle_path,
    )


def get_buffered_start_date(start_date: str, buffer_hours: int = DEFAULT_FORCING_BUFFER_HOURS) -> str:
    start_dt = datetime.fromisoformat(start_date)
    buffered = start_dt - timedelta(hours=buffer_hours)
    return buffered.date().isoformat()


def run_full_workflow(
    *,
    site: SiteConfig,
    slopes: SlopeConfig,
    snowpack: SnowpackConfig,
    forcing_request: ForcingRequest,
    workdir: str | Path | None = None,
    run_model: bool = True,
    snowpack_executable: str | None = None,
) -> WorkflowResult:
    workspace = create_workspace(workdir)
    provider = resolve_forcing_provider(forcing_request)
    effective_snowpack = replace(
        snowpack,
        meas_incoming_longwave=snowpack.meas_incoming_longwave or provider_supplies_measured_longwave(provider),
    )
    buffered_forcing_request = replace(
        forcing_request,
        start_date=get_buffered_start_date(forcing_request.start_date),
    )

    config_artifacts = generate_config_files(
        site=site,
        slopes=slopes,
        snowpack=effective_snowpack,
        workspace=workspace,
    )

    forcing_result = build_forcing_dataframe(
        request=buffered_forcing_request,
        workspace=workspace,
    )

    create_smet_from_weather_data(
        weather_df=forcing_result.dataframe,
        output_path=forcing_result.smet_path,
        site=site,
    )

    snowpack_stdout = ""
    profile_files = []
    bundle_path = None
    if run_model:
        snowpack_stdout = run_snowpack(
            ini_path=config_artifacts.ini_path,
            end_date=effective_snowpack.snowpack_end_date,
            snowpack_executable=snowpack_executable,
        )
        profile_files, bundle_path = bundle_profiles(workspace.output_dir, workspace.bundle_path)

    return WorkflowResult(
        provider=provider,
        workspace=workspace,
        ini_path=config_artifacts.ini_path,
        sno_paths=config_artifacts.sno_paths,
        smet_path=forcing_result.smet_path,
        profile_files=profile_files,
        bundle_path=bundle_path,
        forcing_metadata=forcing_result.metadata,
        snowpack_stdout=snowpack_stdout,
    )

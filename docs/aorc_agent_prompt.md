# Agent Prompt: Integrate AORC Forcing into SNOWPACKforPatrollers

Integrate NOAA AORC forcing into the SNOWPACKforPatrollers Colab workflow as an additional weather-model option while preserving the existing patroller-oriented UX.

1. Extend the "Install environment updates" cell so it also installs and imports the AWS/S3 tooling that the standalone AORC notebook relies on (`s3fs`, `xarray`, `h5netcdf`), and create a shared anonymous S3 filesystem handle (`s3fs.S3FileSystem(anon=True)`) alongside the current imports.

2. In the SMET-parameter form cell, add a new `@param` choice `aorc` to `model_selection`, labeling it to indicate the data is only available through 2024; keep the existing Colab form UX intact.

3. Lift the reusable AORC utilities from the dedicated notebook—`fetch_aorc_point_series`, `compute_relative_humidity`, `wind_from_components`, `cumulative_to_hourly`, and their supporting constants—and add them to the SMET handling cell. Adapt them to return a DataFrame in SMET-ready units with `timestamp`, `TA` (K), `RH` (fraction), `VW` (m/s), `DW` (deg), `ISWR`, optional `ILWR`, `PSUM`, and a placeholder `HS`. Reuse the existing SNODAS helper (`get_snodas_snow_depth`) for depth enrichment rather than duplicating that logic.

4. Update `create_smet_from_weather_data` so it automatically includes optional columns such as `ILWR` (inserted after `ISWR`) when they are present, keeping the current behavior for legacy fields unchanged.

5. Refactor the "Generate SMET Files" cell to recognise the new `aorc` option: add it to `valid_models`, branch to the new AORC fetcher instead of Open-Meteo, track HS units so the later conversion step skips the centimetre-to-metre division for AORC data, and write ILWR values if available. Gate the AORC branch with a check that `end_date` does not exceed 2024-12-31, surfacing a friendly error if the user requests newer data. Keep SNODAS integration, summaries, and SMET writing intact for the legacy models. Ensure that the AORC branch always sources HS values from the existing SNODAS workflow rather than the AORC forcing data itself.

6. Add a short markdown note near the model-selection form explaining that the AORC archive currently ends in 2024 so users understand the constraint when choosing that option.

7. When writing SMET files for the AORC option, always include the `ILWR` column immediately after `ISWR` to expose the longwave radiation forcing downstream.

⚠️ Tests not run (not requested).

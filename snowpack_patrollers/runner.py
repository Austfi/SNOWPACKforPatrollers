from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path


def find_snowpack_executable(explicit_path: str | None = None) -> str:
    if explicit_path:
        return explicit_path
    executable = shutil.which("snowpack")
    if executable is None:
        raise FileNotFoundError("SNOWPACK executable not found on PATH")
    return executable


def run_snowpack(
    *,
    ini_path: str | Path,
    end_date: str,
    snowpack_executable: str | None = None,
) -> str:
    ini_file = Path(ini_path).resolve()
    if not ini_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {ini_file}")

    executable = find_snowpack_executable(snowpack_executable)
    try:
        result = subprocess.run(
            [executable, "-c", str(ini_file), "-e", end_date],
            cwd=str(ini_file.parent),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        details: list[str] = [f"SNOWPACK failed with exit code {exc.returncode}."]
        if exc.stderr and exc.stderr.strip():
            details.append(f"SNOWPACK STDERR:\n{exc.stderr.strip()}")
        if exc.stdout and exc.stdout.strip():
            details.append(f"SNOWPACK STDOUT:\n{exc.stdout.strip()}")
        raise RuntimeError("\n\n".join(details)) from exc
    return result.stdout


def bundle_profiles(output_dir: str | Path, bundle_path: str | Path) -> tuple[list[Path], Path | None]:
    output_path = Path(output_dir)
    search_root = output_path.parent if output_path.name == "output" else output_path
    profile_files = sorted(
        path
        for path in search_root.rglob("*")
        if path.is_file() and path.suffix.lower() == ".pro"
    )
    if not profile_files:
        return [], None

    bundle = Path(bundle_path)
    bundle.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(bundle, "w") as archive:
        for profile in profile_files:
            archive.write(profile, profile.name)
    return profile_files, bundle

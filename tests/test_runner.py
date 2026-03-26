import subprocess
import zipfile

import pytest

from snowpack_patrollers.runner import bundle_profiles, run_snowpack


def test_run_snowpack_surfaces_stderr(tmp_path, monkeypatch):
    ini_path = tmp_path / "demo.ini"
    ini_path.write_text("[General]\n")

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["snowpack", "-c", str(ini_path)],
            output="starting snowpack",
            stderr="invalid config option",
        )

    monkeypatch.setattr("snowpack_patrollers.runner.find_snowpack_executable", lambda explicit_path: "snowpack")
    monkeypatch.setattr("snowpack_patrollers.runner.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="invalid config option"):
        run_snowpack(ini_path=ini_path, end_date="2024-03-03T23:00")


def test_bundle_profiles_finds_recursive_case_insensitive_profiles(tmp_path):
    config_dir = tmp_path / "config"
    output_dir = config_dir / "output"
    output_dir.mkdir(parents=True)
    lower = output_dir / "demo_res.pro"
    upper = config_dir / "demo_flat_res.PRO"
    lower.write_text("lower")
    upper.write_text("upper")

    profiles, bundle_path = bundle_profiles(output_dir, tmp_path / "profiles.zip")

    assert [path.name for path in profiles] == ["demo_flat_res.PRO", "demo_res.pro"]
    assert bundle_path == (tmp_path / "profiles.zip")
    with zipfile.ZipFile(bundle_path) as archive:
        assert sorted(archive.namelist()) == ["demo_flat_res.PRO", "demo_res.pro"]

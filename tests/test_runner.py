import subprocess

import pytest

from snowpack_patrollers.runner import run_snowpack


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

from pathlib import Path

from snowpack_patrollers.cli import main


def test_smoke_command_generates_local_workdir(tmp_path):
    exit_code = main(
        [
            "smoke",
            "--workdir",
            str(tmp_path / "smoke"),
            "--station-id",
            "cli_demo",
            "--hours",
            "24",
            "--skip-model",
        ]
    )

    workdir = Path(tmp_path / "smoke")
    assert exit_code == 0
    assert (workdir / "input" / "cli_demo.smet").exists()
    assert (workdir / "config" / "cli_demo.ini").exists()

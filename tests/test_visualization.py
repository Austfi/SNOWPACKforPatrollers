from pathlib import Path

import pytest

from snowpack_patrollers.visualization import render_pro_plot, select_profile_file, select_snapshot_index


def test_select_profile_file_validates_presence(tmp_path):
    profile = tmp_path / "demo.pro"
    profile.write_text("test")

    selected = select_profile_file([profile], profile_file_index=0)

    assert selected == profile.resolve()


def test_select_profile_file_rejects_bad_index(tmp_path):
    profile = tmp_path / "demo.pro"
    profile.write_text("test")

    with pytest.raises(IndexError, match="between 0 and 0"):
        select_profile_file([profile], profile_file_index=1)


def test_select_snapshot_index_supports_expected_modes():
    assert select_snapshot_index(5, "first") == 0
    assert select_snapshot_index(5, "middle") == 2
    assert select_snapshot_index(5, "latest") == 4


def test_render_pro_plot_rejects_unsupported_mode(tmp_path):
    profile = tmp_path / "demo.pro"
    profile.write_text("test")

    with pytest.raises(ValueError, match="Unsupported plot mode"):
        render_pro_plot(profile, plot_mode="bad-mode")  # type: ignore[arg-type]

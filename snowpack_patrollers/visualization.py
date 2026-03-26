from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Sequence

PlotMode = Literal["profile", "timeline"]
Snapshot = Literal["first", "middle", "latest"]


def _load_snowpat():
    try:
        from snowpat import SnowLense as sl
        from snowpat import snowpackreader as spr
    except ImportError as exc:
        raise ImportError("Install `snowpat` to visualize SNOWPACK .pro files in the notebook.") from exc
    return spr, sl


def select_profile_file(profile_files: Sequence[str | Path], profile_file_index: int = 0) -> Path:
    if not profile_files:
        raise ValueError("No .pro files are available. Run the model first.")
    if profile_file_index < 0 or profile_file_index >= len(profile_files):
        raise IndexError(f"profile_file_index must be between 0 and {len(profile_files) - 1}.")
    return Path(profile_files[profile_file_index]).expanduser().resolve()


def select_snapshot_index(total_profiles: int, snapshot: Snapshot = "latest") -> int:
    if total_profiles <= 0:
        raise ValueError("No profiles are available inside the .pro file.")
    if snapshot == "first":
        return 0
    if snapshot == "middle":
        return total_profiles // 2
    if snapshot == "latest":
        return total_profiles - 1
    raise ValueError(f"Unsupported snapshot selection: {snapshot}")


def render_pro_plot(
    profile_path: str | Path,
    *,
    plot_mode: PlotMode = "profile",
    snapshot: Snapshot = "latest",
    discard_below_ground: bool = True,
) -> dict[str, Any]:
    if plot_mode not in {"profile", "timeline"}:
        raise ValueError(f"Unsupported plot mode: {plot_mode}")

    profile_file = Path(profile_path).expanduser().resolve()
    if not profile_file.exists():
        raise FileNotFoundError(f"Profile file not found: {profile_file}")

    spr, sl = _load_snowpat()
    reader = spr.readPRO(str(profile_file))
    if discard_below_ground and hasattr(reader, "discard_below_ground"):
        reader.discard_below_ground(discard=True)

    dates = list(reader.get_all_dates())
    selected_date = None
    plotter = None

    if plot_mode == "timeline":
        plot_result = sl.plot(reader)
        if isinstance(plot_result, tuple):
            figure, plotter = plot_result
        else:
            figure = plot_result
        if dates:
            selected_date = dates[-1]
    else:
        snapshot_index = select_snapshot_index(len(dates), snapshot)
        profile = reader.get_profile_nr(snapshot_index)
        plot_result = sl.plotProfile(profile)
        if isinstance(plot_result, tuple):
            figure, plotter = plot_result
        else:
            figure = plot_result
        selected_date = dates[snapshot_index]

    return {
        "profile_path": profile_file,
        "dates": dates,
        "selected_date": selected_date,
        "figure": figure,
        "plotter": plotter,
    }


def show_snowpat_figure(figure: Any) -> None:
    _, sl = _load_snowpat()
    sl.show_figure(figure)

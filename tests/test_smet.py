import pandas as pd

from snowpack_patrollers.models import SiteConfig
from snowpack_patrollers.smet import create_smet_from_weather_data


def test_create_smet_writes_ilwr_after_iswr(tmp_path):
    site = SiteConfig(
        station_id="demo",
        station_name="Demo",
        latitude=39.7,
        longitude=-105.8,
        altitude_meters=3200.0,
    )
    dataframe = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-11-01T00:00:00"]),
            "TA": [273.15],
            "RH": [0.75],
            "TSG": [273.15],
            "VW": [4.0],
            "DW": [225.0],
            "ISWR": [100.0],
            "ILWR": [250.0],
            "PSUM": [0.5],
            "HS": [0.4],
        }
    )

    path = create_smet_from_weather_data(weather_df=dataframe, output_path=tmp_path / "demo.smet", site=site)
    text = path.read_text()

    assert "fields = timestamp TA RH TSG VW DW ISWR ILWR PSUM HS" in text


def test_create_smet_writes_without_ilwr_when_not_present(tmp_path):
    site = SiteConfig(
        station_id="demo",
        station_name="Demo",
        latitude=39.7,
        longitude=-105.8,
        altitude_meters=3200.0,
    )
    dataframe = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-11-01T00:00:00"]),
            "TA": [273.15],
            "RH": [0.75],
            "VW": [4.0],
            "DW": [225.0],
            "ISWR": [100.0],
            "PSUM": [0.5],
        }
    )

    path = create_smet_from_weather_data(weather_df=dataframe, output_path=tmp_path / "demo.smet", site=site)
    text = path.read_text()

    assert "fields = timestamp TA RH TSG VW DW ISWR PSUM HS" in text

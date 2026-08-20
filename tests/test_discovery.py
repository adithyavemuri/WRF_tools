from datetime import datetime

from wrf_tools.io import discover_wrfout


def test_discover_filters_domain_and_time(tmp_path):
    for name in (
        "wrfout_d01_2024-01-01_00_00_00",
        "wrfout_d02_2024-01-01_00_00_00",
        "wrfout_d02_2024-01-02_00_00_00",
        "not_wrf_output.nc",
    ):
        (tmp_path / name).touch()
    result = discover_wrfout(
        tmp_path,
        domain="d02",
        end=datetime(2024, 1, 1, 12),
    )
    assert [path.name for path in result] == ["wrfout_d02_2024-01-01_00_00_00"]

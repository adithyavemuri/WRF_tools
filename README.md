# WRF Tools

`wrf-tools` is a general-purpose Python package for inspecting and processing
WRF and WRF-LES output, preparing WPS workflows, and coupling WRF-LES wind
planes to TurbSim/OpenFAST.

The package is being rebuilt from the preserved scripts under
`source_collections/`. New modules do not contain machine-specific paths,
fixed case names, fixed grid sizes, or fixed time ranges.

## Install for development

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
```

## Examples

```python
from wrf_tools.io import discover_wrfout
from wrf_tools.diagnostics import wind_speed, wind_direction

files = discover_wrfout("path/to/run", domain="d03")
speed = wind_speed(u, v)
direction = wind_direction(u, v)
```

Create a TurbSim/OpenFAST full-field wind file:

```python
from wrf_tools.coupling.openfast import WindField, write_bts

field = WindField(
    velocity=velocity,  # (time, vertical, lateral, component)
    dy=10.0,
    dz=10.0,
    dt=0.1,
    hub_height=120.0,
    bottom_height=10.0,
)
write_bts("inflow.bts", field)
```

Use `wrf-tools --help` for command-line operations.

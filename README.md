# WRF Tools

`wrf-tools` is a general-purpose Python package for inspecting and processing
WRF/WRF-LES output, managing small WPS workflows, and creating TurbSim/OpenFAST
full-field wind files. Its APIs use configurable variables, dimensions, and
paths rather than case-specific values.

## Capabilities

- **WRF I/O:** discover, open, inspect, validate, and access NetCDF variables.
- **Grid operations:** destagger fields, find nearest cells, geographic subsets,
  and vertical interpolation.
- **Wind and turbulence:** speed/direction, component conversion, fluctuations,
  Reynolds stresses, turbulence intensity, and resolved/total TKE.
- **WRF-LES:** configurable velocity loading, native-grid destaggering, and
  turbulent flux calculation.
- **OpenFAST coupling:** map arbitrary WRF-LES wind-plane layouts and read,
  write, or validate TurbSim/OpenFAST `.bts` files.
- **Workflow helpers:** read/write WRF `tslist` files, edit WPS namelist dates,
  use typed configuration objects, and run command-line inspection tools.

COAWST functionality and case-specific installation/HPC automation are outside
the package scope.

## Installation

For development from a local clone:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[netcdf,test]"
```

## Quick examples

### Find and inspect WRF output

```python
from wrf_tools.io import discover_wrfout, get_variable, open_wrf

files = discover_wrfout("path/to/wrf/run", domain="d03", recursive=True)

with open_wrf(files[0]) as ds:
    temperature = get_variable(ds, "T", time=0)
    print(ds.sizes)
    print(temperature.shape)
```

The same operations are available from the command line:

```powershell
wrf-tools discover "path/to/wrf/run" --domain d03 --recursive
wrf-tools inspect "path/to/wrfout_d03_2024-01-01_00_00_00"
```

### Calculate wind and turbulence diagnostics

```python
from wrf_tools.diagnostics import resolved_tke, turbulence_intensity, wind_direction, wind_speed

speed = wind_speed(u, v)
direction = wind_direction(u, v)
tke = resolved_tke(u, v, w, axis=0)
ti = turbulence_intensity(speed, axis=0)
```

### Load native WRF-LES velocity fields

```python
from wrf_tools.io import open_wrf
from wrf_tools.les import calculate_fluxes, calculate_total_tke, load_velocity

with open_wrf("wrfout_d01_2024-01-01_00_00_00") as ds:
    u, v, w = load_velocity(ds)  # U, V, and W are destaggered automatically
    fluxes = calculate_fluxes(u, v, w, axis=0)
    total_tke = calculate_total_tke(u, v, w, subgrid_tke=ds.get("TKE"), axis=0)
```

Variable names can be remapped with
`load_velocity(ds, names={"u": "my_u", "v": "my_v", "w": "my_w"})`.

### Locate a grid cell

```python
from wrf_tools.grid import nearest_grid_point

point = nearest_grid_point(
    ds["XLAT"].isel(Time=0),
    ds["XLONG"].isel(Time=0),
    target_latitude=52.0,
    target_longitude=4.3,
)
print(point.x, point.y)
```

### Create an OpenFAST `.bts` wind file

```python
from wrf_tools.coupling.openfast import wind_field_from_components, write_bts

# Each component is a 3-D array; its axis order is declared explicitly.
field = wind_field_from_components(
    u_plane,
    v_plane,
    w_plane,
    time_axis=0,
    vertical_axis=1,
    lateral_axis=2,
    dy=10.0,
    dz=10.0,
    dt=0.1,
    hub_height=120.0,
    bottom_height=10.0,
)
write_bts("inflow.bts", field)
```

Inspect the generated file with:

```powershell
wrf-tools bts-info inflow.bts
```

## Tests

```powershell
python -m pytest
```

# Installation and optional tools

The normal toolkit, connected report and synthetic showcase need no WRF build,
compiler, administrator access or system-package changes. Use an isolated Python
environment. CI targets Python 3.10 and 3.12; optional native extensions may have
additional platform/version restrictions.

## Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[netcdf,science,plot,report,animation]"
```

## Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[netcdf,science,plot,report,animation]"
```

Alternatively install `requirements.txt`, then `pip install -e . --no-deps`.
That file includes Cartopy, Pillow and the Python-3.10 TOML dependency.

## Optional tools are not mandatory toolkit dependencies

- `wrf-python`: only for users wanting its external API; not required by the
  report, algorithms or showcase. Its source installation can need compatible
  compilers/NetCDF libraries. Do not install it just to run these examples.
- Manim: separate optional scene renderer; follow [the visualization
  guide](VISUALIZATION.md). Native graphics/text libraries can be required.
- FFmpeg: needed for MP4, not the Pillow GIF examples.
- `wgrib2`: required only when explicitly selecting GRIB conversion.
- OpenFAST: required only to execute a real, complete turbine model.
- Natural Earth map features: downloaded into Cartopy's user cache on first
  report use, or explicitly with `wrf-tools setup-maps --resolution 50m`.
  Set `WRF_TOOLS_OFFLINE_MAPS=1` for cache-only behavior; absent features use a
  visible bundled-raster fallback. The synthetic showcase uses cache-only mode.

No installer here invokes a system package manager. If a native dependency
cannot be installed without administrator access on your platform, use an
existing user-managed environment or omit that optional tool.

## Check the environment

```bash
wrf-tools doctor
wrf-tools doctor --core-only
wrf-tools doctor --json
```

Optional tools being absent does not mean the core toolkit failed.

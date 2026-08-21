# Prerequisites and platform notes

WRF Tools requires Python 3.10 or newer. Python 3.10-3.12 is recommended when
using `wrf-python`, because native-extension availability can lag behind the
newest Python release.

## Linux

The core package and most extras install from Python wheels. Debian/Ubuntu
users who need `wrf-python` can install its native build prerequisites with:

```bash
sudo apt-get update
sudo apt-get install -y build-essential gfortran libnetcdf-dev libhdf5-dev
```

Create an isolated environment and install the complete stack:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

Install native WRF and Cartopy integration only when needed:

```bash
python -m pip install -r requirements-wrf.txt
```

## Windows

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

## Verify the environment

```bash
wrf-tools doctor
wrf-tools doctor --json
```

The command distinguishes required dependencies from optional capabilities
and includes the underlying import error when a compiled library is missing.

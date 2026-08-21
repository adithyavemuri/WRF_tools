"""Non-destructive batch post-processing workflows."""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
from .io import open_wrf_sequence

def aggregate_wrf(paths, *, variables=None, output=None, load=False):
    """Combine compatible sequential WRF files and optionally export them."""
    dataset=open_wrf_sequence(paths)
    if variables is not None: dataset=dataset[list(variables)]
    if load: dataset.load()
    if output is not None: dataset.to_netcdf(output)
    return dataset

def archive_outputs(paths, directory, *, overwrite=False):
    """Copy completed outputs to an archive; source files are never deleted."""
    destination=Path(directory); destination.mkdir(parents=True,exist_ok=True); copied=[]
    for item in paths:
        source=Path(item); target=destination/source.name
        if target.exists() and not overwrite: raise FileExistsError(target)
        shutil.copy2(source,target); copied.append(target)
    return copied

def convert_grib_to_netcdf(source, output, *, executable="wgrib2", extra_args=()):
    """Run an explicitly configured wgrib2 conversion and verify its output."""
    source,output=Path(source),Path(output)
    command=[str(executable),str(source),"-netcdf",str(output),*map(str,extra_args)]
    completed=subprocess.run(command,check=True,capture_output=True,text=True)
    if not output.exists(): raise RuntimeError("converter completed without creating the requested output")
    return output,completed

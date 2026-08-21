"""OpenFAST output post-processing (independent of controller tuning)."""
from __future__ import annotations
from pathlib import Path
import struct
import subprocess
import numpy as np
import xarray as xr

def read_ascii_output(path):
    """Read a conventional OpenFAST whitespace-delimited ASCII output."""
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    header = next((i for i, line in enumerate(lines) if line.strip().split() and line.strip().split()[0].lower() == "time"), None)
    if header is None or header + 2 > len(lines):
        raise ValueError("OpenFAST channel header was not found")
    names = lines[header].split()
    units = [unit.strip("()[]") for unit in lines[header+1].split()]
    data = np.loadtxt(lines[header+2:])
    return xr.Dataset({name: ("time", data[:, i], {"units": units[i] if i < len(units) else ""}) for i, name in enumerate(names[1:], 1)}, coords={"time": data[:, 0]})

def read_binary_output(path):
    """Read the packed OpenFAST binary output formats with/without time."""
    with Path(path).open("rb") as stream:
        file_id, channels, nt = struct.unpack("<hii", stream.read(10))
        if file_id not in (1, 2): raise ValueError(f"unsupported OpenFAST binary format {file_id}")
        time_a, time_b = struct.unpack("<dd", stream.read(16))
        slopes = np.frombuffer(stream.read(4*channels), dtype="<f4").astype(float)
        offsets = np.frombuffer(stream.read(4*channels), dtype="<f4").astype(float)
        (description_length,) = struct.unpack("<i", stream.read(4))
        description = stream.read(description_length).decode("utf-8", errors="replace")
        names = [stream.read(10).decode("ascii", errors="replace").strip() for _ in range(channels+1)]
        units = [stream.read(10).decode("ascii", errors="replace").strip().strip("()[]") for _ in range(channels+1)]
        if file_id == 1:
            packed_time = np.frombuffer(stream.read(4*nt), dtype="<i4").astype(float)
            time = (packed_time-time_b)/time_a
        else:
            time = time_a+time_b*np.arange(nt)
        packed = np.frombuffer(stream.read(2*nt*channels), dtype="<i2").reshape(nt, channels)
    values = (packed-offsets)/slopes
    return xr.Dataset({names[i+1] or f"channel_{i+1}": ("time", values[:,i], {"units":units[i+1]}) for i in range(channels)}, coords={"time":time}, attrs={"description":description,"file_id":file_id})

def zero_crossing_frequency(signal, sample_rate):
    values = np.asarray(signal, float)-np.nanmean(signal)
    crossings = np.count_nonzero(np.diff(np.signbit(values)))
    return crossings*sample_rate/(2*values.size)

def stress_from_moment(moment, distance_to_centroid, moment_of_inertia):
    return np.asarray(moment)*distance_to_centroid/moment_of_inertia

def rainflow_cycles(signal):
    """Return cycle ranges/counts using the ASTM four-point stack method."""
    values = np.asarray(signal, float).ravel()
    reversals = values[np.r_[True, np.diff(np.sign(np.diff(values))) != 0, True]]
    stack, cycles = [], []
    for value in reversals:
        stack.append(value)
        while len(stack) >= 3 and abs(stack[-2]-stack[-3]) <= abs(stack[-1]-stack[-2]):
            amplitude = abs(stack[-2]-stack[-3])
            count = 0.5 if len(stack) == 3 else 1.0
            cycles.append((amplitude, count))
            if len(stack) == 3:
                stack.pop(0)
            else:
                stack[-3:-1] = []
    cycles.extend((abs(stack[i+1]-stack[i]), 0.5) for i in range(len(stack)-1))
    return np.asarray(cycles, float).reshape(-1, 2)

def channel_statistics(dataset):
    """Return min/mean/max/std for every numeric OpenFAST channel."""
    return {name:{"minimum":float(data.min()),"mean":float(data.mean()),"maximum":float(data.max()),"standard_deviation":float(data.std())} for name,data in dataset.data_vars.items() if np.issubdtype(data.dtype,np.number)}

def compare_outputs(first, second, *, channels=None):
    """Align two OpenFAST datasets and compare selected channels."""
    from .validation import comparison_summary
    a,b=xr.align(first,second,join="inner"); selected=channels or sorted(set(a.data_vars)&set(b.data_vars))
    return {name:comparison_summary(a[name].values,b[name].values) for name in selected}

def run_openfast(input_file, *, executable="openfast", working_directory=None, timeout=None):
    """Run OpenFAST explicitly and return captured process information."""
    source=Path(input_file); cwd=Path(working_directory) if working_directory else source.parent
    completed=subprocess.run([str(executable),source.name],cwd=cwd,check=True,capture_output=True,text=True,timeout=timeout)
    return completed

"""Thin, explicit TOML chains for any cataloged WRF_tools function.

No eval, shell commands, automatic external simulations, or scientific inference.
Recipe functions can write files/run tools when explicitly selected: review
recipes before execution. This is not a sandbox for untrusted recipes.
"""
from __future__ import annotations

from contextlib import ExitStack
import dataclasses
import json
from pathlib import Path
import re

import numpy as np

from .capabilities import get_capability


class _UnavailableResult(Exception):
    pass


def _references(value):
    if isinstance(value, dict):
        if "ref" in value:
            yield value["ref"]
        for item in value.values():
            yield from _references(item)
    elif isinstance(value, list):
        for item in value:
            yield from _references(item)


def _summary(value):
    if isinstance(value, np.ndarray):
        return dict(type="array", shape=list(value.shape), dtype=str(value.dtype))
    if hasattr(value, "sizes"):
        return dict(type=type(value).__name__, dimensions=dict(value.sizes))
    if dataclasses.is_dataclass(value):
        return dict(type=type(value).__name__, fields=[item.name for item in dataclasses.fields(value)])
    if isinstance(value, dict):
        return {str(key): _summary(item) for key,item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_summary(item) for item in value]
    if isinstance(value, (str, bool, int, type(None))):
        return value
    if isinstance(value, (complex, np.complexfloating)):
        return dict(real=_summary(float(value.real)),imag=_summary(float(value.imag)))
    if isinstance(value, (float, np.number)):
        return value.item() if isinstance(value, np.number) and np.isfinite(value) else (value if np.isfinite(value) else None)
    if isinstance(value, Path):
        return str(value)
    return dict(type=type(value).__name__)


def _resolve(value, results, base, output):
    if isinstance(value, list):
        return [_resolve(item, results, base, output) for item in value]
    if not isinstance(value, dict):
        return value
    if set(value)=={"slice"}:
        return slice(*value["slice"])
    if "ref" in value:
        if value["ref"] not in results:
            raise _UnavailableResult(value["ref"])
        item = results[value["ref"]]
        for part in value.get("path", []):
            if isinstance(part, int) or isinstance(item, dict):
                item = item[part]
            elif isinstance(part, str) and not part.startswith("_"):
                item = getattr(item, part)
            else:
                raise ValueError("References select only public attributes or indexed items")
        if "variable" in value:
            item = item[value["variable"]]
        if "isel" in value:
            item = item.isel(value["isel"])
        if "sel" in value:
            item = item.sel(value["sel"])
        if value.get("array", False):
            item = np.asarray(item)
        return item
    if set(value) == {"file"}:
        path=(base / Path(value["file"]).expanduser()).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Input path does not exist: {path}")
        return path
    if set(value) == {"output"}:
        return _output_path(output, value["output"])
    if "type" in value:
        from .types import GeoBounds, GridPoint, Station, WindField
        classes = {cls.__name__: cls for cls in (GeoBounds, GridPoint, Station, WindField)}
        if value["type"] not in classes:
            raise ValueError("Unsupported recipe data type")
        return classes[value["type"]](**_resolve(value.get("kwargs", {}), results, base, output))
    return {name: _resolve(item, results, base, output) for name,item in value.items()}


def _output_path(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Output references must stay inside the selected output directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _save(value, path):
    if hasattr(value, "to_netcdf"):
        value.to_netcdf(path)
    elif hasattr(value, "savefig"):
        value.savefig(path, dpi=180, bbox_inches="tight")
    elif isinstance(value, (tuple, list)) and value and hasattr(value[0], "savefig"):
        value[0].savefig(path, dpi=180, bbox_inches="tight")
    elif hasattr(value,"save") and type(value).__module__.startswith("matplotlib.animation"):
        value.save(str(path))
    elif isinstance(value, np.ndarray):
        if path.suffix != ".npy":
            raise ValueError("Array results need a .npy save target")
        np.save(path, value)
    elif isinstance(value, dict) and path.suffix == ".npz":
        np.savez(path, **value)
    else:
        path.write_text(json.dumps(_summary(value), indent=2, allow_nan=False)+"\n")


def run_recipe(path, output_directory, *, force=False):
    """Execute explicit steps, retain result references, save a status manifest.

    Each step has id, call, args/kwargs, optional save, and optional enabled/reason.
    Missing-input skips require explicit optional=true; calculation errors fail
    with a saved diagnostic. Downstream missing references are recorded as skipped.
    Paths use {file='...'} relative to the TOML, or {output='...'} under output.
    """
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib
    path = Path(path).expanduser().resolve()
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    steps = config.get("steps", [])
    if not steps:
        raise ValueError("Recipe requires one or more [[steps]]")
    ids = [step.get("id", "") for step in steps]
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name) for name in ids):
        raise ValueError("Step IDs must be unique, simple nonempty names")
    previous=set()
    for step in steps:
        missing=set(_references(step))-previous
        if missing:
            raise ValueError(f"{step['id']}: unknown or forward references {sorted(missing)}")
        previous.add(step["id"])
    # Validate all requested function names before any step executes.
    functions = {step["id"]: get_capability(step["call"]) for step in steps}
    output = Path(output_directory).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = output / "analysis-manifest.json"
    if manifest.exists() and not force:
        raise FileExistsError(f"{manifest} exists; use a new output folder or --force")
    report = dict(recipe=path.name, status="RUNNING", steps=[])
    results = {}
    try:
        with ExitStack() as resources:
            for step in steps:
                record = dict(id=step["id"], call=step["call"], parameters=step)
                if not step.get("enabled", True):
                    record.update(status="SKIPPED", reason=step.get("reason", "Disabled by the researcher"))
                    report["steps"].append(record); continue
                try:
                    args = _resolve(step.get("args", []), results, path.parent, output)
                    kwargs = _resolve(step.get("kwargs", {}), results, path.parent, output)
                    value = functions[step["id"]](*args, **kwargs)
                    if hasattr(value, "close") and callable(value.close):
                        resources.callback(value.close)
                    figure=value[0] if isinstance(value,(list,tuple)) and value else value
                    if hasattr(figure,"savefig"):
                        import matplotlib.pyplot as plt
                        resources.callback(plt.close,figure)
                    results[step["id"]] = value
                    if "save" in step:
                        target = _output_path(output, step["save"])
                        _save(value, target); record["artifact"] = target.name
                    record.update(status="COMPLETE", result=_summary(value))
                except _UnavailableResult as exc:
                    record.update(status="SKIPPED", reason=f"Required prior result unavailable: {exc}")
                    report["steps"].append(record); continue
                except (FileNotFoundError, KeyError, ImportError) as exc:
                    record.update(status="SKIPPED" if step.get("optional", False) else "FAILED", reason=str(exc))
                    report["steps"].append(record)
                    if record["status"] == "FAILED":
                        raise
                    continue
                except Exception as exc:
                    record.update(status="FAILED", reason=f"{type(exc).__name__}: {exc}")
                    report["steps"].append(record); raise
                report["steps"].append(record)
        report["status"] = "COMPLETE_WITH_SKIPS" if any(item["status"]=="SKIPPED" for item in report["steps"]) else "COMPLETE"
    except Exception:
        report["status"] = "FAILED"
        raise
    finally:
        manifest.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    return manifest

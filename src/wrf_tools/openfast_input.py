"""Minimal lossless editing of labelled OpenFAST text parameters."""
from __future__ import annotations
from pathlib import Path
import re

_LINE = re.compile(r'^(?P<prefix>\s*)(?P<value>"[^"]*"|\S+)(?P<space>\s+)(?P<label>[A-Za-z][A-Za-z0-9_]*)(?P<rest>.*)$')

def read_parameters(path):
    result={}
    for line in Path(path).read_text(encoding="utf-8",errors="replace").splitlines():
        match=_LINE.match(line)
        if match: result[match.group("label")]=match.group("value").strip('"')
    return result

def update_parameters(path, values, *, output=None):
    source=Path(path); lines=source.read_text(encoding="utf-8",errors="replace").splitlines(); found=set(); updated=[]
    for line in lines:
        match=_LINE.match(line)
        if match and match.group("label") in values:
            label=match.group("label"); value=values[label]; rendered=f'"{value}"' if isinstance(value,str) and (" " in value or match.group("value").startswith('"')) else str(value)
            line=f'{match.group("prefix")}{rendered}{match.group("space")}{label}{match.group("rest")}'; found.add(label)
        updated.append(line)
    missing=set(values)-found
    if missing: raise KeyError(f"OpenFAST parameters not found: {', '.join(sorted(missing))}")
    target=Path(output) if output else source; target.write_text("\n".join(updated)+"\n",encoding="utf-8"); return target

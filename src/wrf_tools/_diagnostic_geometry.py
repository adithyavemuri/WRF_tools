"""Physical-coordinate diagnostics for the optional offline viewer.

Velocity gradients are reconstructed by the chain rule on the full native
mass grid before display subsampling. A spherical Earth embedding accounts
for column slopes, nonuniform heights and changing local wind basis. This is
a diagnostic reconstruction, NOT WRF's discrete dynamical operator or LES
validation. See docs/ISOSURFACES.md for derivation and limitations.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


_DEFINITIONS = {
    "wind_speed": ("Horizontal wind speed", "m s-1", False,
        "hypot(mass-grid U, mass-grid V); not turbulence intensity", ("U", "V")),
    "vertical_velocity": ("Vertical velocity", "m s-1", True,
        "Mass-grid W; positive up, negative down; NOT a turbulent flux", ("W",)),
    "vertical_vorticity": ("Vertical relative vorticity", "s-1", True,
        "Radial component of curl of Earth-relative velocity; excludes planetary vorticity",
        ("U", "V", "W", "COSALPHA", "SINALPHA")),
    "q_criterion": ("Q criterion", "s-2", True,
        "0.5*(||Omega||^2-||S||^2); positive means rotation dominates strain, not a turbulence/energy budget",
        ("U", "V", "W", "COSALPHA", "SINALPHA")),
    "model_tke": ("Model-provided TKE", "m2 s-2", False,
        "Supported model energy only; NOT resolved or total TKE", ()),
}

_DERIVATIVE_METHOD = (
    "Full mass-grid finite differences in native indices; chain-rule Jacobian of "
    "spherical Earth Cartesian positions (XLAT, XLONG, MSL height); grid U/V rotated "
    "using COSALPHA/SINALPHA and local east/north/up basis before differentiation. "
    "One-sided boundary differences; not WRF's discrete dynamical operator. "
    "Spherical geometric embedding, not an ellipsoidal or shallow-atmosphere stencil."
)


def _basis(latitude, longitude):
    """Return Earth-fixed Cartesian local east, north and radial unit vectors."""
    lat, lon = np.deg2rad(latitude), np.deg2rad(longitude)
    east = np.stack((-np.sin(lon), np.cos(lon), np.zeros_like(lat)), axis=-1)
    north = np.stack((-np.sin(lat)*np.cos(lon), -np.sin(lat)*np.sin(lon), np.cos(lat)), axis=-1)
    up = np.stack((np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)), axis=-1)
    return east, north, up


def _cartesian_gradient(positions, velocity):
    """Return d velocity_a / d physical_position_b via dV/di * (dX/di)^-1.

    positions/velocity: finite (k,j,i,3). Central index differences inside,
    first-order one-sided differences at boundaries. Singular geometry is an
    error, not a license to silently use nominal DX/DY.
    """
    positions, velocity = np.asarray(positions, float), np.asarray(velocity, float)
    if positions.shape != velocity.shape or positions.ndim != 4 or positions.shape[-1] != 3 or min(positions.shape[:3]) < 2:
        raise ValueError("Position and velocity need matching (k,j,i,3) shapes, at least two cells per axis")
    if not np.isfinite(positions).all() or not np.isfinite(velocity).all():
        raise ValueError("Missing physical-coordinate/velocity samples are not filled")
    jacobian = np.stack(np.gradient(positions, axis=(0,1,2), edge_order=1), axis=-1)
    dv = np.stack(np.gradient(velocity, axis=(0,1,2), edge_order=1), axis=-1)
    scales = np.prod(np.linalg.norm(jacobian, axis=-2), axis=-1)
    if np.any(np.abs(np.linalg.det(jacobian)) <= 1e-8*scales) or np.any(scales == 0):
        raise ValueError("Singular or nearly coplanar physical grid; derivatives are undefined")
    return np.swapaxes(np.linalg.solve(np.swapaxes(jacobian,-1,-2), np.swapaxes(dv,-1,-2)), -1,-2)


def _invariants(gradient, up):
    """Q convention and radial relative vorticity from one physical tensor."""
    strain = .5*(gradient+np.swapaxes(gradient,-1,-2))
    rotation = .5*(gradient-np.swapaxes(gradient,-1,-2))
    q = .5*(np.sum(rotation**2,axis=(-2,-1))-np.sum(strain**2,axis=(-2,-1)))
    curl = np.stack((gradient[...,2,1]-gradient[...,1,2],
                     gradient[...,0,2]-gradient[...,2,0],
                     gradient[...,1,0]-gradient[...,0,1]), axis=-1)
    return q, np.sum(curl*up, axis=-1)


def _physical_diagnostics(frame, u, v, w, heights, radius):
    """Reconstruct velocity derivatives in a fixed Cartesian spherical frame."""
    lat, lon = np.asarray(frame.XLAT), np.asarray(frame.XLONG)
    cosine, sine = np.asarray(frame.COSALPHA), np.asarray(frame.SINALPHA)
    if not np.isfinite([cosine,sine,lat,lon]).all() or np.any(np.abs(lat) > 90):
        raise ValueError("Nonfinite/invalid geographic coordinates or wind rotation")
    if not np.allclose(cosine*cosine+sine*sine,1.,atol=2e-5):
        raise ValueError("COSALPHA/SINALPHA do not form unit rotations")
    east, north, up = _basis(lat,lon)
    positions = (radius+heights)[...,None]*up
    earth_u, earth_v = u*cosine-v*sine, v*cosine+u*sine
    velocity = earth_u[...,None]*east+earth_v[...,None]*north+w[...,None]*up
    return _invariants(_cartesian_gradient(positions,velocity),up)


def _sample(array, rows, columns):
    return np.asarray(array)[:,rows][:,:,columns]


def _export_diagnostics(run_directory, output, *, domain, diagnostics, top_metres,
        horizontal_stride, vertical_exaggeration, maximum_frames, maximum_faces,
        tke_source, earth_radius_metres):
    from .grid import destagger
    from .io import discover_wrfout, open_wrf_sequence
    from .isosurfaces import _indices, _terrain, isosurface_mesh
    from .turbulence import model_tke
    from .visualization import history_times, mass_heights

    if not isinstance(diagnostics,dict) or not diagnostics or set(diagnostics)-set(_DEFINITIONS):
        raise ValueError("diagnostics needs a nonempty name: thresholds mapping; supported: "+", ".join(_DEFINITIONS))
    for name, levels in diagnostics.items():
        a = np.asarray(levels,float)
        if a.ndim != 1 or not a.size or not np.isfinite(a).all() or np.any(np.diff(a) <= 0):
            raise ValueError(f"{name}: thresholds must be finite, nonempty and strictly increasing")
    for name, value in (("horizontal_stride",horizontal_stride),("maximum_faces",maximum_faces)):
        if isinstance(value,bool) or not isinstance(value,int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if maximum_frames is not None and (isinstance(maximum_frames,bool) or not isinstance(maximum_frames,int) or maximum_frames < 1):
        raise ValueError("maximum_frames must be positive or None")
    for name,value in (("vertical_exaggeration",vertical_exaggeration),("earth_radius_metres",earth_radius_metres)):
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    if top_metres is not None and (not np.isfinite(top_metres) or top_metres <= 0):
        raise ValueError("top_metres must be positive or None")
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Choose a new geometry output: {output}")
    files = discover_wrfout(run_directory,domain=domain)
    records, frames = {}, []
    with open_wrf_sequence(files) as ds:
        required = {"HGT","LANDMASK","PH","PHB","XLAT","XLONG"}
        if missing := required-set(ds.variables):
            raise ValueError("Missing WRF variables: "+", ".join(sorted(missing)))
        base = ds.isel(Time=0,drop=True)
        pressure_pa = float(np.asarray(base.P_TOP).item()) if "P_TOP" in base else None
        coordinates = {name: np.asarray(base[name]) for name in ("HGT","LANDMASK","XLAT","XLONG")}
        dx,dy = float(ds.attrs["DX"]),float(ds.attrs["DY"])
        if not np.isfinite([dx,dy]).all() or min(dx,dy) <= 0:
            raise ValueError("DX/DY must be positive and finite")
        rows = _indices(ds.sizes["south_north"],horizontal_stride)
        columns = _indices(ds.sizes["west_east"],horizontal_stride)
        x,y = columns*dx/1000,rows*dy/1000
        terrain = _terrain(base,x,y,rows,columns)
        for name,levels in diagnostics.items():
            label,units,signed,definition,required = _DEFINITIONS[name]
            missing = sorted(set(required)-set(ds.variables))
            reason = "Missing WRF variables: "+", ".join(missing) if missing else ""
            source = dict(definition=definition,source_variables=list(required),units=units)
            if name == "model_tke":
                try:
                    energy = model_tke(base,source=tke_source)
                except LookupError as exc:
                    reason = str(exc)
                else:
                    source.update(energy.attrs)
                    source.pop("unused_array",None)
                    # Only the model_tke contract, not arbitrary NetCDF attributes.
                    source = {key:source[key] for key in ("definition","units","source_variable",
                        "conversion_factor","tke_kind","vertical_processing","method_reference","warning")}
            if name in {"q_criterion","vertical_vorticity"}:
                source["derivative_method"] = _DERIVATIVE_METHOD
                source["earth_radius_metres"] = float(earth_radius_metres)
            records[name] = dict(label=label,units=units,signed=signed,available=not reason,
                reason=reason,source=source,thresholds=np.asarray(levels,float).tolist())
        available = [name for name,entry in records.items() if entry["available"]]
        if not available:
            raise ValueError("None of the requested diagnostics are available")
        extrema = {name:[np.inf,-np.inf] for name in available}
        needs_derivatives = bool(set(available)&{"q_criterion","vertical_vorticity"})
        for index,stamp in enumerate(history_times(ds)[:maximum_frames]):
            frame = ds.isel(Time=index,drop=True)
            if any(not np.allclose(frame[name],original) for name,original in coordinates.items()):
                raise ValueError("Moving grids or time-varying terrain/land masks are not supported")
            heights = mass_heights(frame.PH,frame.PHB,frame.HGT,axis=0,agl=False)
            if not np.isfinite(heights).all() or np.any(np.diff(heights,axis=0) <= 0):
                raise ValueError("Mass heights must be finite and increasing in every column")
            fields = {}
            if "wind_speed" in available or needs_derivatives:
                u = np.asarray(destagger(frame.U,"west_east_stag").transpose("bottom_top","south_north","west_east"),float)
                v = np.asarray(destagger(frame.V,"south_north_stag").transpose("bottom_top","south_north","west_east"),float)
                if "wind_speed" in available: fields["wind_speed"] = np.hypot(u,v)
            if "vertical_velocity" in available or needs_derivatives:
                w = np.asarray(destagger(frame.W,"bottom_top_stag").transpose("bottom_top","south_north","west_east"),float)
                if "vertical_velocity" in available: fields["vertical_velocity"] = w
            if needs_derivatives:
                q,zeta = _physical_diagnostics(frame,u,v,w,heights,earth_radius_metres)
                if "q_criterion" in available: fields["q_criterion"] = q
                if "vertical_vorticity" in available: fields["vertical_vorticity"] = zeta
            if "model_tke" in available:
                fields["model_tke"] = np.asarray(model_tke(frame,source=tke_source).transpose("bottom_top","south_north","west_east"),float)
            above = np.flatnonzero(np.min(heights,axis=(1,2)) > top_metres) if top_metres is not None else []
            stop = int(above[0]+1) if len(above) else len(heights)
            # Keep a full bracketing level for geometric clipping, both surfaces
            # and curtains; section z-axis hides the part above a numeric top.
            sampled_heights = _sample(heights[:stop],rows,columns)
            entry = dict(time_utc=stamp,heights_m=sampled_heights.tolist(),diagnostics={})
            face_count = 0
            for name in available:
                if fields[name].shape != heights.shape or not np.isfinite(fields[name]).all():
                    raise ValueError(f"{stamp} {name}: nonfinite or incompatible mass-grid volume")
                values = _sample(fields[name][:stop],rows,columns)
                meshes = [isosurface_mesh(values,sampled_heights,x,y,level,top_metres=top_metres)
                          for level in records[name]["thresholds"]]
                face_count += sum(len(mesh["faces"]) for mesh in meshes)
                # Ranges exclude the bracketing samples above a requested top.
                visible = values if top_metres is None else values[sampled_heights <= top_metres]
                if not visible.size:
                    raise ValueError("Selected display ceiling is below all sampled mass levels")
                extrema[name][0] = min(extrema[name][0],float(visible.min()))
                extrema[name][1] = max(extrema[name][1],float(visible.max()))
                entry["diagnostics"][name] = dict(meshes=meshes,values=values.tolist())
            if face_count > maximum_faces:
                raise ValueError(f"{stamp}: {face_count} faces exceed maximum_faces={maximum_faces}; explicitly increase the limit or stride")
            interface = np.asarray((frame.PH+frame.PHB).isel(bottom_top_stag=-1),float)/9.81
            entry["model_top"] = dict(interface_msl_m=[float(interface.min()),float(interface.max())],
                highest_mass_msl_m=[float(heights[-1].min()),float(heights[-1].max())])
            entry["face_count"] = face_count
            frames.append(entry)
    model_top = {key:[min(f["model_top"][key][0] for f in frames),max(f["model_top"][key][1] for f in frames)]
                 for key in ("interface_msl_m","highest_mass_msl_m")}
    model_top["pressure_pa"] = pressure_pa
    for name,(lower,upper) in extrema.items():
        if records[name]["signed"]:
            bound = max(abs(lower),abs(upper),1e-15); colour_range = [-bound,bound]
        else:
            colour_range = [min(0.,lower),max(upper,1e-15)]
        records[name].update(value_range=[lower,upper],colour_range=colour_range)
    bundle = dict(schema="wrf-tools-isosurfaces",schema_version=2,domain=domain,
        diagnostics=records,initial_variable=available[0],frames=frames,terrain=terrain,
        x_km=x.tolist(),y_km=y.tolist(),x_extent_km=float(x[-1]),y_extent_km=float(y[-1]),
        source_files=[p.name for p in files],temporal_interpolation="none",height_reference="MSL",
        history_intervals_seconds=np.diff(np.asarray([f["time_utc"] for f in frames],dtype="datetime64[s]")).astype("timedelta64[s]").astype(int).tolist(),
        horizontal_stride=horizontal_stride,nominal_spacing_km=[dx/1000,dy/1000],
        requested_top_metres=top_metres,top_metres=top_metres if top_metres is not None else model_top["highest_mass_msl_m"][1],
        model_top=model_top,vertical_exaggeration=vertical_exaggeration,
        derivative_method=_DERIVATIVE_METHOD,
        references=["https://doi.org/10.5065/1dfh-6p97",
            "https://github.com/wrf-model/WRF/blob/v4.7.1/share/module_model_constants.F",
            "https://forum.mmm.ucar.edu/threads/converting-model-grid-relative-wind-to-earth-relative-wind.179/",
            "https://doi.org/10.1017/S0022112095000462",
            "https://scikit-image.org/docs/stable/api/skimage.measure.html#skimage.measure.marching_cubes"],
        limitations=["Post-processing reconstruction, not WRF discrete operators or vortex/cyclone identification",
            "Q uses rotation/strain definition; compressible flow is not assumed divergence-free",
            "Hourly kilometre-scale output does not resolve LES eddies or temporal turbulent fluxes",
            "No flux budgets, SLP calculation, lambda2 or swirling strength in this viewer",
            "Display point subsampling is not filtering; sampled curtains follow native mass heights",
            "Nominal projected display x/y; spherical physical gradients use geographic coordinates",
            "Open threshold surfaces; no extrapolation, volume integration or temporal morphing",
            "Surface thresholds and colour scales are fixed across saved times; no universal thresholds"])
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(bundle,separators=(",",":"),allow_nan=False),encoding="utf-8")
    return output

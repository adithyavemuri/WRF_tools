"""Reusable non-interactive plotting primitives."""
from __future__ import annotations
import numpy as np

def _plt():
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError("Plotting requires: pip install wrf-tools[plot]") from exc
    return plt

def horizontal(field, *, x=None, y=None, ax=None, levels=20, colorbar=True,
               title=None, xlabel="West-east grid index", ylabel="South-north grid index",
               colorbar_label=None, **kwargs):
    """Filled contours on supplied x/y or index coordinates; return editable artists."""
    plt = _plt(); ax = ax or plt.subplots()[1]
    artist = ax.contourf(np.arange(field.shape[-1]) if x is None else x, np.arange(field.shape[-2]) if y is None else y, field, levels=levels, **kwargs)
    if colorbar:
        cbar=ax.figure.colorbar(artist, ax=ax); cbar.set_label(colorbar_label or "Value")
    ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
    return ax.figure, ax, artist

def profile(values, height, *, ax=None, label=None, title=None,
            xlabel="Value", ylabel="Height (m)", **kwargs):
    """Plot supplied values against physical height; no interpolation is inferred."""
    plt = _plt(); ax = ax or plt.subplots()[1]
    line = ax.plot(values, height, label=label, **kwargs)
    if label: ax.legend()
    ax.set(xlabel=xlabel, ylabel=ylabel, title=title); ax.grid(True,alpha=.3)
    return ax.figure, ax, line

def time_height(values, time, height, *, ax=None, levels=20, colorbar=True,
                title=None, xlabel="Time", ylabel="Height (m)", colorbar_label=None, **kwargs):
    """Plot a supplied (time,height) array with caller-defined coordinates/units."""
    plt = _plt(); ax = ax or plt.subplots()[1]
    artist = ax.contourf(time, height, np.asarray(values).T, levels=levels, **kwargs)
    if colorbar:
        cbar=ax.figure.colorbar(artist, ax=ax); cbar.set_label(colorbar_label or "Value")
    ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
    return ax.figure, ax, artist

def wind_rose(direction, speed, *, direction_bins=16, speed_bins=5, ax=None,
              title="Wind speed and direction", speed_units="m s$^{-1}$"):
    """Stack speed-bin sample counts by meteorological direction, not frequencies."""
    plt = _plt()
    ax = ax or plt.subplots(subplot_kw={"projection": "polar"})[1]
    theta_edges = np.linspace(0, 360, direction_bins+1)
    speed_edges = np.linspace(0, np.nanmax(speed), speed_bins+1)
    hist, _, _ = np.histogram2d(np.asarray(direction)%360, speed, bins=(theta_edges, speed_edges))
    bottoms = np.zeros(direction_bins); width = 2*np.pi/direction_bins
    for i in range(speed_bins):
        heights = hist[:, i]
        label=f"{speed_edges[i]:.1f}-{speed_edges[i+1]:.1f} {speed_units}"
        ax.bar(np.deg2rad(theta_edges[:-1]), heights, width=width, bottom=bottoms, align="edge",label=label)
        bottoms += heights
    ax.set_theta_zero_location("N"); ax.set_theta_direction(-1); ax.set_title(title,pad=18)
    ax.set_rlabel_position(135)
    ax.text(-0.16, 0.5, "Sample count", transform=ax.transAxes, rotation=90,
            va="center", ha="center")
    ax.legend(title="Wind speed",loc="upper left",bbox_to_anchor=(1.08,1.08),frameon=False)
    return ax.figure, ax

def cross_section(values, distance=None, height=None, *, terrain=None, ax=None, levels=20,
                  colorbar=True, title=None, xlabel="Distance", ylabel="Height (m)",
                  colorbar_label=None, **kwargs):
    """Plot a supplied section and optional terrain; not automatic WRF extraction."""
    plt = _plt(); ax = ax or plt.subplots()[1]; values = np.asarray(values)
    distance = np.arange(values.shape[-1]) if distance is None else distance
    height = np.arange(values.shape[-2]) if height is None else height
    artist = ax.contourf(distance, height, values, levels=levels, **kwargs)
    if terrain is not None: ax.fill_between(distance, 0, terrain, color="0.35")
    if colorbar:
        cbar=ax.figure.colorbar(artist, ax=ax); cbar.set_label(colorbar_label or "Value")
    ax.set(xlabel=xlabel,ylabel=ylabel,title=title)
    return ax.figure, ax, artist

def wind_barbs(u, v, *, x=None, y=None, ax=None, stride=1, title=None,
               xlabel="West-east grid index", ylabel="South-north grid index", **kwargs):
    """Plot supplied co-located wind vectors; caller must establish vector basis."""
    plt = _plt(); ax = ax or plt.subplots()[1]; u, v = np.asarray(u), np.asarray(v)
    x = np.arange(u.shape[-1]) if x is None else np.asarray(x); y = np.arange(u.shape[-2]) if y is None else np.asarray(y)
    x_plot = x[::stride, ::stride] if x.ndim == 2 else x[::stride]
    y_plot = y[::stride, ::stride] if y.ndim == 2 else y[::stride]
    artist = ax.barbs(x_plot, y_plot, u[::stride,::stride], v[::stride,::stride], **kwargs)
    ax.set(xlabel=xlabel,ylabel=ylabel,title=title); ax.set_aspect("equal")
    return ax.figure, ax, artist

def nested_domains(domains, *, ax=None, labels=True, **kwargs):
    """Plot projected DomainGeometry rectangles, not geographic coastlines."""
    plt = _plt(); ax = ax or plt.subplots()[1]
    from matplotlib.patches import Rectangle
    artists=[]
    for domain in domains:
        xmin,xmax,ymin,ymax=domain.extent
        patch=Rectangle((xmin,ymin),xmax-xmin,ymax-ymin,fill=False,**kwargs); ax.add_patch(patch); artists.append(patch)
        if labels: ax.text(xmin,ymax,f"d{domain.domain:02d}",va="bottom")
    ax.autoscale_view(); ax.set_aspect("equal"); ax.set(xlabel="West-east distance (m)",ylabel="South-north distance (m)",title="WPS nested domains")
    return ax.figure, ax, artists

def validation_scatter(model, observation, *, ax=None, one_to_one=True, **kwargs):
    """Scatter matched observations against model values with optional 1:1 line."""
    plt = _plt(); ax = ax or plt.subplots()[1]
    artist=ax.scatter(observation,model,**kwargs)
    if one_to_one:
        lo=np.nanmin([model,observation]); hi=np.nanmax([model,observation]); ax.plot([lo,hi],[lo,hi],"k--")
    ax.set_xlabel("Observation"); ax.set_ylabel("Model")
    ax.grid(True,alpha=.3)
    return ax.figure,ax,artist

def taylor_diagram(standard_deviation, correlation, *, reference_std=1.0, labels=None, ax=None, **kwargs):
    """Plot standard deviation and correlation on a Taylor diagram.

    Reference: Taylor (2001), *Journal of Geophysical Research*,
    doi:10.1029/2000JD900719.
    """
    plt=_plt(); ax=ax or plt.subplots(subplot_kw={"projection":"polar"})[1]
    theta=np.arccos(np.clip(correlation,-1,1)); artist=ax.scatter(theta,standard_deviation,**kwargs)
    ax.scatter([0],[reference_std],marker="*",color="black",label="reference")
    ax.set_thetamin(0); ax.set_thetamax(180); ax.set_xlabel("Correlation"); ax.set_title("Taylor diagram")
    if labels:
        for angle,radius,label in zip(theta,standard_deviation,labels): ax.text(angle,radius,str(label))
    return ax.figure,ax,artist

def animate_fields(fields, *, interval=100, levels=20, cmap=None, repeat=False,
                   title="Field", xlabel="West-east grid index", ylabel="South-north grid index"):
    """Animate supplied (time,y,x) arrays at fixed levels; no time interpolation."""
    plt=_plt(); from matplotlib.animation import FuncAnimation
    values=np.asarray(fields); fig,ax=plt.subplots()
    finite=values[np.isfinite(values)]
    if values.ndim != 3 or not len(values) or not finite.size:
        raise ValueError("Expected finite fields with shape (time, y, x)")
    if np.isscalar(levels):
        lo,hi=float(finite.min()),float(finite.max())
        if hi == lo: hi=lo+1
        levels=np.linspace(lo,hi,int(levels)+1)
    def draw(index):
        ax.clear()
        contour = ax.contourf(values[index], levels=levels, cmap=cmap)
        ax.set(xlabel=xlabel,ylabel=ylabel,title=f"{title} - frame {index}")
        # QuadContourSet.collections was removed in Matplotlib 3.11.  Returning
        # the set itself is supported by FuncAnimation and works across both
        # the old and new Matplotlib artist APIs.
        return (contour,)
    animation=FuncAnimation(fig,draw,frames=values.shape[0],interval=interval,repeat=repeat,cache_frame_data=False)
    return fig,ax,animation

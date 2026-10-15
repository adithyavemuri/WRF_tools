"""Offline interactive isosurface inspection with an immutable terrain layer.

Plotly is optional. Geometry, physical coordinates and model states come from
the deterministic exporter; this module changes only their presentation.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


_WEBGL_PREFLIGHT = """
<style>
body {margin:0; background:#080f1c; color:#dce8f1; font-family:system-ui,sans-serif;}
#wrf-webgl-diagnostic[hidden] {display:none;}
#wrf-webgl-diagnostic {position:fixed; z-index:10000; top:18px; left:18px;
 max-width:660px; padding:22px; background:#152536; border:1px solid #edb96a;
 border-radius:8px; box-shadow:0 8px 40px #0009; line-height:1.5;}
#wrf-webgl-diagnostic code {color:#a8dbe5;}
#wrf-webgl-diagnostic button {padding:7px 14px; cursor:pointer;}
</style>
<section id="wrf-webgl-diagnostic" hidden role="alert">
 <strong>3-D graphics (WebGL) are unavailable in this browser.</strong>
 <p>This is a browser graphics problem, not an error in the WRF data.
 Opening the file through a web server will not enable disabled graphics.</p>
 <p>In Chrome, open <code>chrome://settings/system</code>, enable graphics
 acceleration and relaunch. Check <code>chrome://gpu</code> if it still fails.
 Try a full browser rather than an IDE preview.</p>
 <p>If hardware rendering is unavailable, the WRF_tools guide provides an
 explicit <code>--software-webgl</code> launcher using an isolated Chrome profile.
 That lower-security fallback is only for trusted local files.</p>
 <p id="wrf-webgl-detail"></p>
 <button type="button" onclick="location.reload()">Retry after fixing graphics</button>
</section>
<script>
(function () {
    const canvas = document.createElement('canvas');
    let detail = '';
    canvas.addEventListener('webglcontextcreationerror', event => {
        detail = event.statusMessage || 'The browser refused a WebGL context.';
    });
    let context = null;
    try {
        context = canvas.getContext('webgl2') || canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    } catch (error) {
        detail = String(error);
    }
    window.WRF_WEBGL_STATUS = {available: Boolean(context)};
    if (!context) {
        document.getElementById('wrf-webgl-detail').textContent = detail;
        document.getElementById('wrf-webgl-diagnostic').hidden = false;
    } else {
        const cleanup = context.getExtension('WEBGL_lose_context');
        if (cleanup) cleanup.loseContext();
    }
})();
</script>
"""


_HTML_SCRIPT = """
document.body.style.margin = '0';
document.body.style.backgroundColor = '#080f1c';
const graph = document.getElementById('{plot_id}');
// WebGL wheel zoom can precede Plotly's layout-camera update. Commit the live
// view before controls redraw meshes, so time/opacity do not reset zoom.
function rememberCamera() {
    const scene = graph._fullLayout && graph._fullLayout.scene._scene;
    if (scene && typeof scene.getCamera === 'function') {
        graph.layout.scene.camera = JSON.parse(JSON.stringify(scene.getCamera()));
    }
}
graph.addEventListener('pointerdown', rememberCamera, true);
graph.addEventListener('pointerup', () => setTimeout(rememberCamera, 0), true);
graph.addEventListener('wheel', () => {
    [0, 100, 300].forEach(delay => setTimeout(rememberCamera, delay));
}, {passive: true});
graph.on('plotly_animating', rememberCamera);
Plotly.Plots.resize(graph);
"""


def _geometry(value):
    data = json.loads(Path(value).read_text(encoding="utf-8")) if isinstance(value, (str, Path)) else value
    if data.get("schema") != "wrf-tools-isosurfaces" or data.get("schema_version") not in (1,2):
        raise ValueError("Expected WRF_tools isosurface geometry schema v1 or v2")
    if data.get("temporal_interpolation") != "none" or not data.get("frames"):
        raise ValueError("Expected actual timestamps, without temporal morphing")
    if data["schema_version"] == 2:
        from ._diagnostic_interactive import _validate_bundle
        _validate_bundle(data)
        return data
    expected = list(data["thresholds"])
    if any([mesh["level"] for mesh in frame["meshes"]] != expected for frame in data["frames"]):
        raise ValueError("Isosurface thresholds and ordering must remain fixed across frames")
    return data


def _coordinates(mesh):
    vertices = np.asarray(mesh["vertices_km"], float).reshape(-1,3)
    faces = np.asarray(mesh["faces"], int).reshape(-1,3)
    if not np.isfinite(vertices).all() or (len(faces) and (faces.min() < 0 or faces.max() >= len(vertices))):
        raise ValueError("Invalid mesh coordinates or face indices")
    return dict(x=vertices[:,0].tolist(),y=vertices[:,1].tolist(),z=vertices[:,2].tolist(),
                i=faces[:,0].tolist(),j=faces[:,1].tolist(),k=faces[:,2].tolist())


def isosurface_figure(geometry, *, vertical_exaggeration=5., surface_opacity=.35):
    """Return a Plotly 3-D figure with orbit/zoom, actual-time slider and controls.

    Terrain is one opaque, ambient-lit static mesh: animation frames update ONLY
    wind/TKE meshes, never terrain or camera. Vertex z remains physical km MSL;
    exaggeration changes the axis aspect ratio, not the data. Camera orientation
    is preserved across time steps. Transparency still has WebGL depth-sorting
    limitations; the terrain-only control separates geometry from occlusion.
    Schema v2 returns the initial diagnostic/section scene; write_isosurface_html
    installs the offline variable, time and movable-section controls.
    """
    try:
        import plotly.graph_objects as go
    except ImportError as exc:
        raise ImportError('Install the optional browser renderer: pip install "wrf-tools[interactive]"') from exc
    if not np.isfinite(vertical_exaggeration) or vertical_exaggeration <= 0:
        raise ValueError("vertical_exaggeration must be positive and finite")
    if not np.isfinite(surface_opacity) or not 0 <= surface_opacity <= 1:
        raise ValueError("surface_opacity must be in [0,1]")
    data = _geometry(geometry)
    if data["schema_version"] == 2:
        from ._diagnostic_interactive import _diagnostic_figure
        return _diagnostic_figure(data,vertical_exaggeration,surface_opacity)
    ground = data["terrain"]
    faces, colours = [], []
    for face, colour in zip(ground["faces"], ground["colours"]):
        for index in range(1, len(face)-1):
            faces.append([face[0],face[index],face[index+1]])
            colours.append(colour)
    terrain = go.Mesh3d(**_coordinates(dict(vertices_km=ground["vertices_km"],faces=faces)),
        facecolor=colours,name="Terrain / ocean",opacity=1.,flatshading=True,
        lighting=dict(ambient=1.,diffuse=0.,specular=0.,fresnel=0.,roughness=1.),
        hovertemplate="Terrain/ocean<br>x %{x:.1f} km<br>y %{y:.1f} km<br>z %{z:.3f} km MSL<extra></extra>",
        showlegend=True)
    coast = [[],[],[]]
    for line in ground["coastlines_km"]:
        for x,y,z in line:
            for array, value in zip(coast,(x,y,z+.002)):
                array.append(value)
        for array in coast: array.append(None)
    coastline = go.Scatter3d(x=coast[0],y=coast[1],z=coast[2],mode="lines",
        line=dict(color="#b8d4d6",width=3),name="WRF coastline",hoverinfo="skip",showlegend=True)
    palette = ["#4fc8cf","#f2b45e","#f17467","#bd99ec"]
    wind_indices = list(range(2,2+len(data["thresholds"])))
    first = [go.Mesh3d(**_coordinates(mesh),name=f"{mesh['level']:g} {data['source']['units']}",
        color=palette[index%len(palette)],opacity=surface_opacity,flatshading=False,
        lighting=dict(ambient=.8,diffuse=.2,specular=0.,fresnel=0.),
        hovertemplate="x %{x:.1f} km<br>y %{y:.1f} km<br>z %{z:.3f} km MSL<extra>%{fullData.name}</extra>",
        showlegend=True) for index,mesh in enumerate(data["frames"][0]["meshes"])]
    frames = [go.Frame(name=frame["time_utc"],traces=wind_indices,
        data=[go.Mesh3d(**_coordinates(mesh)) for mesh in frame["meshes"]]) for frame in data["frames"]]
    fig = go.Figure(data=[terrain,coastline,*first],frames=frames)
    width,depth = data["x_extent_km"],data["y_extent_km"]
    ground_z = np.asarray(ground["vertices_km"])[:,2]
    zmin,zmax = min(-.01,float(ground_z.min())),float(data["top_metres"])/1000
    span = max(width,depth)

    def ratio(exaggeration):
        return dict(x=width/span,y=depth/span,z=(zmax-zmin)*exaggeration/span)

    steps = [dict(label=frame["time_utc"].replace("T"," "),method="animate",
        args=[[frame["time_utc"]],dict(mode="immediate",frame=dict(duration=0,redraw=True),transition=dict(duration=0))])
        for frame in data["frames"]]
    n = len(fig.data)
    scales = sorted(set([1.,5.,10.,25.,float(vertical_exaggeration)]))
    model_top = data.get("model_top",{}).get("interface_msl_m")
    model_text = f"Model-top interface {model_top[0]/1000:.2f}-{model_top[1]/1000:.2f} km MSL. " if model_top else ""
    fig.update_layout(template="plotly_dark",paper_bgcolor="#080f1c",plot_bgcolor="#080f1c",
        title=dict(text=f"WRF {data['domain'].upper()} | {data['variable'].replace('_',' ')} isosurfaces",x=.02,y=.99,yanchor="top"),
        height=900,margin=dict(l=5,r=5,t=130,b=220),uirevision="wrf-isosurface-view",
        legend=dict(orientation="h",x=.02,y=1.08),
        scene=dict(xaxis=dict(title="Native x (km)",range=[0,width]),
            yaxis=dict(title="Native y (km)",range=[0,depth]),
            zaxis=dict(title="Height (km MSL)",range=[zmin,zmax]),
            aspectmode="manual",aspectratio=ratio(vertical_exaggeration),
            dragmode="orbit",camera=dict(eye=dict(x=.9,y=-.95,z=.65)),uirevision="wrf-isosurface-camera"),
        sliders=[dict(active=0,currentvalue=dict(prefix="UTC: "),pad=dict(t=30,b=5),steps=steps,x=.15,len=.82,y=-.04)],
        updatemenus=[
            dict(type="buttons",direction="left",showactive=False,x=0,y=-.04,xanchor="left",yanchor="top",buttons=[
                dict(label="Play",method="animate",args=[None,dict(fromcurrent=True,mode="immediate",
                    frame=dict(duration=900,redraw=True),transition=dict(duration=0))]),
                dict(label="Pause",method="animate",args=[[None],dict(mode="immediate",frame=dict(duration=0,redraw=False))])]),
            dict(type="dropdown",x=.02,y=1.18,xanchor="left",active=0,buttons=[
                dict(label="Terrain + surfaces",method="restyle",args=["visible",[True]*n]),
                dict(label="Terrain only",method="restyle",args=["visible",[True,True]+[False]*(n-2)]),
                dict(label="Surfaces only",method="restyle",args=["visible",[False,False]+[True]*(n-2)])]),
            dict(type="dropdown",x=.32,y=1.18,xanchor="left",active=scales.index(float(vertical_exaggeration)),buttons=[
                dict(label=f"Vertical scale {value:g}x",method="relayout",args=[{"scene.aspectratio":ratio(value)}]) for value in scales]),
            dict(type="dropdown",x=.60,y=1.18,xanchor="left",active=0,buttons=[
                dict(label=f"Surface opacity {value:g}",method="restyle",args=["opacity",value,wind_indices])
                for value in dict.fromkeys([float(surface_opacity),.15,.6,1.])])],
        annotations=[dict(x=.01,y=-.32,xref="paper",yref="paper",xanchor="left",showarrow=False,align="left",
            text=model_text+f"Displayed top {zmax:.2f} km MSL; stride {data['horizontal_stride']}.<br>"
                "Drag: rotate | wheel: zoom | use pan tool to move | legend: hide a surface.<br>"
                "Terrain is static; colours are illustrative. Actual saved timestamps only; no temporal morphing.")],
        meta=dict(schema="wrf-tools-interactive-isosurfaces",geometry_schema_version=1,
            terrain_trace_indices=[0,1],animated_trace_indices=wind_indices,
            physical_height_units="km MSL",initial_vertical_exaggeration=float(vertical_exaggeration),
            temporal_interpolation="none",terrain_lighting="ambient only; fixed colours"))
    return fig


def write_isosurface_html(geometry, output, *, vertical_exaggeration=5., surface_opacity=.35):
    """Write a self-contained offline HTML viewer; no server or CDN is needed.

    Requires an ordinary WebGL-capable browser. Refuses to overwrite existing
    output. Camera and terrain remain fixed when the time slider is changed;
    manual rotation changes only the shared viewing camera, not coordinates.
    """
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Choose a new HTML output: {output}")
    figure = isosurface_figure(geometry,vertical_exaggeration=vertical_exaggeration,surface_opacity=surface_opacity)
    data = _geometry(geometry)
    controls, script = "", _HTML_SCRIPT
    diagnostic = data["schema_version"] == 2
    if data["schema_version"] == 2:
        from ._diagnostic_interactive import _CONTROLS, _SCRIPT
        controls = _CONTROLS
        # Prevent a data string containing an HTML closing tag from breaking
        # out of the script element. No external JS or eval is used.
        payload = json.dumps(data,separators=(",",":"),allow_nan=False).replace("<","\\u003c")
        script += _SCRIPT.replace("__WRF_DIAGNOSTIC_DATA__",payload)
    output.parent.mkdir(parents=True,exist_ok=True)
    figure.update_layout(height=None,autosize=True)
    html = figure.to_html(include_plotlyjs=True,full_html=True,auto_play=False,
        default_height="100%" if diagnostic else "100vh",
        config=dict(scrollZoom=True,displaylogo=False,responsive=True),div_id="wrf-isosurfaces",
        post_script=script)
    initialization = 'if (document.getElementById("wrf-isosurfaces")) {'
    if html.count(initialization) != 1:
        raise RuntimeError("Plotly HTML initialization changed; update the WebGL preflight guard")
    html = html.replace(initialization,
        'if (window.WRF_WEBGL_STATUS.available && document.getElementById("wrf-isosurfaces")) {',1)
    # This runs BEFORE Plotly: its post_script cannot explain a failed initial
    # WebGL context because Plotly's initialization promise may reject first.
    body = '<body class="wrf-diagnostic-page">' if diagnostic else "<body>"
    output.write_text(html.replace("<body>", body+_WEBGL_PREFLIGHT+controls, 1),encoding="utf-8")
    return output

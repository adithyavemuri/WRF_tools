"""Offline diagnostic controls; all calculations happen in Python at export."""
from copy import deepcopy

import numpy as np


def _validate_bundle(data):
    from .interactive import _coordinates
    names = [key for key,value in data["diagnostics"].items() if value["available"]]
    if not names or data["initial_variable"] not in names:
        raise ValueError("No valid initial diagnostic")
    x,y = np.asarray(data["x_km"],float),np.asarray(data["y_km"],float)
    if x.ndim != 1 or y.ndim != 1 or min(len(x),len(y)) < 2 or not np.isfinite(np.r_[x,y]).all() or np.any(np.diff(x) <= 0) or np.any(np.diff(y) <= 0):
        raise ValueError("Invalid diagnostic section horizontal coordinates")
    for name in names:
        entry = data["diagnostics"][name]
        levels = np.asarray(entry["thresholds"],float)
        colour = np.asarray(entry["colour_range"],float)
        if levels.ndim != 1 or not levels.size or not np.isfinite(levels).all() or np.any(np.diff(levels) <= 0):
            raise ValueError("Invalid diagnostic thresholds")
        if colour.shape != (2,) or not np.isfinite(colour).all() or colour[1] <= colour[0]:
            raise ValueError("Invalid diagnostic colour range")
    for frame in data["frames"]:
        z = np.asarray(frame["heights_m"],float)
        if z.ndim != 3 or min(z.shape) < 2 or z.shape[1:] != (len(y),len(x)) or not np.isfinite(z).all() or np.any(np.diff(z,axis=0) <= 0):
            raise ValueError("Invalid diagnostic section heights")
        for name in names:
            values = np.asarray(frame["diagnostics"][name]["values"],float)
            meshes = frame["diagnostics"][name]["meshes"]
            if values.shape != z.shape or not np.isfinite(values).all():
                raise ValueError("Invalid diagnostic section values")
            if [m["level"] for m in meshes] != data["diagnostics"][name]["thresholds"]:
                raise ValueError("Diagnostic thresholds must remain fixed across frames")
            for mesh in meshes: _coordinates(mesh)


def _section(data,variable,time_index,axis,position):
    """Exact sampled native column curtain, no vertical/time interpolation."""
    frame = data["frames"][time_index]
    values = np.asarray(frame["diagnostics"][variable]["values"])
    z = np.asarray(frame["heights_m"])/1000
    x,y = np.asarray(data["x_km"]),np.asarray(data["y_km"])
    if axis == "xz":
        scalar,height = values[:,position,:],z[:,position,:]
        xx = np.broadcast_to(x,height.shape); yy = np.full_like(height,y[position])
    elif axis == "yz":
        scalar,height = values[:,:,position],z[:,:,position]
        yy = np.broadcast_to(y,height.shape); xx = np.full_like(height,x[position])
    else:
        raise ValueError("Section axis must be xz or yz")
    return dict(x=xx.tolist(),y=yy.tolist(),z=height.tolist(),surfacecolor=scalar.tolist())


def _diagnostic_figure(data,exaggeration,opacity):
    import plotly.graph_objects as go
    from .interactive import isosurface_figure
    name = data["initial_variable"]
    entry = data["diagnostics"][name]
    # Reuse the tested immutable terrain renderer, without changing schema v1.
    initial = deepcopy(data["frames"][0]["diagnostics"][name]["meshes"])
    slots = max(len(d["thresholds"]) for d in data["diagnostics"].values() if d["available"])
    while len(initial) < slots:
        initial.append(dict(level=0.,vertices_km=[],faces=[]))
    legacy = {key:data[key] for key in ("domain","terrain","top_metres","model_top",
        "horizontal_stride","x_extent_km","y_extent_km","temporal_interpolation")}
    legacy.update(schema="wrf-tools-isosurfaces",schema_version=1,variable=name,
        source=entry["source"],thresholds=[m["level"] for m in initial],
        frames=[dict(time_utc=data["frames"][0]["time_utc"],meshes=initial)])
    fig = isosurface_figure(legacy,vertical_exaggeration=exaggeration,surface_opacity=opacity)
    for index,mesh in enumerate(fig.data[2:]):
        if index >= len(entry["thresholds"]): mesh.visible = False
    curtain = go.Surface(**_section(data,name,0,"xz",len(data["y_km"])//2),
        colorscale="RdBu_r" if entry["signed"] else "Viridis",
        cmin=entry["colour_range"][0],cmax=entry["colour_range"][1],opacity=.9,
        name="Native-grid vertical section",showscale=True,showlegend=False,
        colorbar=dict(title=entry["units"],len=.6,thickness=14),
        hovertemplate="x %{x:.1f} km<br>y %{y:.1f} km<br>z %{z:.3f} km MSL<br>value %{surfacecolor:.4g}<extra>Section</extra>")
    fig.add_trace(curtain)
    fig.frames = []
    # Plotly update_layout merges compound arrays; an empty list does not
    # reliably remove the v1 controls. Assign them explicitly instead.
    fig.layout.sliders = ()
    fig.layout.updatemenus = ()
    fig.layout.annotations = ()
    fig.update_layout(title=dict(text=""),
        margin=dict(l=5,r=85,t=65,b=45),
        legend=dict(y=1.,yanchor="bottom"),
        meta=dict(schema="wrf-tools-interactive-diagnostics",geometry_schema_version=2,
            terrain_trace_indices=[0,1],mesh_trace_indices=list(range(2,2+slots)),
            section_trace_index=2+slots,physical_height_units="km MSL",
            initial_vertical_exaggeration=float(exaggeration),initial_surface_opacity=float(opacity),
            temporal_interpolation="none",controls="Installed by write_isosurface_html"))
    return fig


_CONTROLS = """
<style>
body.wrf-diagnostic-page {display:grid;grid-template-rows:auto minmax(360px,1fr) auto;
 height:100vh;min-height:600px;}
#wrf-controls {grid-row:1;position:relative;z-index:20;padding:12px 16px;
 max-height:40vh;overflow:auto;box-sizing:border-box;min-width:0;
 background:#101d2bf2;border-bottom:1px solid #355169;font-size:13px;line-height:1.6;}
#wrf-plot-container {grid-row:2;position:relative;min-width:0;min-height:360px;}
#wrf-isosurfaces {min-height:360px;}
#wrf-controls .row {display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:3px 0;}
#wrf-controls select,#wrf-controls button {background:#1d3449;color:#edf7ff;
 border:1px solid #54718b;border-radius:4px;padding:4px;max-width:320px;}
#wrf-controls input[type=range] {width:170px;vertical-align:middle;}
#wrf-controls input[type=number] {width:105px;padding:4px;background:#1d3449;
 color:#edf7ff;border:1px solid #54718b;border-radius:4px;}
#wrf-time {width:260px !important;}
#wrf-status {color:#b6d5e4;} #wrf-source {max-height:95px;overflow:auto;}
#wrf-method p {margin:4px 0;} #wrf-method a {color:#9dd9ef;}
#wrf-footer {grid-row:3;position:relative;padding:8px 16px;min-width:0;
 background:#101d2bf2;font-size:12px;color:#b6d5e4;z-index:20;}
</style>
<section id="wrf-controls" aria-label="WRF diagnostic controls">
 <div class="row"><strong>WRF diagnostic explorer</strong>
  <label>Field <select id="wrf-variable"></select></label>
  <label>View <select id="wrf-view">
   <option value="all">Terrain + surfaces + section</option>
   <option value="terrain_surfaces">Terrain + surfaces only</option>
   <option value="section">Terrain + section only</option>
   <option value="terrain">Terrain only</option>
   <option value="surfaces">Surfaces only</option>
  </select></label>
  <label>Vertical scale <select id="wrf-scale"></select></label>
  <label>Surface opacity <input id="wrf-opacity" type="range" min="0" max="1" step="0.05"></label>
 </div>
 <div class="row"><button id="wrf-play" type="button">Play</button>
  <label>Saved time <input id="wrf-time" type="range" min="0" step="1"></label><output id="wrf-stamp"></output>
 </div>
 <div class="row"><label>Vertical section <select id="wrf-section-axis">
  <option value="xz">Along native x; move in y</option>
  <option value="yz">Along native y; move in x</option>
 </select></label>
 <label>Position <input id="wrf-section-position" type="range" min="0" step="1"></label>
 <output id="wrf-section-label"></output></div>
 <div class="row"><strong>Height window (m MSL)</strong>
  <label>From <input id="wrf-height-min" type="number" step="any" required></label>
  <label>To <input id="wrf-height-max" type="number" step="any" required></label>
  <button id="wrf-height-apply" type="button">Apply height</button>
  <button id="wrf-height-full" type="button">Full export</button>
  <label><input id="wrf-height-fit" type="checkbox" checked>Fit vertical view</label>
  <output id="wrf-height-note"></output>
 </div>
 <div id="wrf-status" role="status"></div>
 <details id="wrf-source"><summary>Definition, sources and scientific limits</summary><div id="wrf-method"></div></details>
</section>
<footer id="wrf-footer">Drag: rotate · wheel: zoom · pan tool: move · Heights remain km MSL at every vertical scale.
 Actual saved states only. Surfaces are threshold geometry, not proof of turbulence or a model error.</footer>
"""


_SCRIPT = """
(async function () {
const bundle = __WRF_DIAGNOSTIC_DATA__;
const control = id => document.getElementById('wrf-'+id);
const available = Object.keys(bundle.diagnostics).filter(key => bundle.diagnostics[key].available);
const meshIndices = graph.layout.meta.mesh_trace_indices;
const sectionIndex = graph.layout.meta.section_trace_index;
const fullHeightRange=Array.from(graph.layout.scene.zaxis.range);
let heightRange=Array.from(fullHeightRange);
control('height-min').value=fullHeightRange[0]*1000;
control('height-max').value=fullHeightRange[1]*1000;
const terrainFull={vertices_km:graph.data[0].x.map((x,i)=>[x,graph.data[0].y[i],graph.data[0].z[i]]),
    faces:graph.data[0].i.map((i,n)=>[i,graph.data[0].j[n],graph.data[0].k[n]]),
    colours:Array.from(graph.data[0].facecolor)};
const coastlineFull={x:Array.from(graph.data[1].x),y:Array.from(graph.data[1].y),z:Array.from(graph.data[1].z)};
let playing = false, busy = false;
const hiddenMeshes = {};
for (const [key,entry] of Object.entries(bundle.diagnostics)) {
    const option = document.createElement('option');
    option.value = key; option.disabled = !entry.available;
    option.textContent = entry.label + (entry.available ? '' : ' — unavailable');
    option.title = entry.reason || entry.source.definition;
    control('variable').appendChild(option);
}
control('variable').value = bundle.initial_variable;
control('time').max = bundle.frames.length-1;
control('time').value = 0;
control('section-position').max = bundle.y_km.length-1;
control('section-position').value = Math.floor(bundle.y_km.length/2);
control('opacity').value = graph.layout.meta.initial_surface_opacity;
for (const value of [...new Set([1,5,10,25,graph.layout.meta.initial_vertical_exaggeration])].sort((a,b)=>a-b)) {
    const option = document.createElement('option'); option.value = value; option.textContent = value+'x';
    control('scale').appendChild(option);
}
control('scale').value = graph.layout.meta.initial_vertical_exaggeration;
function meshCoordinates(mesh) {
    const v = mesh.vertices_km, f = mesh.faces;
    return {x:v.map(p=>p[0]),y:v.map(p=>p[1]),z:v.map(p=>p[2]),
            i:f.map(p=>p[0]),j:f.map(p=>p[1]),k:f.map(p=>p[2])};
}
function clipMesh(mesh,lower,upper) {
    // Clip existing triangles geometrically; never invent a horizontal cap.
    const points=mesh.vertices_km;
    if(points.every(p=>p[2]>=lower&&p[2]<=upper)) return mesh;
    const vertices=[],faces=[],colours=[];
    function clipPolygon(polygon,bound,keepAbove) {
        const result=[];
        polygon.forEach((a,i)=>{
            const b=polygon[(i+1)%polygon.length];
            const insideA=keepAbove?a[2]>=bound:a[2]<=bound;
            const insideB=keepAbove?b[2]>=bound:b[2]<=bound;
            if(insideA) result.push(a);
            if(insideA!==insideB) {
                const t=(bound-a[2])/(b[2]-a[2]);
                result.push([a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]),bound]);
            }
        });
        return result;
    }
    mesh.faces.forEach((face,index)=>{
        let polygon=clipPolygon(face.map(i=>points[i]),lower,true);
        polygon=clipPolygon(polygon,upper,false);
        for(let j=1;j<polygon.length-1;j++) {
            const [a,b,c]=[polygon[0],polygon[j],polygon[j+1]];
            const ab=b.map((v,i)=>v-a[i]),ac=c.map((v,i)=>v-a[i]);
            const area=Math.hypot(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]);
            if(area===0) continue;
            const start=vertices.length;vertices.push(a,b,c);faces.push([start,start+1,start+2]);
            if(mesh.colours) colours.push(mesh.colours[index]);
        }
    });
    return {level:mesh.level,vertices_km:vertices,faces:faces,colours:colours};
}
function clipLine(line,lower,upper) {
    if(line.z.every(z=>z===null||(z>=lower&&z<=upper))) return line;
    const result={x:[],y:[],z:[]};
    for(let i=0;i<line.z.length-1;i++) {
        if(line.z[i]===null||line.z[i+1]===null) continue;
        const a=[line.x[i],line.y[i],line.z[i]],b=[line.x[i+1],line.y[i+1],line.z[i+1]];
        const dz=b[2]-a[2];let lo=0,hi=1;
        if(dz===0) {if(a[2]<lower||a[2]>upper) continue;}
        else {
            const t1=(lower-a[2])/dz,t2=(upper-a[2])/dz;
            lo=Math.max(0,Math.min(t1,t2));hi=Math.min(1,Math.max(t1,t2));
            if(lo>hi) continue;
        }
        for(const t of [lo,hi]) {
            result.x.push(a[0]+t*(b[0]-a[0]));result.y.push(a[1]+t*(b[1]-a[1]));
            result.z.push(Math.max(lower,Math.min(upper,a[2]+t*dz)));
        }
        result.x.push(null);result.y.push(null);result.z.push(null);
    }
    return result;
}
function clipSection(section,lower,upper) {
    const z=section.z.map(row=>Array.from(row)),colour=section.surfacecolor.map(row=>Array.from(row));
    for(let i=0;i<z[0].length;i++) {
        const heights=section.z.map(row=>row[i]),values=section.surfacecolor.map(row=>row[i]);
        if(heights.at(-1)<lower||heights[0]>upper) {
            z.forEach(row=>row[i]=null);colour.forEach(row=>row[i]=null);continue;
        }
        for(let k=0;k<heights.length;k++) {
            const target=Math.max(lower,Math.min(upper,heights[k]));
            if(target===heights[k]) continue;
            let a=0;while(a<heights.length-2&&heights[a+1]<target) a++;
            const weight=(target-heights[a])/(heights[a+1]-heights[a]);
            z[k][i]=target;colour[k][i]=values[a]+weight*(values[a+1]-values[a]);
        }
    }
    return Object.assign({},section,{z:z,surfacecolor:colour});
}
function sectionCoordinates(frame, variable, axis, position) {
    const volume = frame.diagnostics[variable].values, height = frame.heights_m;
    const x=[],y=[],z=[],colour=[];
    for (let k=0; k<height.length; k++) {
        const xs=[],ys=[],zs=[],cs=[];
        const size = axis==='xz' ? bundle.x_km.length : bundle.y_km.length;
        for (let a=0;a<size;a++) {
            const j=axis==='xz'?position:a, i=axis==='xz'?a:position;
            xs.push(bundle.x_km[i]);ys.push(bundle.y_km[j]);
            zs.push(height[k][j][i]/1000);cs.push(volume[k][j][i]);
        }
        x.push(xs);y.push(ys);z.push(zs);colour.push(cs);
    }
    return {x:x,y:y,z:z,surfacecolor:colour};
}
function statusText(variable,frame,displayedMeshes) {
    const entry=bundle.diagnostics[variable], meshes=frame.diagnostics[variable].meshes;
    const empty=(displayedMeshes||meshes).filter(m=>!m.faces.length).map(m=>m.level);
    const missing=Object.values(bundle.diagnostics).filter(d=>!d.available).map(d=>d.label+': '+d.reason);
    control('stamp').textContent=frame.time_utc.replace('T',' ')+' UTC';
    control('status').textContent='Thresholds: '+entry.thresholds.join(', ')+' '+entry.units+
        ' · Fixed colour range: '+entry.colour_range.map(v=>v.toPrecision(3)).join(' to ')+
        (empty.length?' · No surface in height window at: '+empty.join(', '):'')+' · stride '+bundle.horizontal_stride;
    control('height-note').textContent=heightRange.map(z=>(z*1000).toLocaleString(undefined,{maximumFractionDigits:2})).join(' to ')+' m MSL';
    const panel=control('method');panel.replaceChildren();
    const sources=(entry.source.source_variables||[entry.source.source_variable]).filter(Boolean).join(', ');
    const paragraphs=[entry.source.definition,'Source fields: '+sources+'. Units: '+entry.units+'.',
        'Domain: '+bundle.domain+'. Display top: '+(bundle.top_metres/1000).toFixed(2)+' km MSL. '+
        'Model-top interfaces: '+bundle.model_top.interface_msl_m.map(v=>(v/1000).toFixed(2)).join(' to ')+' km MSL. '+
        'Saved intervals (seconds): '+[...new Set(bundle.history_intervals_seconds||[])].join(', ')+'.',
        entry.source.derivative_method,entry.source.warning,
        entry.source.conversion_factor!==undefined?'Source conversion factor: '+entry.source.conversion_factor:null,
        ...bundle.limitations,...missing];
    for (const text of paragraphs.filter(Boolean)) {
        const p=document.createElement('p');p.textContent=text;panel.appendChild(p);
    }
    for (const url of bundle.references) {
        const p=document.createElement('p'),a=document.createElement('a');
        a.textContent=url;a.href=url;a.target='_blank';a.rel='noopener noreferrer';
        p.appendChild(a);panel.appendChild(p);
    }
}
async function draw() {
    // Controls remain responsive; coalesce rapid slider events into a final redraw.
    if (busy) { window.WRF_DIAGNOSTIC_VIEWER.pending=true; return; }
    busy=true;
    try {
        rememberCamera();
        const variable=control('variable').value, entry=bundle.diagnostics[variable];
        const frame=bundle.frames[Number(control('time').value)];
        const view=control('view').value, axis=control('section-axis').value;
        const coords=axis==='xz'?bundle.y_km:bundle.x_km;
        control('section-position').max=coords.length-1;
        const position=Math.min(Number(control('section-position').value),coords.length-1);
        control('section-position').value=position;
        control('section-label').textContent=(axis==='xz'?'y':'x')+' = '+coords[position].toFixed(1)+' km (native grid)';
        const traces=graph.data.map(trace=>Object.assign({},trace));
        const ground=clipMesh(terrainFull,heightRange[0],heightRange[1]);
        traces[0]=Object.assign({},traces[0],meshCoordinates(ground),{facecolor:ground.colours});
        traces[1]=Object.assign({},traces[1],clipLine(coastlineFull,heightRange[0],heightRange[1]));
        traces[0].visible=traces[1].visible=view!=='surfaces';
        const meshes=frame.diagnostics[variable].meshes.map(mesh=>clipMesh(mesh,heightRange[0],heightRange[1]));
        meshIndices.forEach((traceIndex,index)=>{
            const mesh=meshes[index]||{vertices_km:[],faces:[],level:0};
            const visible=(view==='all'||view==='terrain_surfaces'||view==='surfaces')&&index<meshes.length;
            const signedColour=mesh.level<0?'#5b9ded':'#ed8b67';
            traces[traceIndex]=Object.assign({},traces[traceIndex],meshCoordinates(mesh),{
                name:mesh.level+' '+entry.units,
                visible:visible?(hiddenMeshes[variable+':'+index]?'legendonly':true):false,
                opacity:Number(control('opacity').value),
                color:entry.signed?signedColour:['#4fc8cf','#f2b45e','#bd99ec'][index%3]});
        });
        traces[sectionIndex]=Object.assign({},traces[sectionIndex],
            clipSection(sectionCoordinates(frame,variable,axis,position),heightRange[0],heightRange[1]),{
            cmin:entry.colour_range[0],cmax:entry.colour_range[1],
            colorscale:entry.signed?'RdBu_r':'Viridis',
            colorbar:{title:{text:entry.units},len:.6,thickness:14},
            visible:view==='all'||view==='section'});
        const width=bundle.x_extent_km,depth=bundle.y_extent_km,span=Math.max(width,depth);
        const zr=heightRange;
        const scene=Object.assign({},graph.layout.scene,{zaxis:Object.assign({},graph.layout.scene.zaxis,{range:Array.from(zr)}),
            aspectratio:{x:width/span,y:depth/span,
            z:(zr[1]-zr[0])*Number(control('scale').value)/span}});
        const layout=Object.assign({},graph.layout,{scene:scene,title:{text:''}});
        await Plotly.react(graph,traces,layout);
        statusText(variable,frame,meshes);
    } catch (error) {
        control('status').textContent='Viewer error: '+error.message;
        console.error(error);
    } finally {
        busy=false;
        if (window.WRF_DIAGNOSTIC_VIEWER.pending) {
            window.WRF_DIAGNOSTIC_VIEWER.pending=false; await draw();
        }
    }
}
window.WRF_DIAGNOSTIC_VIEWER={draw:draw,pending:false,bundle:bundle,
    clipMesh:clipMesh,clipLine:clipLine,clipSection:clipSection};
function applyHeight(next) {
    if(!next.every(Number.isFinite)||next[0]>=next[1]||next[0]<fullHeightRange[0]-1e-12||next[1]>fullHeightRange[1]+1e-12) {
        control('status').textContent='Invalid height window: use increasing finite heights within the exported range ('+
            fullHeightRange.map(z=>(z*1000).toFixed(2)).join(' to ')+' m MSL).';
        return;
    }
    next=[Math.max(next[0],fullHeightRange[0]),Math.min(next[1],fullHeightRange[1])];
    if(control('height-fit').checked) {
        // Keep the vertical box useful when inspecting a shallow layer. The
        // displayed exaggeration is updated honestly, not disguised as 1:1.
        const scale=Number((Number(control('scale').value)*(heightRange[1]-heightRange[0])/(next[1]-next[0])).toPrecision(10));
        if(!Array.from(control('scale').options).some(o=>Number(o.value)===scale)) {
            const option=document.createElement('option');option.value=String(scale);
            option.textContent=scale.toLocaleString(undefined,{maximumSignificantDigits:6})+'x (fit)';
            control('scale').appendChild(option);
        }
        control('scale').value=String(scale);
    }
    heightRange=Array.from(next);draw();
}
control('height-apply').addEventListener('click',()=>applyHeight([
    control('height-min').valueAsNumber/1000,control('height-max').valueAsNumber/1000]));
control('height-full').addEventListener('click',()=>{
    control('height-min').value=fullHeightRange[0]*1000;
    control('height-max').value=fullHeightRange[1]*1000;applyHeight(fullHeightRange);
});
// Controls, plot and footer occupy separate layout rows, never overlays.
// Recompute the plot's own pixel size when wrapping/expanded methods/browser
// zoom changes the space available. Paper-relative legends stay in that plot.
const plotContainer=graph.parentElement;
plotContainer.id='wrf-plot-container';
let resizeRequest=0,lastWidth=-1,lastHeight=-1;
const resizePlot=()=>{
    const width=plotContainer.clientWidth,height=plotContainer.clientHeight;
    if(width===lastWidth&&height===lastHeight) return;
    lastWidth=width;lastHeight=height;
    cancelAnimationFrame(resizeRequest);
    resizeRequest=requestAnimationFrame(()=>{rememberCamera();Plotly.Plots.resize(graph);});
};
new ResizeObserver(resizePlot).observe(plotContainer);
resizePlot();
for (const id of ['variable','view','scale','section-axis']) control(id).addEventListener('change',draw);
for (const id of ['time','section-position','opacity']) control(id).addEventListener('input',draw);
graph.on('plotly_legendclick',event=>{
    if (event.curveNumber>=2&&event.curveNumber<sectionIndex) {
        const key=control('variable').value+':'+(event.curveNumber-2);
        hiddenMeshes[key]=!hiddenMeshes[key];draw();return false;
    }
});
graph.on('plotly_legenddoubleclick',()=>false);
control('play').addEventListener('click',async()=>{
    playing=!playing;control('play').textContent=playing?'Pause':'Play';
    if (!playing) return;
    if(Number(control('time').value)>=bundle.frames.length-1) control('time').value=0;
    while (playing) {
        const next=Number(control('time').value)+1;
        if (next>=bundle.frames.length) {playing=false;break;}
        control('time').value=next;await draw();
        await new Promise(resolve=>setTimeout(resolve,900));
    }
    control('play').textContent='Play';
});
await draw();
})();
"""

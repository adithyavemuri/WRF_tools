"""Optional real-browser acceptance check, separate from numerical pytest tests.

Install Playwright in a test environment and use an already installed Chrome:
    python -m pip install playwright
    python tests/browser/check_diagnostic_viewer.py /path/to/viewer.html

--software-webgl explicitly opts into isolated software rendering for trusted
local files; it does not modify the normal browser profile or disable sandboxing.
"""
import argparse
import json
from pathlib import Path
import shutil

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html',type=Path)
    parser.add_argument('--chrome',default=shutil.which('google-chrome') or shutil.which('chromium'))
    parser.add_argument('--software-webgl',action='store_true')
    parser.add_argument('--screenshot',type=Path)
    parser.add_argument('--result',type=Path)
    args = parser.parse_args()
    if not args.html.is_file() or not args.chrome:
        parser.error('Supply a local HTML viewer and an installed Chrome/Chromium executable')
    for path in (args.screenshot,args.result):
        if path and path.exists(): parser.error('Choose new screenshot/result paths; no overwrite')
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        flags = ['--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'] if args.software_webgl else []
        browser = p.chromium.launch(executable_path=args.chrome,headless=True,args=flags,chromium_sandbox=True)
        context = browser.new_context(viewport=dict(width=1600,height=1000),offline=True)
        page = context.new_page()
        errors,requests = [],[]
        page.on('pageerror',lambda error: errors.append(str(error)))
        page.on('request',lambda request: requests.append(request.url))
        page.goto(args.html.resolve().as_uri(),wait_until='load',timeout=90000)
        page.wait_for_function("() => window.WRF_DIAGNOSTIC_VIEWER && document.getElementById('wrf-stamp').textContent",timeout=90000)
        layout_sizes = [(1600,1000),(1280,720),(900,700),(1920,1080),(2560,1440)]
        for width,height in layout_sizes:
            page.set_viewport_size(dict(width=width,height=height))
            for expanded in (False,True):
                page.locator('#wrf-source').evaluate('(e,value)=>e.open=value',expanded)
                page.wait_for_function("""() => {
                    const box=s=>document.querySelector(s)?.getBoundingClientRect();
                    const controls=box('#wrf-controls'),plot=box('#wrf-isosurfaces'),footer=box('#wrf-footer');
                    const legend=box('#wrf-isosurfaces .legend'),tools=box('#wrf-isosurfaces .modebar');
                    return controls&&plot&&footer&&legend&&tools&&
                        controls.bottom<=plot.top+1&&plot.bottom<=footer.top+1&&
                        legend.top>=plot.top-1&&legend.bottom<=plot.bottom+1&&
                        tools.top>=plot.top-1&&tools.bottom<=plot.bottom+1;
                }""",timeout=15000)
        page.set_viewport_size(dict(width=1600,height=1000))
        page.locator('#wrf-source').evaluate('(e)=>e.open=false')
        page.wait_for_timeout(500)
        snapshot = """() => {const g=document.getElementById('wrf-isosurfaces');
            return {terrain:JSON.stringify([g.data[0],g.data[1]]),
                camera:g._fullLayout.scene._scene.getCamera(),
                colour:[g.data.at(-1).cmin,g.data.at(-1).cmax],
                height:g.layout.scene.zaxis.range,section:g.data.at(-1).surfacecolor,
                opacity:g.data[2].opacity};} """
        initial = page.evaluate(snapshot)
        page.mouse.move(750,510); page.mouse.down(); page.mouse.move(900,550,steps=12); page.mouse.up()
        page.wait_for_timeout(400)
        rotated = page.evaluate(snapshot)
        assert rotated['camera'] != initial['camera'], 'Mouse rotation failed'
        page.mouse.wheel(0,-300); page.wait_for_timeout(700)
        zoomed = page.evaluate(snapshot)
        assert zoomed['camera'] != rotated['camera'], 'Mouse zoom failed'

        def redraw():
            page.evaluate('async () => {await window.WRF_DIAGNOSTIC_VIEWER.draw();}')
            page.wait_for_function("() => !document.getElementById('wrf-status').textContent.startsWith('Viewer error:')")

        # Setting DOM values then invoking the same callback avoids racing the
        # GUI between screenshots. A real UI event is also tested below.
        page.locator('#wrf-opacity').evaluate('(e) => e.value=.6')
        names = page.evaluate('() => Object.entries(WRF_DIAGNOSTIC_VIEWER.bundle.diagnostics).filter(([k,v])=>v.available).map(([k,v])=>k)')
        state_count = page.evaluate('() => WRF_DIAGNOSTIC_VIEWER.bundle.frames.length')
        for name in names:
            page.locator('#wrf-variable').evaluate('(e,value)=>e.value=value',name)
            for time in range(state_count):
                page.locator('#wrf-time').evaluate('(e,value)=>e.value=value',str(time)); redraw()
                after = page.evaluate(snapshot)
                assert after['terrain'] == initial['terrain'], 'Terrain changed with diagnostic/time'
                assert after['opacity'] == .6
                expected = page.evaluate('() => {const b=WRF_DIAGNOSTIC_VIEWER.bundle;return b.diagnostics[document.getElementById("wrf-variable").value].colour_range;}')
                np.testing.assert_array_equal(after['colour'],expected)
                for key in ('eye','up','center'):
                    np.testing.assert_allclose(list(after['camera'][key].values()),list(zoomed['camera'][key].values()),atol=1e-8,rtol=1e-8)
        for axis in ('xz','yz'):
            page.locator('#wrf-section-axis').evaluate('(e,value)=>e.value=value',axis)
            for position in (0,3):
                page.locator('#wrf-section-position').evaluate('(e,value)=>e.value=value',str(position));redraw()
                result = page.evaluate("""() => {const b=WRF_DIAGNOSTIC_VIEWER.bundle,g=document.getElementById('wrf-isosurfaces');
                    const name=document.getElementById('wrf-variable').value,t=+document.getElementById('wrf-time').value;
                    const axis=document.getElementById('wrf-section-axis').value,p=+document.getElementById('wrf-section-position').value;
                    const v=b.frames[t].diagnostics[name].values;
                    const expected=v.map(layer=>axis==='xz'?layer[p]:layer.map(row=>row[p]));
                    return JSON.stringify(expected)===JSON.stringify(g.data.at(-1).surfacecolor);} """)
                assert result,'Section does not match exported scalar values'
        page.locator('#wrf-view').evaluate('(e)=>e.value="section"');redraw()
        assert page.evaluate("() => {const g=document.getElementById('wrf-isosurfaces');return g.layout.meta.mesh_trace_indices.every(i=>g.data[i].visible===false)&&g.data.at(-1).visible;}")
        page.locator('#wrf-view').select_option('terrain_surfaces')
        page.wait_for_function("""() => {
            const g=document.getElementById('wrf-isosurfaces');
            return g.data[0].visible===true&&g.data[1].visible===true&&
                g.layout.meta.mesh_trace_indices.some(i=>g.data[i].visible===true)&&g.data.at(-1).visible===false;
        }""")
        # The no-section choice must survive diagnostic/time redraws.
        page.locator('#wrf-time').evaluate('(e)=>e.value="0"');redraw()
        assert page.evaluate("() => {const g=document.getElementById('wrf-isosurfaces');return g.data[0].visible===true&&g.data[1].visible===true&&!g.data.at(-1).visible;}")
        # Independent geometric/linear-interpolation oracles in the actual JS
        # engine: no Python mirror of the clipping implementation is involved.
        analytic = page.evaluate("""() => {
            const api=WRF_DIAGNOSTIC_VIEWER;
            const mesh={level:1,vertices_km:[[0,0,0],[1,0,1],[0,1,2]],faces:[[0,1,2]],colours:['red']};
            const original=JSON.stringify(mesh),cut=api.clipMesh(mesh,.5,1.5);
            const line=api.clipLine({x:[0,3],y:[0,0],z:[-1,2]},.5,1.5);
            const section=api.clipSection({x:[[0,1],[0,1]],y:[[0,0],[0,0]],
                z:[[0,0],[2,2]],surfacecolor:[[0,0],[20,20]]},.5,1.5);
            const points=new Set(cut.vertices_km.map(p=>p.join(',')));
            return {unaltered:JSON.stringify(mesh)===original,faces:cut.faces.length,
                expected_vertices:['0.5,0,0.5','1,0,1','0.5,0.5,1.5','0,0.75,1.5','0,0.25,0.5'].every(p=>points.has(p)),
                plane:cut.vertices_km.every(p=>Math.abs(p[2]-p[0]-2*p[1])<1e-12),
                colours:cut.colours.every(c=>c==='red'),line:line,section:section};
        }""")
        assert analytic['unaltered'] and analytic['expected_vertices'] and analytic['plane'] and analytic['colours']
        assert analytic['faces'] == 3
        assert analytic['line']['x'] == [1.5,2.5,None]
        assert analytic['line']['z'] == [.5,1.5,None]
        assert analytic['section']['z'] == [[.5,.5],[1.5,1.5]]
        assert analytic['section']['surfacecolor'] == [[5,5],[15,15]]
        height_before = page.evaluate(snapshot)
        cutoff = min(1000.,height_before['height'][1]*500)
        lower = max(0.,height_before['height'][0]*1000)
        page.locator('#wrf-height-min').fill(str(lower))
        page.locator('#wrf-height-max').fill(str(cutoff))
        page.locator('#wrf-height-apply').click()
        page.wait_for_function('(top)=>document.getElementById("wrf-isosurfaces").layout.scene.zaxis.range[1]===top',arg=cutoff/1000)
        for name in names:
            page.locator('#wrf-variable').evaluate('(e,value)=>e.value=value',name)
            for time in (0,state_count-1):
                page.locator('#wrf-time').evaluate('(e,value)=>e.value=value',str(time));redraw()
                assert page.evaluate("""() => {
                    const g=document.getElementById('wrf-isosurfaces'),[lo,hi]=g.layout.scene.zaxis.range;
                    const bounded=v=>v===null||(v>=lo-1e-12&&v<=hi+1e-12);
                    return [0,1,...g.layout.meta.mesh_trace_indices].every(i=>g.data[i].z.every(bounded))&&
                        g.data.at(-1).z.every(row=>row.every(bounded))&&g.data.at(-1).visible===false;
                }"""), 'Geometry leaked outside the selected physical height band'
        height_after = page.evaluate(snapshot)
        for key in ('eye','up','center'):
            np.testing.assert_allclose(list(height_after['camera'][key].values()),list(height_before['camera'][key].values()),atol=1e-8,rtol=1e-8)
        assert page.evaluate('() => +document.getElementById("wrf-scale").value') > 5
        # Reversed bounds must not change the current valid scene.
        page.locator('#wrf-height-min').fill(str(cutoff+1))
        page.locator('#wrf-height-apply').click()
        page.wait_for_function('() => document.getElementById("wrf-status").textContent.startsWith("Invalid height window")')
        assert page.evaluate(snapshot)['height'] == height_after['height']
        page.locator('#wrf-height-full').click()
        page.wait_for_function('(top)=>document.getElementById("wrf-isosurfaces").layout.scene.zaxis.range[1]===top',arg=height_before['height'][1])
        redraw()
        assert page.evaluate(snapshot)['terrain'] == initial['terrain'], 'Full export did not restore original terrain'
        before_scale = page.evaluate(snapshot)
        page.locator('#wrf-scale').select_option('1')  # Actual HTML change event.
        page.wait_for_timeout(1000);redraw()
        assert page.evaluate(snapshot)['height'] == before_scale['height']
        assert page.evaluate('() => Array.from(document.getElementById("wrf-variable").options).filter(o=>o.disabled).every(o=>o.title.length>0)')
        # Leave a scientifically labelled rotating-flow view for visual review.
        if 'vertical_vorticity' in names:
            page.locator('#wrf-variable').evaluate('(e)=>e.value="vertical_vorticity"')
        page.locator('#wrf-scale').evaluate('(e)=>e.value="5"')
        page.locator('#wrf-view').evaluate('(e)=>e.value="all"');redraw()
        # Screenshot a useful overview, not the deliberately zoomed test view.
        page.evaluate("async () => {const g=document.getElementById('wrf-isosurfaces');await Plotly.relayout(g,{'scene.camera':{eye:{x:.9,y:-.95,z:.65},up:{x:0,y:0,z:1},center:{x:0,y:0,z:0}}});}")
        page.wait_for_timeout(500)
        if args.screenshot: page.screenshot(path=str(args.screenshot))
        external = [url for url in requests if url.startswith(('http://','https://'))]
        assert not external,external
        assert not errors,errors
        report = dict(browser='Installed Chrome, headless, isolated ephemeral profile, offline',
            software_webgl_opt_in=args.software_webgl,diagnostics_checked=names,actual_states=state_count,
            mouse_rotation=True,wheel_zoom=True,camera_preserved=True,terrain_static=True,
            opacity_preserved=True,fixed_colour_ranges=True,sections_match_export_in_both_orientations=True,
            section_only_view=True,physical_height_invariant=True,missing_fields_explained=True,
            terrain_and_surfaces_without_section=True,
            height_window_clips_meshes_terrain_coast_and_sections=True,height_window_persists_across_fields_and_times=True,
            height_clipping_analytical_oracles=True,invalid_height_window_rejected=True,full_height_restores_original_terrain=True,
            layout_viewports_checked=layout_sizes,layout_checked_with_methods_expanded_and_collapsed=True,
            external_http_requests=external,page_errors=errors)
        if args.result: args.result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report,indent=2))
        browser.close()


if __name__ == '__main__':
    main()

"""Viewer contracts: animation cannot rewrite terrain, coordinates or camera."""
from copy import deepcopy
from html.parser import HTMLParser

import numpy as np
import pytest

pytest.importorskip("plotly")

from wrf_tools.interactive import isosurface_figure, write_isosurface_html


def _geometry():
    return dict(schema="wrf-tools-isosurfaces",schema_version=1,temporal_interpolation="none",
        domain="d01",variable="wind_speed",thresholds=[12.],top_metres=500.,horizontal_stride=1,
        x_extent_km=1.,y_extent_km=1.,source=dict(units="m s-1"),
        model_top=dict(interface_msl_m=[600.,620.]),
        terrain=dict(vertices_km=[[0,0,0],[1,0,0],[1,1,.01],[0,1,0]],
            faces=[[0,1,2,3]],colours=["#175373"],coastlines_km=[[[0,.5,0],[1,.5,0]]]),
        frames=[dict(time_utc=f"2025-01-01T0{i}:00:00",meshes=[dict(level=12.,
            vertices_km=[[0,0,.1+i*.1],[1,0,.1+i*.1],[0,1,.1+i*.1]],faces=[[0,1,2]])]) for i in range(2)])


def test_only_wind_is_animated_terrain_camera_and_user_settings_are_not_reset():
    data = _geometry()
    original = deepcopy(data)
    figure = isosurface_figure(data,vertical_exaggeration=5.)
    assert data == original
    assert figure.layout.scene.uirevision == "wrf-isosurface-camera"
    assert figure.layout.scene.dragmode == "orbit"
    assert figure.data[0].opacity == 1
    assert figure.data[0].lighting.ambient == 1
    assert figure.data[0].lighting.diffuse == 0
    assert len(figure.data[0].i) == 2  # Terrain quad is explicitly triangulated.
    for frame in figure.frames:
        assert frame.traces == (2,)
        assert len(frame.data) == 1
        assert frame.layout.to_plotly_json() == {}
        assert frame.data[0].opacity is None and frame.data[0].visible is None


def test_vertical_exaggeration_changes_display_not_physical_height():
    a = isosurface_figure(_geometry(),vertical_exaggeration=1.)
    b = isosurface_figure(_geometry(),vertical_exaggeration=25.)
    assert a.data[0].z == b.data[0].z
    assert a.data[2].z == b.data[2].z == (.1,.1,.1)
    assert b.layout.scene.aspectratio.z == pytest.approx(25*a.layout.scene.aspectratio.z)
    assert a.layout.scene.zaxis.range == b.layout.scene.zaxis.range == (-.01,.5)
    assert b.layout.meta["physical_height_units"] == "km MSL"


def test_controls_retain_time_and_only_change_requested_presentation():
    fig = isosurface_figure(_geometry())
    assert [frame.name for frame in fig.frames] == ["2025-01-01T00:00:00","2025-01-01T01:00:00"]
    assert len(fig.layout.sliders[0].steps) == 2
    menus = fig.layout.updatemenus
    assert menus[1].buttons[1].label == "Terrain only"
    assert list(menus[1].buttons[1].args[1]) == [True,True,False]
    assert menus[2].buttons[0].label == "Vertical scale 1x"
    assert all(list(button.args[-1]) == [2] for button in menus[3].buttons)


def test_self_contained_html_needs_no_external_script_and_refuses_overwrite(tmp_path):
    path = write_isosurface_html(_geometry(),tmp_path/"viewer.html")
    text = path.read_text(encoding="utf-8")

    class Scripts(HTMLParser):
        def __init__(self):
            super().__init__(); self.external = []
        def handle_starttag(self,tag,attributes):
            if tag == "script" and "src" in dict(attributes): self.external.append(dict(attributes)["src"])

    parser = Scripts(); parser.feed(text)
    assert not parser.external
    assert "Plotly.newPlot" in text and "wrf-isosurfaces" in text and "scrollZoom" in text
    assert "wrf-webgl-diagnostic" in text and "WRF_WEBGL_STATUS" in text
    assert text.index("window.WRF_WEBGL_STATUS") < text.index("Plotly.newPlot")
    assert "chrome://settings/system" in text
    assert 'if (window.WRF_WEBGL_STATUS.available && document.getElementById("wrf-isosurfaces")) {' in text
    assert "Plotly.animate('wrf-isosurfaces'" not in text  # No automatic playback.
    with pytest.raises(FileExistsError):
        write_isosurface_html(_geometry(),path)


@pytest.mark.parametrize("options",[{"vertical_exaggeration":0},{"vertical_exaggeration":np.nan},
    {"surface_opacity":-.1},{"surface_opacity":1.1},{"surface_opacity":np.inf}])
def test_invalid_display_settings_rejected(options):
    with pytest.raises(ValueError):
        isosurface_figure(_geometry(),**options)


def test_inconsistent_thresholds_and_invalid_faces_are_rejected():
    data = _geometry(); data["frames"][1]["meshes"][0]["level"] = 16.
    with pytest.raises(ValueError,match="thresholds"):
        isosurface_figure(data)
    data = _geometry(); data["frames"][1]["meshes"][0]["faces"] = [[0,1,99]]
    with pytest.raises(ValueError,match="face indices"):
        isosurface_figure(data)

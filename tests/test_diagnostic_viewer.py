"""Analytical tensor checks and real-shape offline diagnostic contracts."""
import json
from copy import deepcopy

import numpy as np
import pytest

from wrf_tools._diagnostic_geometry import _basis, _cartesian_gradient, _invariants, _physical_diagnostics


def test_cartesian_chain_rule_recovers_general_affine_tensor_on_sloping_grid():
    k,j,i = np.indices((5,6,7),dtype=float)
    positions = np.stack((700*i+25*j,900*j+10*k,30*i+40*j+50*k+4*k*k),axis=-1)
    tensor = np.array([[.2,-.4,.7],[.8,.3,-.6],[-.1,.9,.5]])
    velocity = np.einsum('ab,...b->...a',tensor,positions)+[2,4,7]
    gradient = _cartesian_gradient(positions,velocity)
    np.testing.assert_allclose(gradient,np.broadcast_to(tensor,gradient.shape),atol=3e-14)
    q,zeta = _invariants(gradient,np.array([0.,0.,1.]))
    expected_q = -.5*np.trace(tensor@tensor)
    np.testing.assert_allclose(q,expected_q,atol=3e-14)
    np.testing.assert_allclose(zeta,1.2,atol=3e-14)


@pytest.mark.parametrize('kind',['rotation','strain','shear','uniform'])
def test_q_does_not_confuse_shear_strain_translation_and_rotation(kind):
    k,j,i = np.indices((4,4,4),dtype=float)
    positions = np.stack((i*1000,j*1200,50+100*k+8*i),axis=-1)
    rate = .002
    tensors = dict(rotation=[[0,-rate,0],[rate,0,0],[0,0,0]],
        strain=[[rate,0,0],[0,-rate,0],[0,0,0]],
        shear=[[0,rate,0],[0,0,0],[0,0,0]],uniform=np.zeros((3,3)))
    velocity = positions@np.asarray(tensors[kind]).T+[1,2,3]
    q,zeta = _invariants(_cartesian_gradient(positions,velocity),np.array([0.,0.,1.]))
    np.testing.assert_allclose(q,dict(rotation=rate**2,strain=-rate**2,shear=0,uniform=0)[kind],atol=1e-17)
    np.testing.assert_allclose(zeta,dict(rotation=2*rate,strain=0,shear=-rate,uniform=0)[kind],atol=1e-15)


def test_spherical_embedding_rotation_and_wind_basis_match_exact_cartesian_field():
    import xarray as xr
    k,j,i = np.indices((4,5,6),dtype=float)
    lat = 51+j[0]*.02; lon = 4+i[0]*.03
    heights = 100+200*k+20*i+30*j
    radius = 6370000.
    east,north,up = _basis(lat,lon)
    positions = (radius+heights)[...,None]*up
    tensor = np.array([[1e-4,-3e-4,2e-4],[5e-4,-2e-4,1e-4],[0,4e-4,1e-4]])
    velocity = positions@tensor.T+[1,2,3]
    earth_u = np.sum(velocity*east,axis=-1)
    earth_v = np.sum(velocity*north,axis=-1)
    w = np.sum(velocity*up,axis=-1)
    angle = .2+.001*i[0]; cosine,sine = np.cos(angle),np.sin(angle)
    u,v = earth_u*cosine+earth_v*sine,earth_v*cosine-earth_u*sine
    dims = ('south_north','west_east')
    frame = xr.Dataset({name:(dims,value) for name,value in dict(
        XLAT=lat,XLONG=lon,COSALPHA=cosine,SINALPHA=sine).items()})
    q,zeta = _physical_diagnostics(frame,u,v,w,heights,radius)
    curl = np.array([tensor[2,1]-tensor[1,2],tensor[0,2]-tensor[2,0],tensor[1,0]-tensor[0,1]])
    np.testing.assert_allclose(q,-.5*np.trace(tensor@tensor),rtol=2e-9,atol=1e-15)
    np.testing.assert_allclose(zeta,np.broadcast_to(up@curl,zeta.shape),rtol=2e-9,atol=1e-14)
    frame.COSALPHA.values[:] = 2
    with pytest.raises(ValueError,match='unit rotations'):
        _physical_diagnostics(frame,u,v,w,heights,radius)


def test_singular_missing_and_incompatible_coordinates_are_errors():
    positions = np.zeros((3,3,3,3))
    with pytest.raises(ValueError,match='Singular'):
        _cartesian_gradient(positions,positions)
    with pytest.raises(ValueError,match='matching'):
        _cartesian_gradient(positions,np.zeros((2,3,3,3)))
    positions[0,0,0,0] = np.nan
    with pytest.raises(ValueError,match='Missing'):
        _cartesian_gradient(positions,positions)


@pytest.fixture
def bundle(tmp_path):
    pytest.importorskip('skimage'); pytest.importorskip('netCDF4')
    from test_isosurfaces import _fixture
    from wrf_tools.isosurfaces import export_isosurface_sequence
    ds = _fixture().drop_vars('QKE')
    k,j,i = np.indices((5,8,8),dtype=float)
    ds.W.values[:] = .1*j-.2*i+.03*k
    ds.to_netcdf(tmp_path/'wrfout_d01_2025-01-01_00_00_00')
    path = export_isosurface_sequence(tmp_path,tmp_path/'diagnostics.json',domain='d01',
        diagnostics=dict(wind_speed=[7,8],vertical_velocity=[-.5,.5],
            vertical_vorticity=[-1e-4,1e-4],q_criterion=[1e-9],model_tke=[.5,1]),
        horizontal_stride=2,top_metres=None,maximum_frames=2)
    return json.loads(path.read_text(encoding='utf-8'))


def test_export_units_availability_fixed_ranges_and_sampled_native_heights(bundle):
    assert bundle['schema_version'] == 2
    records = bundle['diagnostics']
    assert not records['model_tke']['available']
    assert 'No supported' in records['model_tke']['reason']
    assert records['q_criterion']['units'] == 's-2'
    assert records['vertical_vorticity']['units'] == 's-1'
    assert records['vertical_velocity']['colour_range'][0] == -records['vertical_velocity']['colour_range'][1]
    assert 'Jacobian' in records['q_criterion']['source']['derivative_method']
    assert [f['time_utc'] for f in bundle['frames']] == ['2025-01-01T00:00:00','2025-01-01T00:00:10']
    for frame in bundle['frames']:
        assert np.shape(frame['heights_m']) == (4,5,5)
        assert 'model_tke' not in frame['diagnostics']
        assert np.shape(frame['diagnostics']['wind_speed']['values']) == (4,5,5)
        for name,row in frame['diagnostics'].items():
            assert [m['level'] for m in row['meshes']] == records[name]['thresholds']


def test_native_section_matches_exact_exported_values_in_both_orientations(bundle):
    from wrf_tools._diagnostic_interactive import _section
    frame = bundle['frames'][1]
    for axis in ('xz','yz'):
        section = _section(bundle,'vertical_velocity',1,axis,2)
        values = np.asarray(frame['diagnostics']['vertical_velocity']['values'])
        expected = values[:,2,:] if axis == 'xz' else values[:,:,2]
        np.testing.assert_array_equal(section['surfacecolor'],expected)
        coord = section['y'] if axis == 'xz' else section['x']
        assert np.all(np.asarray(coord) == bundle['y_km' if axis == 'xz' else 'x_km'][2])


def test_offline_diagnostic_html_and_initial_scene_contract(bundle,tmp_path):
    pytest.importorskip('plotly')
    from wrf_tools.interactive import isosurface_figure,write_isosurface_html
    original = deepcopy(bundle)
    figure = isosurface_figure(bundle)
    assert bundle == original
    assert not figure.frames
    assert not figure.layout.updatemenus and not figure.layout.sliders and not figure.layout.annotations
    assert figure.layout.legend.y == 1. and figure.layout.legend.yanchor == 'bottom'
    assert figure.data[0].opacity == 1
    assert figure.data[-1].type == 'surface'
    assert figure.layout.meta['section_trace_index'] == 4
    assert list(figure.layout.meta['terrain_trace_indices']) == [0,1]
    html = write_isosurface_html(bundle,tmp_path/'viewer.html').read_text(encoding='utf-8')
    for marker in ('wrf-variable','wrf-section-position','wrf-section-axis','WRF_DIAGNOSTIC_VIEWER',
                   'No supported model TKE','surfacecolor','rememberCamera','WRF_WEBGL_STATUS'):
        assert marker in html
    assert '__WRF_DIAGNOSTIC_DATA__' not in html
    assert '<body class="wrf-diagnostic-page">' in html
    assert 'grid-template-rows:auto minmax(360px,1fr) auto' in html
    assert "plotContainer.id='wrf-plot-container'" in html
    assert "'margin.t':height+65" not in html
    assert '<option value="terrain_surfaces">Terrain + surfaces only</option>' in html
    for marker in ('wrf-height-min','wrf-height-max','wrf-height-apply','wrf-height-full',
                   'wrf-height-fit','Height window (m MSL)','Invalid height window'):
        assert marker in html


def test_corrupt_second_frame_is_rejected_not_silently_skipped(bundle):
    pytest.importorskip('plotly')
    from wrf_tools.interactive import isosurface_figure
    bad = deepcopy(bundle); bad['frames'][1]['diagnostics']['q_criterion']['meshes'][0]['level'] = 10.
    with pytest.raises(ValueError,match='thresholds'):
        isosurface_figure(bad)
    bad = deepcopy(bundle); bad['frames'][1]['diagnostics']['wind_speed']['values'][0][0][0] = np.nan
    with pytest.raises(ValueError,match='section values'):
        isosurface_figure(bad)


def test_missing_rotation_disables_derivatives_without_disabling_native_fields(tmp_path):
    pytest.importorskip('netCDF4'); pytest.importorskip('skimage')
    from test_isosurfaces import _fixture
    from wrf_tools.isosurfaces import export_isosurface_sequence
    ds = _fixture().drop_vars('COSALPHA')
    ds.to_netcdf(tmp_path/'wrfout_d01_2025-01-01_00_00_00')
    path = export_isosurface_sequence(tmp_path,tmp_path/'no-rotation.json',domain='d01',
        diagnostics=dict(wind_speed=[1e6],q_criterion=[1e-8],model_tke=[.5,1.5]),
        horizontal_stride=1,top_metres=500)
    data = json.loads(path.read_text(encoding='utf-8'))
    assert not data['diagnostics']['q_criterion']['available']
    assert 'COSALPHA' in data['diagnostics']['q_criterion']['reason']
    assert data['diagnostics']['wind_speed']['available']
    assert not data['frames'][0]['diagnostics']['wind_speed']['meshes'][0]['faces']
    # An empty isosurface does not disable a valid field/section.
    assert data['diagnostics']['model_tke']['available']
    assert data['diagnostics']['model_tke']['source']['conversion_factor'] == .5
    np.testing.assert_allclose(data['frames'][0]['diagnostics']['model_tke']['values'],1.)
    with pytest.raises(FileExistsError):
        export_isosurface_sequence(tmp_path,path,diagnostics=dict(wind_speed=[7,8]))


def test_diagnostic_resource_limit_moving_grid_and_missing_values_fail_visibly(tmp_path):
    pytest.importorskip('netCDF4'); pytest.importorskip('skimage')
    from test_isosurfaces import _fixture
    from wrf_tools.isosurfaces import export_isosurface_sequence
    ds = _fixture()
    source = tmp_path/'wrfout_d01_2025-01-01_00_00_00'
    output = tmp_path/'invalid.json'
    ds.to_netcdf(source)
    options = dict(domain='d01',diagnostics=dict(wind_speed=[7,8]),horizontal_stride=1)
    with pytest.raises(ValueError,match='maximum_faces'):
        export_isosurface_sequence(tmp_path,output,maximum_faces=1,**options)
    assert not output.exists()
    ds.XLAT.values[1] += .01; ds.to_netcdf(source)
    with pytest.raises(ValueError,match='Moving grids'):
        export_isosurface_sequence(tmp_path,output,**options)
    ds = _fixture(); ds.U.values[0,0,0,0] = np.nan; ds.to_netcdf(source)
    with pytest.raises(ValueError,match='nonfinite'):
        export_isosurface_sequence(tmp_path,output,**options)
    assert not output.exists()


@pytest.mark.parametrize('options',[dict(diagnostics={}),dict(diagnostics={'fake':[1]}),
    dict(diagnostics={'wind_speed':[2,1]}),dict(earth_radius_metres=0),dict(horizontal_stride=0),
    dict(maximum_frames=0),dict(maximum_faces=0),dict(top_metres=np.nan)])
def test_invalid_diagnostic_settings_fail_before_reading_files(tmp_path,options):
    from wrf_tools.isosurfaces import export_isosurface_sequence
    options = dict(diagnostics={'wind_speed':[7,8]},**options) if 'diagnostics' not in options else options
    with pytest.raises(ValueError):
        export_isosurface_sequence(tmp_path,tmp_path/'none.json',**options)

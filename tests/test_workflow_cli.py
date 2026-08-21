import numpy as np
from wrf_tools.cli import build_parser
from wrf_tools.coupling.openfast import step_field, write_uniform_wind
from wrf_tools.workflow import archive_outputs

def test_archive_step_uniform_and_cli(tmp_path):
    source=tmp_path/"source.txt"; source.write_text("data")
    copied=archive_outputs([source],tmp_path/"archive")
    assert copied[0].read_text()=="data"
    field=step_field(speeds=[5,10],step_duration=1,dt=.5,ny=2,nz=2,dy=5,dz=5,hub_height=10,bottom_height=5)
    np.testing.assert_allclose(field.velocity[:,0,0,0],[5,5,10,10])
    path=write_uniform_wind(tmp_path/"uniform.wnd",[0,1],[5,6])
    assert path.exists()
    parser=build_parser()
    for command in ("validate","concat","extract","filter","spectra","report","openfast-info","bts-compare"):
        assert command in parser.format_help()

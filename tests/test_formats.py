import struct
import numpy as np
from wrf_tools.coupling.openfast import WindField, read_bladed_wnd, read_coherent_points, read_hub_height_binary, write_bladed_wnd
from wrf_tools.openfast import read_binary_output

def test_hub_height_and_coherent_point_readers(tmp_path):
    hh = tmp_path/"wind.hh"
    np.arange(28, dtype="<f4").tofile(hh)
    assert read_hub_height_binary(hh).sizes["time"] == 2
    pts = tmp_path/"wind.pts"
    header = struct.pack("<hiifffff", -99, 3, 2, 10.0, 5.0, 10.0, 20.0, 30.0)
    pts.write_bytes(header+np.zeros(12, dtype="<i2").tobytes())
    result = read_coherent_points(pts)
    assert result.velocity.shape == (2,2,3)
    np.testing.assert_allclose(result.velocity[...,0], 5)

def test_openfast_binary_without_packed_time(tmp_path):
    path = tmp_path/"output.outb"; channels=2; nt=3
    payload = struct.pack("<hii", 2, channels, nt)+struct.pack("<dd", 0.0, 0.5)
    payload += np.ones(channels, dtype="<f4").tobytes()+np.zeros(channels, dtype="<f4").tobytes()
    payload += struct.pack("<i", 4)+b"test"
    for text in ("Time","Wind","Load"): payload += text.ljust(10).encode()
    for text in ("s","m/s","N"): payload += text.ljust(10).encode()
    payload += np.arange(nt*channels, dtype="<i2").tobytes(); path.write_bytes(payload)
    data = read_binary_output(path)
    np.testing.assert_allclose(data.time, [0,.5,1])
    assert set(data.data_vars) == {"Wind","Load"}

def test_bladed_wnd_roundtrip(tmp_path):
    rng=np.random.default_rng(2); velocity=rng.normal(scale=.5,size=(4,2,3,3)); velocity[...,0]+=10
    field=WindField(velocity,dy=5,dz=6,dt=.1,hub_height=50,bottom_height=47,mean_speed=10)
    path=write_bladed_wnd(tmp_path/"field.wnd",field)
    actual=read_bladed_wnd(path,hub_height=50)
    assert actual.velocity.shape==velocity.shape
    np.testing.assert_allclose(actual.velocity,velocity,atol=.002)

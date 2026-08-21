from wrf_tools.openfast_input import read_parameters, update_parameters

def test_openfast_parameter_roundtrip(tmp_path):
    source=tmp_path/"case.fst"; source.write_text('10.0 TMax - Total run time\n"wind.bts" Filename - Inflow file\n')
    target=tmp_path/"updated.fst"; update_parameters(source,{"TMax":20.0,"Filename":"new wind.bts"},output=target)
    values=read_parameters(target)
    assert values["TMax"]=="20.0" and values["Filename"]=="new wind.bts"

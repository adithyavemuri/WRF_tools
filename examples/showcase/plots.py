"""Chapter 4: editable plot objects and report writers, all synthetic."""
import numpy as np
import xarray as xr


def run(c):
    import matplotlib.pyplot as plt
    call=c.call
    x=np.arange(8); field=x[None,:]+x[:,None]
    examples={
        "horizontal":((field,),dict(title="SYNTHETIC field",colorbar_label="Value")),
        "profile":(([5,7,9],[10,100,200]),dict(xlabel="Wind speed (m/s)",title="SYNTHETIC profile")),
        "time_height":((np.arange(12).reshape(4,3),[0,1,2,3],[10,100,200]),dict(title="SYNTHETIC time-height")),
        "wind_rose":(([0,90,180,270],[4,5,6,7]),dict(title="SYNTHETIC wind rose")),
        "cross_section":((field,),dict(title="SYNTHETIC index-space section")),
        "wind_barbs":((field,field*.2),dict(stride=2,title="SYNTHETIC barbs")),
        "nested_domains":((c.domains,),{}),
        "validation_scatter":(([8.5,9.5,10.5],[8,9,10]),{}),
        "taylor_diagram":(([1.,1.2],[.8,.9]),dict(labels=["Synthetic A","Synthetic B"])),
    }
    for name,(args,kwargs) in examples.items():
        figure=call("plotting."+name,*args,**kwargs)
        c.save(figure,"plot-"+name+".png")
    fig,ax,animation=call("plotting.animate_fields",np.stack([field,field+1]),title="SYNTHETIC frame sequence")
    animation.save(c.output/"synthetic-fields.gif",writer="pillow",fps=1); plt.close(fig)
    figure=plt.figure(figsize=(6,5))
    call("visualization.geographic_axis",figure,111,c.dataset)
    c.save(figure,"synthetic-map-context.png")

    # Comparisons require explicit matching coordinates AND units.
    cases={"Synthetic A":c.model.speed.assign_attrs(units="m s-1"),
           "Synthetic B":c.observations.speed.assign_attrs(units="m s-1")}
    call("comparison.align_cases",cases,coordinate="time")
    c.save(call("comparison.plot_timeseries",cases,coordinate="time"),"comparison-timeseries.png")
    a=xr.DataArray([5,7,9],dims="height",coords={"height":[10,100,200]},attrs={"units":"m s-1"})
    a.height.attrs=dict(units="m",reference="AGL")
    c.save(call("comparison.plot_profiles",{"Synthetic A":a,"Synthetic B":a.copy(data=a.values+1)}),"comparison-profiles.png")
    report=call("reporting.dataset_summary",c.dataset)
    call("reporting.write_json_report",report,c.output/"synthetic-dataset-summary.json")
    metadata=call("reporting.provenance",inputs=c.files,configuration={"data_origin":"SYNTHETIC"})
    simple={"Data origin":"SYNTHETIC demonstration, not a WRF simulation","provenance":metadata}
    call("reporting.write_html_report",simple,c.output/"synthetic-metadata.html")
    call("reporting.write_pdf_report",simple,c.output/"synthetic-metadata.pdf")
    call("doctor.dependency_status")
    call("doctor.environment_report")
    call("doctor.print_environment_report",include_optional=False)
